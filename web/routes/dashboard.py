"""Dashboard — visão geral do dia e do mês."""

from __future__ import annotations

from datetime import date, timedelta

from flask import Blueprint, render_template
from flask_login import login_required

from app.repositories.db import get_connection
from app.repositories import receita_repo, despesa_repo

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    conn = get_connection()
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)

    total_hoje, qtd_hoje = receita_repo.total_periodo(conn, hoje, hoje)
    desp_hoje, _ = despesa_repo.total_periodo(conn, hoje, hoje)

    total_mes, qtd_mes = receita_repo.total_periodo(conn, inicio_mes, hoje)
    desp_mes, _ = despesa_repo.total_periodo(conn, inicio_mes, hoje)

    serie = receita_repo.serie_diaria(conn, inicio_mes, hoje)
    serie_desp = despesa_repo.serie_diaria(conn, inicio_mes, hoje)
    ranking = receita_repo.ranking_servicos(conn, inicio_mes, hoje, limite=5)
    mix = receita_repo.mix_forma_pagamento(conn, hoje, hoje)

    conn.close()

    # Prepara séries para Chart.js
    dias_mes = _dias_no_periodo(inicio_mes, hoje)
    receita_por_dia = {r["data"]: r["total"] for r in serie}
    despesa_por_dia = {r["data"]: r["total"] for r in serie_desp}

    labels = [d.strftime("%d/%m") for d in dias_mes]
    data_receita = [receita_por_dia.get(d.isoformat(), 0) / 100 for d in dias_mes]
    data_despesa = [despesa_por_dia.get(d.isoformat(), 0) / 100 for d in dias_mes]

    return render_template(
        "dashboard.html",
        hoje=hoje,
        # KPIs do dia
        total_hoje=total_hoje,
        qtd_hoje=qtd_hoje,
        desp_hoje=desp_hoje,
        resultado_hoje=total_hoje - desp_hoje,
        # KPIs do mês
        total_mes=total_mes,
        qtd_mes=qtd_mes,
        desp_mes=desp_mes,
        resultado_mes=total_mes - desp_mes,
        # Gráfico
        chart_labels=labels,
        chart_receita=data_receita,
        chart_despesa=data_despesa,
        # Ranking e mix
        ranking=ranking,
        mix=mix,
    )


def _dias_no_periodo(inicio: date, fim: date) -> list[date]:
    dias = []
    atual = inicio
    while atual <= fim:
        dias.append(atual)
        atual += timedelta(days=1)
    return dias
