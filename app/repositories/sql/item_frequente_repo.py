"""Repositório de itens frequentes de despesa — SQLite."""

from __future__ import annotations

import sqlite3
from typing import Optional

from app.utils.validators import ValidacaoError


def listar_ativos_ordenado_por_uso(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """SELECT * FROM item_despesa_frequente
           WHERE ativo = 1
           ORDER BY vezes_usado DESC, descricao"""
    ).fetchall()
    return [dict(r) for r in rows]


def listar_todos(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """SELECT * FROM item_despesa_frequente
           ORDER BY (CASE WHEN ativo=1 THEN 0 ELSE 1 END), descricao"""
    ).fetchall()
    return [dict(r) for r in rows]


def obter(conn: sqlite3.Connection, item_id: int) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM item_despesa_frequente WHERE id = ?", (item_id,)
    ).fetchone()
    return dict(row) if row else None


def criar(
    conn: sqlite3.Connection,
    descricao: str,
    categoria_id: int,
    valor_sugerido: Optional[int] = None,
) -> int:
    cur = conn.execute(
        """INSERT INTO item_despesa_frequente (descricao, categoria_id, valor_sugerido, vezes_usado, ativo)
           VALUES (?, ?, ?, 0, 1)""",
        (descricao, categoria_id, valor_sugerido),
    )
    return cur.lastrowid


def atualizar(
    conn: sqlite3.Connection,
    item_id: int,
    *,
    descricao: Optional[str] = None,
    categoria_id: Optional[int] = None,
    valor_sugerido: Optional[int] = None,
    ativo: Optional[bool] = None,
) -> bool:
    row = conn.execute(
        "SELECT id FROM item_despesa_frequente WHERE id = ?", (item_id,)
    ).fetchone()
    if not row:
        return False

    sets = []
    params = []
    if descricao is not None:
        sets.append("descricao = ?")
        params.append(descricao)
    if categoria_id is not None:
        sets.append("categoria_id = ?")
        params.append(categoria_id)
    if valor_sugerido is not None:
        sets.append("valor_sugerido = ?")
        params.append(valor_sugerido)
    if ativo is not None:
        sets.append("ativo = ?")
        params.append(1 if ativo else 0)

    if not sets:
        return False

    params.append(item_id)
    conn.execute(
        f"UPDATE item_despesa_frequente SET {', '.join(sets)} WHERE id = ?", params
    )
    return True


def bump_uso(conn: sqlite3.Connection, item_id: int) -> None:
    """Incrementa o contador de uso do item."""
    conn.execute(
        "UPDATE item_despesa_frequente SET vezes_usado = vezes_usado + 1 WHERE id = ?",
        (item_id,),
    )
