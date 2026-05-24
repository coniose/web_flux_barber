"""Plano Pro — checkout Stripe, webhook e portal de cobrança."""

from __future__ import annotations

from datetime import datetime, timezone

import stripe
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.repositories.db import get_connection

billing_bp = Blueprint("billing", __name__)


def _stripe():
    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
    return stripe


# ── Páginas ───────────────────────────────────────────────────────────────────

@billing_bp.route("/upgrade")
@login_required
def upgrade():
    if current_user.is_pro:
        flash("Você já tem o plano Pro.", "info")
        return redirect(url_for("dashboard.index"))
    return render_template("upgrade.html")


@billing_bp.route("/billing/sucesso")
@login_required
def sucesso():
    return render_template("billing_sucesso.html")


# ── Ações ─────────────────────────────────────────────────────────────────────

@billing_bp.route("/billing/checkout", methods=["POST"])
@login_required
def checkout():
    if current_user.is_pro:
        return redirect(url_for("dashboard.index"))

    price_id = current_app.config.get("STRIPE_PRICE_ID", "")
    if not price_id:
        flash("Pagamento indisponível no momento. Tente novamente mais tarde.", "error")
        return redirect(url_for("billing.upgrade"))

    s = _stripe()
    try:
        session = s.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=url_for("billing.sucesso", _external=True),
            cancel_url=url_for("billing.upgrade", _external=True),
            customer_email=current_user.email,
            client_reference_id=str(current_user.id),
            locale="pt-BR",
        )
        return redirect(session.url, 303)
    except stripe.StripeError as e:
        flash("Erro ao iniciar pagamento. Tente novamente.", "error")
        current_app.logger.error("Stripe checkout error: %s", e)
        return redirect(url_for("billing.upgrade"))


@billing_bp.route("/billing/portal", methods=["POST"])
@login_required
def portal():
    if not current_user.is_pro:
        return redirect(url_for("billing.upgrade"))

    conn = get_connection()
    row = conn.execute(
        "SELECT stripe_customer_id FROM usuario WHERE id = ?", (current_user.id,)
    ).fetchone()
    conn.close()

    customer_id = row["stripe_customer_id"] if row else None
    if not customer_id:
        flash("Conta de cobrança não encontrada. Contate o suporte.", "error")
        return redirect(url_for("dashboard.index"))

    s = _stripe()
    try:
        portal_session = s.billing_portal.Session.create(
            customer=customer_id,
            return_url=url_for("dashboard.index", _external=True),
        )
        return redirect(portal_session.url, 303)
    except stripe.StripeError as e:
        flash("Erro ao abrir portal de cobrança. Tente novamente.", "error")
        current_app.logger.error("Stripe portal error: %s", e)
        return redirect(url_for("dashboard.index"))


# ── Webhook ───────────────────────────────────────────────────────────────────

@billing_bp.route("/billing/webhook", methods=["POST"])
def webhook():
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature", "")
    secret = current_app.config.get("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)
    except stripe.errors.SignatureVerificationError:
        current_app.logger.warning("Stripe webhook: assinatura inválida")
        return "Assinatura inválida", 400
    except Exception:
        return "Payload inválido", 400

    event_id = event.get("id") or event.id
    etype = event.get("type") or event.type
    raw = event.get("data", {})
    data = raw.get("object") if isinstance(raw, dict) else getattr(raw, "object", raw)

    conn = get_connection()
    try:
        # Idempotência: ignora eventos já processados (proteção contra retentativas duplicadas)
        if conn.execute(
            "SELECT 1 FROM stripe_events WHERE event_id = ?", (event_id,)
        ).fetchone():
            return "", 200

        def _field(obj, key):
            if isinstance(obj, dict):
                return obj.get(key)
            return getattr(obj, key, None)

        if etype == "checkout.session.completed":
            _ativar_pro(
                conn=conn,
                user_id=_field(data, "client_reference_id"),
                customer_id=_field(data, "customer"),
                subscription_id=_field(data, "subscription"),
            )
        elif etype == "customer.subscription.deleted":
            _desativar_pro(conn=conn, subscription_id=_field(data, "id"))
        elif etype == "invoice.payment_failed":
            # Marca o usuário para que na próxima verificação de plano
            # o Stripe seja consultado e o downgrade ocorra se necessário
            _marcar_verificacao_pendente(conn=conn, customer_id=_field(data, "customer"))
            current_app.logger.warning(
                "Pagamento falhou para customer %s (tentativa %s)",
                _field(data, "customer"),
                _field(data, "attempt_count"),
            )

        conn.execute(
            "INSERT OR IGNORE INTO stripe_events (event_id, tipo) VALUES (?, ?)",
            (event_id, etype),
        )
    except Exception as e:
        current_app.logger.error("Webhook processing error: %s", e)
        return "Erro interno", 500
    finally:
        conn.close()

    return "", 200


def _ativar_pro(conn, user_id, customer_id, subscription_id):
    if not user_id:
        return
    conn.execute(
        """UPDATE usuario
           SET plano = 'pro',
               stripe_customer_id = ?,
               stripe_subscription_id = ?,
               plano_verificado_em = datetime('now')
           WHERE id = ?""",
        (customer_id, subscription_id, int(user_id)),
    )


def _marcar_verificacao_pendente(conn, customer_id):
    """Zera plano_verificado_em para forçar checagem no próximo login."""
    if not customer_id:
        return
    conn.execute(
        "UPDATE usuario SET plano_verificado_em = NULL WHERE stripe_customer_id = ?",
        (customer_id,),
    )


def _desativar_pro(conn, subscription_id):
    if not subscription_id:
        return
    conn.execute(
        """UPDATE usuario
           SET plano = 'free',
               stripe_subscription_id = NULL,
               plano_verificado_em = datetime('now')
           WHERE stripe_subscription_id = ?""",
        (subscription_id,),
    )


# ── Verificação periódica de assinatura ───────────────────────────────────────

def verificar_plano_stripe(user) -> bool:
    """
    Consulta o Stripe para confirmar que a assinatura ainda está ativa.
    Só executa se a última verificação foi há mais de 12 horas.
    Fail open: se o Stripe estiver inacessível, não rebaixa o usuário.
    Retorna True se o plano foi rebaixado para free.
    """
    if not user.is_pro or not user.stripe_subscription_id:
        return False

    # Só re-verifica se passou mais de 12 horas desde a última checagem
    if user.plano_verificado_em:
        try:
            ultima = datetime.fromisoformat(user.plano_verificado_em)
            if ultima.tzinfo is None:
                ultima = ultima.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - ultima).total_seconds() < 43200:
                return False
        except ValueError:
            pass

    try:
        stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
        sub = stripe.Subscription.retrieve(user.stripe_subscription_id)

        conn = get_connection()
        if sub.status in ("canceled", "unpaid", "incomplete_expired"):
            conn.execute(
                """UPDATE usuario
                   SET plano = 'free',
                       stripe_subscription_id = NULL,
                       plano_verificado_em = datetime('now')
                   WHERE id = ?""",
                (user.id,),
            )
            conn.close()
            current_app.logger.info(
                "Usuário #%s rebaixado para free (status Stripe: %s)", user.id, sub.status
            )
            return True
        else:
            conn.execute(
                "UPDATE usuario SET plano_verificado_em = datetime('now') WHERE id = ?",
                (user.id,),
            )
            conn.close()
    except stripe.StripeError as e:
        current_app.logger.warning("Stripe inacessível ao verificar plano: %s", e)

    return False
