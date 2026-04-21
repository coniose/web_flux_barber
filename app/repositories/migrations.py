"""Migrações idempotentes para DBs pré-existentes.

Quando um campo novo entra no ``schema.sql``, bancos já criados em
instalações antigas não recebem automaticamente a coluna (``CREATE TABLE
IF NOT EXISTS`` ignora o novo schema para tabelas existentes). Este
módulo roda **depois** de ``init_schema`` e adiciona incrementalmente o
que falta.

Todas as funções são idempotentes — podem rodar 100x sem efeito colateral.

Princípio geral:
  1. ``PRAGMA table_info(tabela)`` descobre as colunas atuais.
  2. Se a coluna novo nome não existe, fazemos ``ALTER TABLE ADD COLUMN``.
  3. Depois populamos linhas antigas com o valor sensato (uuid gerado,
     ``updated_at`` tirado de ``editado_em`` ou ``criado_em``).
"""

from __future__ import annotations

import sqlite3
import uuid as uuid_lib


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Aplica todas as migrações necessárias neste DB. Chamar após ``init_schema``."""
    _migrar_receita_uuid_updated_at(conn)
    _migrar_despesa_uuid_updated_at(conn)
    _criar_tabela_sync_state(conn)


# ---------------------------------------------------------------------------
# Receita — uuid + updated_at
# ---------------------------------------------------------------------------


def _migrar_receita_uuid_updated_at(conn: sqlite3.Connection) -> None:
    colunas = _colunas(conn, "receita")
    if "uuid" not in colunas:
        conn.execute("ALTER TABLE receita ADD COLUMN uuid TEXT")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_receita_uuid ON receita(uuid)")
        _popular_uuid(conn, "receita")
    if "updated_at" not in colunas:
        # ADD COLUMN em SQLite não aceita DEFAULT com expressão não-constante em
        # versões antigas, mas aceita "CURRENT_TIMESTAMP". Para compatibilidade
        # máxima, adicionamos sem default e populamos manualmente.
        conn.execute("ALTER TABLE receita ADD COLUMN updated_at TEXT")
        conn.execute(
            "UPDATE receita SET updated_at = COALESCE(editado_em, criado_em) "
            "WHERE updated_at IS NULL"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_receita_updated_at ON receita(updated_at)"
        )


# ---------------------------------------------------------------------------
# Despesa — uuid + updated_at
# ---------------------------------------------------------------------------


def _migrar_despesa_uuid_updated_at(conn: sqlite3.Connection) -> None:
    colunas = _colunas(conn, "despesa")
    if "uuid" not in colunas:
        conn.execute("ALTER TABLE despesa ADD COLUMN uuid TEXT")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_despesa_uuid ON despesa(uuid)")
        _popular_uuid(conn, "despesa")
    if "updated_at" not in colunas:
        conn.execute("ALTER TABLE despesa ADD COLUMN updated_at TEXT")
        conn.execute(
            "UPDATE despesa SET updated_at = COALESCE(editado_em, criado_em) "
            "WHERE updated_at IS NULL"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_despesa_updated_at ON despesa(updated_at)"
        )


# ---------------------------------------------------------------------------
# Estado de sincronização — par (tabela, chave) -> timestamp
# ---------------------------------------------------------------------------


def _criar_tabela_sync_state(conn: sqlite3.Connection) -> None:
    """Tabela dedicada ao estado de sync. Mantemos separada de ``config`` para
    ficar claro o que é configuração do usuário vs. estado operacional.
    """
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sync_state (
             tabela         TEXT NOT NULL,
             chave          TEXT NOT NULL,
             valor          TEXT,
             atualizado_em  TEXT NOT NULL DEFAULT (datetime('now')),
             PRIMARY KEY (tabela, chave)
           )"""
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _colunas(conn: sqlite3.Connection, tabela: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({tabela})").fetchall()
    return {r["name"] for r in rows}


def _popular_uuid(conn: sqlite3.Connection, tabela: str) -> None:
    """Gera um UUID4 por linha existente sem uuid. Chamamos depois de ADD COLUMN,
    portanto nunca há conflito com o índice UNIQUE (linhas vêm com NULL).
    """
    rows = conn.execute(f"SELECT id FROM {tabela} WHERE uuid IS NULL").fetchall()
    for r in rows:
        conn.execute(
            f"UPDATE {tabela} SET uuid = ? WHERE id = ?",
            (uuid_lib.uuid4().hex, r["id"]),
        )
