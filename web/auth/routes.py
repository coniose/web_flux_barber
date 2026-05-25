"""Rotas de autenticação: login, register, logout, recuperação de senha."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.repositories.db import get_connection
from web.extensions import limiter
from web.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        lembrar = bool(request.form.get("lembrar"))

        user = User.get_by_email(email)
        if user and user.verificar_senha(senha):
            login_user(user, remember=lembrar)
            user.registrar_acesso()
            # Verifica assinatura Stripe no login para capturar cancelamentos perdidos
            from web.routes.billing import verificar_plano_stripe
            verificar_plano_stripe(user)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))

        flash("E-mail ou senha incorretos.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        confirmar = request.form.get("confirmar", "")

        erros = []
        if not nome:
            erros.append("Nome é obrigatório.")
        if not email or "@" not in email:
            erros.append("E-mail inválido.")
        if len(senha) < 6:
            erros.append("Senha deve ter ao menos 6 caracteres.")
        if senha != confirmar:
            erros.append("As senhas não coincidem.")
        if User.get_by_email(email):
            erros.append("Este e-mail já está cadastrado.")

        if erros:
            for e in erros:
                flash(e, "error")
        else:
            user = User.criar(nome, email, senha)

            # Semeia o catálogo inicial no SQLite do novo usuário
            try:
                from app.repositories.user_db import get_user_connection
                from app.repositories.sql.seed import apply_seed
                conn = get_user_connection(user.device_id)
                apply_seed(conn)
                conn.close()
            except Exception as exc:
                flash(f"Aviso: catálogo inicial não pôde ser criado ({exc}).", "info")

            login_user(user)
            flash(f"Bem-vindo, {user.nome}! Conta criada com sucesso.", "success")
            return redirect(url_for("dashboard.index"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


# ──────────────────────────────── Esqueci minha senha ────────────────────────


@auth_bp.route("/esqueci-senha", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def esqueci_senha():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.get_by_email(email)

        if user and user.auth_provider == "email":
            token = secrets.token_urlsafe(32)
            expira = datetime.now(timezone.utc) + timedelta(hours=1)

            conn = get_connection()
            conn.execute(
                "INSERT INTO password_reset_token (user_id, token, expira_em) VALUES (?, ?, ?)",
                (user.id, token, expira.strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.close()

            reset_url = url_for("auth.redefinir_senha", token=token, _external=True)
            from web.auth.email import send_password_reset
            send_password_reset(user.email, reset_url)

        # Sempre exibe a mesma mensagem — não revela se o e-mail existe
        flash("Se esse e-mail estiver cadastrado, você receberá um link em instantes.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/esqueci_senha.html")


@auth_bp.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def redefinir_senha(token: str):
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM password_reset_token WHERE token = ? AND usado = 0",
        (token,),
    ).fetchone()

    if not row:
        conn.close()
        flash("Link inválido ou já utilizado.", "error")
        return redirect(url_for("auth.login"))

    expira = datetime.strptime(row["expira_em"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expira:
        conn.close()
        flash("Link expirado. Solicite um novo.", "error")
        return redirect(url_for("auth.esqueci_senha"))

    if request.method == "POST":
        nova = request.form.get("senha", "")
        confirmar = request.form.get("confirmar", "")

        if len(nova) < 6:
            conn.close()
            return render_template("auth/redefinir_senha.html", token=token,
                                   erro="A senha deve ter ao menos 6 caracteres.")
        if nova != confirmar:
            conn.close()
            return render_template("auth/redefinir_senha.html", token=token,
                                   erro="As senhas não coincidem.")

        from werkzeug.security import generate_password_hash
        novo_hash = generate_password_hash(nova)
        conn.execute(
            "UPDATE usuario SET senha_hash = ? WHERE id = ?",
            (novo_hash, row["user_id"]),
        )
        conn.execute(
            "UPDATE password_reset_token SET usado = 1 WHERE token = ?",
            (token,),
        )
        conn.close()

        flash("Senha redefinida com sucesso! Faça login.", "success")
        return redirect(url_for("auth.login"))

    conn.close()
    return render_template("auth/redefinir_senha.html", token=token)
