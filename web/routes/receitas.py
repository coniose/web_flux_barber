"""Tela de receitas — listagem e edição."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.repositories.sql import receita_repo
from app.services import receita_service
from web.models import get_user_conn

receitas_bp = Blueprint("receitas", __name__)


@receitas_bp.route("/receitas")
@login_required
def index():
    hoje = date.today()
    de_str = request.args.get("de", hoje.replace(day=1).isoformat())
    ate_str = request.args.get("ate", hoje.isoformat())
    de = date.fromisoformat(de_str)
    ate = date.fromisoformat(ate_str)

    conn = get_user_conn()
    receitas = receita_repo.listar_periodo(conn, de, ate)
    total, qtd = receita_repo.total_periodo(conn, de, ate)

    return render_template(
        "receitas.html",
        receitas=receitas,
        total=total,
        qtd=qtd,
        de=de_str,
        ate=ate_str,
    )


@receitas_bp.route("/receitas/<int:receita_id>/excluir", methods=["POST"])
@login_required
def excluir(receita_id: int):
    conn = get_user_conn()
    receita_service.excluir_atendimento(conn, receita_id)
    flash("Atendimento excluído.", "success")
    return redirect(request.referrer or url_for("receitas.index"))
