"""Rotas de autenticação: login, register, logout."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

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

            # Semeia o catálogo inicial no Firestore do novo usuário
            try:
                from app.repositories.firestore_client import get_firestore_client
                from app.repositories.fs.seed import apply_seed
                from app.repositories.fs.store import BarberStore
                store = BarberStore(db=get_firestore_client(), device_id=user.device_id)
                apply_seed(store)
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
