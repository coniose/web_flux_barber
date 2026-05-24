"""Wizard de onboarding — configura o negócio na primeira vez."""

from __future__ import annotations

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.repositories.sql import config_repo
from web.models import get_user_conn

setup_bp = Blueprint("setup", __name__)


@setup_bp.route("/setup", methods=["GET"])
@login_required
def index():
    return render_template("setup.html")


@setup_bp.route("/setup", methods=["POST"])
@login_required
def salvar():
    conn = get_user_conn()

    nome_negocio = (request.form.get("nome_negocio") or "").strip()
    descricao_negocio = (request.form.get("descricao_negocio") or "").strip()
    tipo_trabalho = request.form.get("tipo_trabalho") or "ambos"
    formas = request.form.getlist("formas_pagamento")
    horario = (request.form.get("horario_trabalho") or "").strip()

    if not nome_negocio:
        return render_template("setup.html", erro="Informe o nome do seu negócio.")

    if tipo_trabalho not in ("servicos", "produtos", "ambos"):
        tipo_trabalho = "ambos"

    formas_validas = {"PIX", "DINHEIRO", "MAQUININHA"}
    formas = [f for f in formas if f in formas_validas]
    if not formas:
        formas = ["PIX", "DINHEIRO", "MAQUININHA"]

    config_repo.set_config(conn, "nome_negocio", nome_negocio)
    config_repo.set_config(conn, "descricao_negocio", descricao_negocio)
    config_repo.set_config(conn, "tipo_trabalho", tipo_trabalho)
    config_repo.set_config(conn, "formas_pagamento", ",".join(formas))
    if horario:
        config_repo.set_config(conn, "horario_trabalho", horario)
    config_repo.set_config(conn, "onboarding_completo", "1")

    return redirect(url_for("dashboard.index"))
