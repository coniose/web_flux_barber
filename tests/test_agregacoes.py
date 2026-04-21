"""Testes das agregações usadas pelo Dashboard."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from app.domain.enums import FormaPagamento
from app.services import despesa_service, receita_service
from app.utils.validators import ValidacaoError


def _servico_id(conn: sqlite3.Connection, nome: str) -> int:
    return conn.execute("SELECT id FROM servico WHERE nome = ?", (nome,)).fetchone()["id"]


def _categoria_id(conn: sqlite3.Connection, nome: str) -> int:
    return conn.execute(
        "SELECT id FROM categoria_despesa WHERE nome = ?", (nome,)
    ).fetchone()["id"]


# ---------------------------------------------------------------------------
# Série diária de receita
# ---------------------------------------------------------------------------


def test_serie_diaria_receita_vazia(conn: sqlite3.Connection) -> None:
    hoje = date.today()
    serie = receita_service.serie_diaria_receita(conn, hoje, hoje)
    assert serie == []


def test_serie_diaria_receita_agrupa_por_data(conn: sqlite3.Connection) -> None:
    sid = _servico_id(conn, "Corte de cabelo")
    hoje = date.today()
    ontem = hoje - timedelta(days=1)

    # 2 atendimentos hoje, 1 ontem
    receita_service.registrar_atendimento_avulso(
        conn, servico_id=sid, valor_centavos=3500, forma_pagamento=FormaPagamento.PIX,
    )
    receita_service.registrar_atendimento_avulso(
        conn, servico_id=sid, valor_centavos=4000, forma_pagamento=FormaPagamento.PIX,
    )
    receita_service.registrar_atendimento_avulso(
        conn, servico_id=sid, valor_centavos=5000, forma_pagamento=FormaPagamento.PIX,
        data_atendimento=ontem,
    )

    serie = receita_service.serie_diaria_receita(conn, ontem, hoje)
    assert len(serie) == 2

    por_data = {r["data"]: r for r in serie}
    assert por_data[ontem.isoformat()]["total"] == 5000
    assert por_data[ontem.isoformat()]["qtd"] == 1
    assert por_data[hoje.isoformat()]["total"] == 7500
    assert por_data[hoje.isoformat()]["qtd"] == 2


def test_serie_diaria_receita_ordenada_crescente(conn: sqlite3.Connection) -> None:
    sid = _servico_id(conn, "Corte de cabelo")
    hoje = date.today()
    for i, v in enumerate([3500, 4000, 4500], start=1):
        receita_service.registrar_atendimento_avulso(
            conn, servico_id=sid, valor_centavos=v,
            forma_pagamento=FormaPagamento.PIX,
            data_atendimento=hoje - timedelta(days=3 - i),
        )
    serie = receita_service.serie_diaria_receita(conn, hoje - timedelta(days=3), hoje)
    datas = [r["data"] for r in serie]
    assert datas == sorted(datas)


def test_serie_diaria_receita_periodo_invalido(conn: sqlite3.Connection) -> None:
    with pytest.raises(ValidacaoError, match="anterior"):
        receita_service.serie_diaria_receita(conn, date(2026, 5, 1), date(2026, 4, 1))


# ---------------------------------------------------------------------------
# Ranking de serviços
# ---------------------------------------------------------------------------


def test_ranking_servicos_ordena_por_total(conn: sqlite3.Connection) -> None:
    corte = _servico_id(conn, "Corte de cabelo")
    barba = _servico_id(conn, "Barba")
    # Corte: 2x R$40 = R$80
    # Barba: 1x R$30 = R$30
    for _ in range(2):
        receita_service.registrar_atendimento_avulso(
            conn, servico_id=corte, valor_centavos=4000,
            forma_pagamento=FormaPagamento.PIX,
        )
    receita_service.registrar_atendimento_avulso(
        conn, servico_id=barba, valor_centavos=3000,
        forma_pagamento=FormaPagamento.PIX,
    )
    hoje = date.today()
    ranking = receita_service.ranking_servicos(conn, hoje, hoje)
    assert ranking[0]["servico_nome"] == "Corte de cabelo"
    assert ranking[0]["total"] == 8000
    assert ranking[0]["qtd"] == 2
    assert ranking[1]["servico_nome"] == "Barba"
    assert ranking[1]["total"] == 3000


def test_ranking_servicos_respeita_limite(conn: sqlite3.Connection) -> None:
    servicos = conn.execute("SELECT id FROM servico ORDER BY ordem LIMIT 5").fetchall()
    for s in servicos:
        receita_service.registrar_atendimento_avulso(
            conn, servico_id=s["id"], valor_centavos=2000,
            forma_pagamento=FormaPagamento.PIX,
        )
    hoje = date.today()
    ranking = receita_service.ranking_servicos(conn, hoje, hoje, limite=3)
    assert len(ranking) == 3


def test_ranking_servicos_vazio(conn: sqlite3.Connection) -> None:
    hoje = date.today()
    assert receita_service.ranking_servicos(conn, hoje, hoje) == []


# ---------------------------------------------------------------------------
# Mix por forma de pagamento
# ---------------------------------------------------------------------------


def test_mix_forma_pagamento(conn: sqlite3.Connection) -> None:
    sid = _servico_id(conn, "Corte de cabelo")
    # 3 PIX, 2 Dinheiro, 1 Maquininha
    for _ in range(3):
        receita_service.registrar_atendimento_avulso(
            conn, servico_id=sid, valor_centavos=4000,
            forma_pagamento=FormaPagamento.PIX,
        )
    for _ in range(2):
        receita_service.registrar_atendimento_avulso(
            conn, servico_id=sid, valor_centavos=4000,
            forma_pagamento=FormaPagamento.DINHEIRO,
        )
    receita_service.registrar_atendimento_avulso(
        conn, servico_id=sid, valor_centavos=4000,
        forma_pagamento=FormaPagamento.MAQUININHA,
    )
    hoje = date.today()
    mix = receita_service.mix_forma_pagamento(conn, hoje, hoje)
    formas = {m["forma"]: m for m in mix}
    assert formas["PIX"]["qtd"] == 3
    assert formas["PIX"]["total"] == 12000
    assert formas["DINHEIRO"]["qtd"] == 2
    assert formas["MAQUININHA"]["qtd"] == 1


# ---------------------------------------------------------------------------
# Despesas — série diária e por categoria
# ---------------------------------------------------------------------------


def test_serie_diaria_despesa(conn: sqlite3.Connection) -> None:
    cat = _categoria_id(conn, "Outros")
    hoje = date.today()
    ontem = hoje - timedelta(days=1)
    despesa_service.registrar_despesa(
        conn, categoria_id=cat, descricao="hoje A",
        valor_centavos=1000, forma_pagamento=FormaPagamento.PIX,
    )
    despesa_service.registrar_despesa(
        conn, categoria_id=cat, descricao="hoje B",
        valor_centavos=2500, forma_pagamento=FormaPagamento.PIX,
    )
    despesa_service.registrar_despesa(
        conn, categoria_id=cat, descricao="ontem",
        valor_centavos=5000, forma_pagamento=FormaPagamento.PIX,
        data_despesa=ontem,
    )
    serie = despesa_service.serie_diaria_despesa(conn, ontem, hoje)
    por_data = {r["data"]: r for r in serie}
    assert por_data[hoje.isoformat()]["total"] == 3500
    assert por_data[hoje.isoformat()]["qtd"] == 2
    assert por_data[ontem.isoformat()]["total"] == 5000


def test_total_por_categoria(conn: sqlite3.Connection) -> None:
    cat_ins = _categoria_id(conn, "Insumos / Produtos")
    cat_beb = _categoria_id(conn, "Bebidas & Alimentos")
    despesa_service.registrar_despesa(
        conn, categoria_id=cat_ins, descricao="Lâmina",
        valor_centavos=3000, forma_pagamento=FormaPagamento.PIX,
    )
    despesa_service.registrar_despesa(
        conn, categoria_id=cat_ins, descricao="Pomada",
        valor_centavos=7000, forma_pagamento=FormaPagamento.PIX,
    )
    despesa_service.registrar_despesa(
        conn, categoria_id=cat_beb, descricao="Café",
        valor_centavos=4000, forma_pagamento=FormaPagamento.PIX,
    )
    hoje = date.today()
    tot = despesa_service.total_por_categoria(conn, hoje, hoje)
    por_nome = {r["categoria_nome"]: r for r in tot}
    assert por_nome["Insumos / Produtos"]["total"] == 10000
    assert por_nome["Insumos / Produtos"]["qtd"] == 2
    assert por_nome["Bebidas & Alimentos"]["total"] == 4000


def test_total_por_categoria_ordena_por_total_desc(conn: sqlite3.Connection) -> None:
    cat_out = _categoria_id(conn, "Outros")
    cat_ins = _categoria_id(conn, "Insumos / Produtos")
    despesa_service.registrar_despesa(
        conn, categoria_id=cat_out, descricao="x", valor_centavos=1000,
        forma_pagamento=FormaPagamento.PIX,
    )
    despesa_service.registrar_despesa(
        conn, categoria_id=cat_ins, descricao="y", valor_centavos=9000,
        forma_pagamento=FormaPagamento.PIX,
    )
    hoje = date.today()
    tot = despesa_service.total_por_categoria(conn, hoje, hoje)
    assert tot[0]["categoria_nome"] == "Insumos / Produtos"
    assert tot[0]["total"] == 9000
