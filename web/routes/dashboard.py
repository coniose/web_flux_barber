"""Dashboard — visão geral do dia e período filtrável."""

from __future__ import annotations

from datetime import date, timedelta

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.repositories.sql import receita_repo, despesa_repo, movimentacao_repo
from web.models import get_user_conn

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    conn = get_user_conn()
    hoje = date.today()

    # --- Hoje (fixo) ---
    total_hoje, qtd_hoje = receita_repo.total_periodo(conn, hoje, hoje)
    desp_hoje, _ = despesa_repo.total_periodo(conn, hoje, hoje)
    mix = receita_repo.mix_forma_pagamento(conn, hoje, hoje)
    est_hoje = movimentacao_repo.totais_periodo(conn, hoje, hoje)

    # --- Período filtrável (query params, padrão = mês atual) ---
    de_str = request.args.get("de", "").strip()
    ate_str = request.args.get("ate", "").strip()
    try:
        de = date.fromisoformat(de_str) if de_str else hoje.replace(day=1)
        ate = date.fromisoformat(ate_str) if ate_str else hoje
        if de > ate:
            de, ate = ate, de
    except ValueError:
        de = hoje.replace(day=1)
        ate = hoje

    total_periodo, qtd_periodo = receita_repo.total_periodo(conn, de, ate)
    desp_periodo, _ = despesa_repo.total_periodo(conn, de, ate)
    est_periodo = movimentacao_repo.totais_periodo(conn, de, ate)

    serie = receita_repo.serie_diaria(conn, de, ate)
    serie_desp = despesa_repo.serie_diaria(conn, de, ate)
    ranking = receita_repo.ranking_servicos(conn, de, ate, limite=5)

    dias = _dias_no_periodo(de, ate)
    receita_por_dia = {r["data"]: r["total"] for r in serie}
    despesa_por_dia = {r["data"]: r["total"] for r in serie_desp}
    labels = [d.strftime("%d/%m") for d in dias]
    data_receita = [receita_por_dia.get(d.isoformat(), 0) / 100 for d in dias]
    data_despesa = [despesa_por_dia.get(d.isoformat(), 0) / 100 for d in dias]

    inicio_semana = hoje - timedelta(days=hoje.weekday())

    return render_template(
        "dashboard.html",
        hoje=hoje,
        inicio_semana=inicio_semana,
        # KPIs do dia
        total_hoje=total_hoje,
        qtd_hoje=qtd_hoje,
        desp_hoje=desp_hoje,
        resultado_hoje=total_hoje - desp_hoje,
        mix=mix,
        est_vendas_hoje=est_hoje["VENDA"]["total"],
        # KPIs do período
        de=de,
        ate=ate,
        total_periodo=total_periodo,
        qtd_periodo=qtd_periodo,
        desp_periodo=desp_periodo,
        resultado_periodo=total_periodo - desp_periodo,
        est_periodo=est_periodo,
        # Gráfico
        chart_labels=labels,
        chart_receita=data_receita,
        chart_despesa=data_despesa,
        ranking=ranking,
    )


def _dias_no_periodo(inicio: date, fim: date) -> list[date]:
    dias = []
    atual = inicio
    while atual <= fim:
        dias.append(atual)
        atual += timedelta(days=1)
    return dias
