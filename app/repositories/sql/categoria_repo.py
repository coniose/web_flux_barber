"""Repositório de categorias de despesa — SQLite."""

from __future__ import annotations

import sqlite3
from typing import Optional

from app.utils.validators import ValidacaoError


def listar_ativas(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM categoria_despesa WHERE ativo = 1 ORDER BY nome"
    ).fetchall()
    return [dict(r) for r in rows]


def listar_todas(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM categoria_despesa ORDER BY (CASE WHEN ativo=1 THEN 0 ELSE 1 END), nome"
    ).fetchall()
    return [dict(r) for r in rows]


def obter(conn: sqlite3.Connection, categoria_id: int) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM categoria_despesa WHERE id = ?", (categoria_id,)
    ).fetchone()
    return dict(row) if row else None


def criar(conn: sqlite3.Connection, nome: str, icone: str = "📦") -> int:
    existing = conn.execute(
        "SELECT id FROM categoria_despesa WHERE nome = ?", (nome,)
    ).fetchone()
    if existing:
        raise ValidacaoError(f"Já existe uma categoria com o nome '{nome}'.")

    cur = conn.execute(
        "INSERT INTO categoria_despesa (nome, icone, ativo) VALUES (?, ?, 1)",
        (nome, icone),
    )
    return cur.lastrowid


def atualizar(
    conn: sqlite3.Connection,
    categoria_id: int,
    *,
    nome: Optional[str] = None,
    icone: Optional[str] = None,
    ativo: Optional[bool] = None,
) -> bool:
    row = conn.execute(
        "SELECT id FROM categoria_despesa WHERE id = ?", (categoria_id,)
    ).fetchone()
    if not row:
        return False

    sets = []
    params = []
    if nome is not None:
        sets.append("nome = ?")
        params.append(nome)
    if icone is not None:
        sets.append("icone = ?")
        params.append(icone)
    if ativo is not None:
        sets.append("ativo = ?")
        params.append(1 if ativo else 0)

    if not sets:
        return False

    params.append(categoria_id)
    conn.execute(f"UPDATE categoria_despesa SET {', '.join(sets)} WHERE id = ?", params)
    return True
