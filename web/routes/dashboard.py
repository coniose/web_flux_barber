"""Dashboard — visão geral do dia e do mês."""

from __future__ import annotations

from datetime import date, timedelta

from flask import Blueprint, render_template
from flask_login import login_required

from app.repositories.fs import receita_repo, despesa_repo, movimentacao_repo
from web.models import get_store

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    store = get_store()
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)

    total_hoje, qtd_hoje = receita_repo.total_periodo(store, hoje, hoje)
    desp_hoje, _ = despesa_repo.total_periodo(store, hoje, hoje)

    total_mes, qtd_mes = receita_repo.total_periodo(store, inicio_mes, hoje)
    desp_mes, _ = despesa_repo.total_periodo(store, inicio_mes, hoje)

    serie = receita_repo.serie_diaria(store, inicio_mes, hoje)
    serie_desp = despesa_repo.serie_diaria(store, inicio_mes, hoje)
    ranking = receita_repo.ranking_servicos(store, inicio_mes, hoje, limite=5)
    mix = receita_repo.mix_forma_pagamento(store, hoje, hoje)

    est_hoje = movimentacao_repo.totais_periodo(store, hoje, hoje)
    est_mes = movimentacao_repo.totais_periodo(store, inicio_mes, hoje)

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
        # Estoque
        est_vendas_hoje=est_hoje["VENDA"]["total"],
        est_vendas_mes=est_mes["VENDA"]["total"],
        est_margem_mes=est_mes["VENDA"]["total"] - est_mes["COMPRA"]["total"],
    )


def _dias_no_periodo(inicio: date, fim: date) -> list[date]:
    dias = []
    atual = inicio
    while atual <= fim:
        dias.append(atual)
        atual += timedelta(days=1)
    return dias
