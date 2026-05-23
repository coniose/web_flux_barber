"""Plano Pro — checkout Stripe, webhook e portal de cobrança."""

from __future__ import annotations

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

    etype = event["type"]
    data = event["data"]["object"]

    if etype == "checkout.session.completed":
        _ativar_pro(
            user_id=data.get("client_reference_id"),
            customer_id=data.get("customer"),
            subscription_id=data.get("subscription"),
        )
    elif etype == "customer.subscription.deleted":
        _desativar_pro(subscription_id=data.get("id"))

    return "", 200


def _ativar_pro(user_id, customer_id, subscription_id):
    if not user_id:
        return
    conn = get_connection()
    conn.execute(
        """UPDATE usuario
           SET plano = 'pro',
               stripe_customer_id = ?,
               stripe_subscription_id = ?
           WHERE id = ?""",
        (customer_id, subscription_id, int(user_id)),
    )
    conn.close()


def _desativar_pro(subscription_id):
    if not subscription_id:
        return
    conn = get_connection()
    conn.execute(
        """UPDATE usuario
           SET plano = 'free', stripe_subscription_id = NULL
           WHERE stripe_subscription_id = ?""",
        (subscription_id,),
    )
    conn.close()
