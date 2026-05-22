"""Tela de despesas — listagem e edição."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.repositories.db import get_connection
from app.repositories import despesa_repo
from app.services import despesa_service
from app.utils.validators import ValidacaoError

despesas_bp = Blueprint("despesas", __name__)


@despesas_bp.route("/despesas")
@login_required
def index():
    hoje = date.today()
    de_str = request.args.get("de", hoje.replace(day=1).isoformat())
    ate_str = request.args.get("ate", hoje.isoformat())
    de = date.fromisoformat(de_str)
    ate = date.fromisoformat(ate_str)

    conn = get_connection()
    despesas = despesa_repo.listar_periodo(conn, de, ate)
    total, qtd = despesa_repo.total_periodo(conn, de, ate)
    por_categoria = despesa_repo.total_por_categoria(conn, de, ate)
    conn.close()

    return render_template(
        "despesas.html",
        despesas=despesas,
        total=total,
        qtd=qtd,
        por_categoria=por_categoria,
        de=de_str,
        ate=ate_str,
    )


@despesas_bp.route("/despesas/<int:despesa_id>/excluir", methods=["POST"])
@login_required
def excluir(despesa_id: int):
    conn = get_connection()
    despesa_service.excluir_despesa(conn, despesa_id)
    conn.close()
    flash("Despesa excluída.", "success")
    return redirect(request.referrer or url_for("despesas.index"))
