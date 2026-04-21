"""Testes do schema — tabelas, índices e PRAGMAs."""

from __future__ import annotations

import sqlite3

import pytest


TABELAS_ESPERADAS = {
    "servico",
    "plano_assinatura",
    "plano_servico",
    "cliente",
    "assinatura",
    "pagamento_assinatura",
    "receita",
    "categoria_despesa",
    "item_despesa_frequente",
    "despesa",
    "auditoria",
    "config",
}


def test_todas_as_tabelas_existem(empty_conn: sqlite3.Connection) -> None:
    rows = empty_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    tabelas = {r["name"] for r in rows}
    assert TABELAS_ESPERADAS.issubset(tabelas), f"Faltando: {TABELAS_ESPERADAS - tabelas}"


def test_foreign_keys_ligadas(empty_conn: sqlite3.Connection) -> None:
    assert empty_conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_journal_mode_wal(empty_conn: sqlite3.Connection) -> None:
    mode = empty_conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


def test_schema_eh_idempotente(empty_conn: sqlite3.Connection) -> None:
    """Re-aplicar o schema no mesmo DB não deve dar erro."""
    from app.repositories.db import init_schema

    init_schema(empty_conn)  # não levanta exceção
    init_schema(empty_conn)


def test_indices_principais(empty_conn: sqlite3.Connection) -> None:
    rows = empty_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'"
    ).fetchall()
    nomes = {r["name"] for r in rows}
    esperados = {
        "idx_servico_ativo_ordem",
        "idx_cliente_nome",
        "idx_assinatura_cliente",
        "idx_pgto_assinatura_mes",
        "idx_receita_data",
        "idx_receita_cliente",
        "idx_receita_assinatura",
        "idx_despesa_data",
        "idx_despesa_categoria",
        "idx_item_freq_uso",
    }
    assert esperados.issubset(nomes), f"Índices faltando: {esperados - nomes}"
