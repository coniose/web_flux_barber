"""Seed inicial do banco SQLite por usuário.

Popula o DB com o catálogo inicial se estiver vazio. Idempotente.
"""

from __future__ import annotations

import sqlite3

from app.repositories.seed import (
    CATEGORIAS_DESPESA,
    CONFIGS,
    ITENS_FREQUENTES,
    SERVICOS,
)


def apply_seed(conn: sqlite3.Connection) -> None:
    """Popula o espaço SQLite do usuário com o catálogo inicial. Idempotente."""
    row = conn.execute("SELECT COUNT(*) FROM servico").fetchone()
    if row[0] > 0:
        return  # já populado

    conn.execute("BEGIN")
    try:
        # Serviços
        conn.executemany(
            "INSERT INTO servico (nome, preco_padrao, categoria_servico, ordem, ativo) VALUES (?, ?, ?, ?, 1)",
            SERVICOS,
        )

        # Categorias de despesa
        conn.executemany(
            "INSERT INTO categoria_despesa (nome, icone, ativo) VALUES (?, ?, 1)",
            CATEGORIAS_DESPESA,
        )

        # Itens frequentes — resolve categoria_id a partir do nome
        categorias = dict(
            conn.execute("SELECT nome, id FROM categoria_despesa").fetchall()
        )
        rows_itens = [
            (desc, categorias[cat_nome], valor)
            for desc, cat_nome, valor in ITENS_FREQUENTES
            if cat_nome in categorias
        ]
        conn.executemany(
            "INSERT INTO item_despesa_frequente (descricao, categoria_id, valor_sugerido, vezes_usado, ativo) VALUES (?, ?, ?, 0, 1)",
            rows_itens,
        )

        # Config
        conn.executemany(
            "INSERT OR IGNORE INTO config (chave, valor) VALUES (?, ?)",
            CONFIGS,
        )

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
