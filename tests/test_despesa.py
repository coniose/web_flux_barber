"""Testes integrados do fluxo de despesas (repo + service + item_frequente)."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from app.domain.enums import FormaPagamento
from app.repositories import categoria_repo, despesa_repo, item_frequente_repo
from app.services import despesa_service
from app.utils.validators import ValidacaoError


def _categoria_id(conn: sqlite3.Connection, nome: str) -> int:
    return conn.execute(
        "SELECT id FROM categoria_despesa WHERE nome = ?", (nome,)
    ).fetchone()["id"]


def _item_id(conn: sqlite3.Connection, descricao: str) -> int:
    return conn.execute(
        "SELECT id FROM item_despesa_frequente WHERE descricao = ?", (descricao,)
    ).fetchone()["id"]


def test_registrar_despesa_generica(conn: sqlite3.Connection) -> None:
    cat = _categoria_id(conn, "Outros")
    did = despesa_service.registrar_despesa(
        conn,
        categoria_id=cat,
        descricao="pagamento caixa",
        valor_centavos=5000,
        forma_pagamento=FormaPagamento.DINHEIRO,
    )
    row = despesa_repo.obter(conn, did)
    assert row["valor"] == 5000
    assert row["item_frequente_id"] is None


def test_registrar_item_frequente_incrementa_uso(conn: sqlite3.Connection) -> None:
    iid = _item_id(conn, "Lâmina")
    antes = item_frequente_repo.obter(conn, iid)["vezes_usado"]

    did = despesa_service.registrar_item_frequente(
        conn, iid, forma_pagamento=FormaPagamento.DINHEIRO
    )
    assert did > 0

    depois = item_frequente_repo.obter(conn, iid)["vezes_usado"]
    assert depois == antes + 1

    row = despesa_repo.obter(conn, did)
    assert row["valor"] == 3000                # valor_sugerido
    assert row["descricao"] == "Lâmina"
    assert row["item_frequente_id"] == iid


def test_item_frequente_ordena_por_uso(conn: sqlite3.Connection) -> None:
    """Itens mais usados aparecem primeiro na listagem ordenada."""
    cafe = _item_id(conn, "Café")
    # Usa café 3 vezes
    for _ in range(3):
        despesa_service.registrar_item_frequente(
            conn, cafe, forma_pagamento=FormaPagamento.PIX
        )
    lista = item_frequente_repo.listar_ativos_ordenado_por_uso(conn)
    assert lista[0]["descricao"] == "Café"
    assert lista[0]["vezes_usado"] == 3


def test_descricao_vazia_rejeita(conn: sqlite3.Connection) -> None:
    cat = _categoria_id(conn, "Outros")
    with pytest.raises(ValidacaoError, match="descri"):
        despesa_service.registrar_despesa(
            conn, categoria_id=cat, descricao="   ",
            valor_centavos=1000, forma_pagamento=FormaPagamento.PIX,
        )


def test_categoria_inexistente_rejeita(conn: sqlite3.Connection) -> None:
    with pytest.raises(ValidacaoError, match="Categoria"):
        despesa_service.registrar_despesa(
            conn, categoria_id=99999, descricao="x",
            valor_centavos=1000, forma_pagamento=FormaPagamento.PIX,
        )


def test_valor_zero_rejeita(conn: sqlite3.Connection) -> None:
    cat = _categoria_id(conn, "Outros")
    with pytest.raises(ValidacaoError, match="maior que zero"):
        despesa_service.registrar_despesa(
            conn, categoria_id=cat, descricao="x", valor_centavos=0,
            forma_pagamento=FormaPagamento.PIX,
        )


def test_listar_periodo_filtro_categoria(conn: sqlite3.Connection) -> None:
    cat_insumos = _categoria_id(conn, "Insumos / Produtos")
    cat_bebidas = _categoria_id(conn, "Bebidas & Alimentos")
    despesa_service.registrar_despesa(
        conn, categoria_id=cat_insumos, descricao="Lâmina",
        valor_centavos=3000, forma_pagamento=FormaPagamento.DINHEIRO,
    )
    despesa_service.registrar_despesa(
        conn, categoria_id=cat_bebidas, descricao="Café",
        valor_centavos=5500, forma_pagamento=FormaPagamento.PIX,
    )

    todas = despesa_service.listar_periodo(conn, date.today(), date.today())
    assert len(todas) == 2

    apenas_insumos = despesa_service.listar_periodo(
        conn, date.today(), date.today(), categoria_id=cat_insumos
    )
    assert len(apenas_insumos) == 1
    assert apenas_insumos[0]["descricao"] == "Lâmina"


def test_totais_periodo_despesa(conn: sqlite3.Connection) -> None:
    cat = _categoria_id(conn, "Outros")
    despesa_service.registrar_despesa(
        conn, categoria_id=cat, descricao="a", valor_centavos=1000,
        forma_pagamento=FormaPagamento.PIX,
    )
    despesa_service.registrar_despesa(
        conn, categoria_id=cat, descricao="b", valor_centavos=2500,
        forma_pagamento=FormaPagamento.PIX,
    )
    r = despesa_service.totais_periodo(conn, date.today(), date.today())
    assert r == {"total_centavos": 3500, "qtd_despesas": 2}


def test_excluir_despesa_grava_auditoria(conn: sqlite3.Connection) -> None:
    cat = _categoria_id(conn, "Outros")
    did = despesa_service.registrar_despesa(
        conn, categoria_id=cat, descricao="teste", valor_centavos=1000,
        forma_pagamento=FormaPagamento.PIX,
    )
    assert despesa_service.excluir_despesa(conn, did)
    assert despesa_repo.obter(conn, did) is None
    n = conn.execute(
        "SELECT COUNT(*) FROM auditoria WHERE tabela='despesa' AND registro_id=? AND acao='DELETE'",
        (did,),
    ).fetchone()[0]
    assert n == 1


def test_editar_despesa(conn: sqlite3.Connection) -> None:
    cat = _categoria_id(conn, "Outros")
    did = despesa_service.registrar_despesa(
        conn, categoria_id=cat, descricao="x", valor_centavos=1000,
        forma_pagamento=FormaPagamento.PIX,
    )
    assert despesa_service.editar_despesa(conn, did, valor_centavos=1500)
    assert despesa_repo.obter(conn, did)["valor"] == 1500


def test_categoria_repo_listar_ativas(conn: sqlite3.Connection) -> None:
    ativas = categoria_repo.listar_ativas(conn)
    assert len(ativas) == 7
