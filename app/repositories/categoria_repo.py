"""Repositório de categorias de despesa."""

from __future__ import annotations

import sqlite3
from typing import Optional

from app.repositories.audit import log_audit, row_to_dict


def listar_ativas(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM categoria_despesa WHERE ativo = 1 ORDER BY nome"
    ).fetchall()


def listar_todas(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM categoria_despesa ORDER BY ativo DESC, nome"
    ).fetchall()


def obter(conn: sqlite3.Connection, categoria_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM categoria_despesa WHERE id = ?", (categoria_id,)
    ).fetchone()


def criar(conn: sqlite3.Connection, nome: str, icone: Optional[str] = None) -> int:
    cur = conn.execute(
        "INSERT INTO categoria_despesa (nome, icone) VALUES (?, ?)",
        (nome, icone),
    )
    new_id = cur.lastrowid
    log_audit(conn, "categoria_despesa", new_id, "INSERT", {"nome": nome, "icone": icone})
    return new_id


def atualizar(
    conn: sqlite3.Connection,
    categoria_id: int,
    *,
    nome: Optional[str] = None,
    icone: Optional[str] = None,
    ativo: Optional[bool] = None,
) -> bool:
    antes = obter(conn, categoria_id)
    if antes is None:
        return False

    campos = []
    valores: list = []
    if nome is not None:
        campos.append("nome = ?"); valores.append(nome)
    if icone is not None:
        campos.append("icone = ?"); valores.append(icone)
    if ativo is not None:
        campos.append("ativo = ?"); valores.append(1 if ativo else 0)

    if not campos:
        return False

    valores.append(categoria_id)
    conn.execute(
        f"UPDATE categoria_despesa SET {', '.join(campos)} WHERE id = ?", valores
    )
    log_audit(conn, "categoria_despesa", categoria_id, "UPDATE", row_to_dict(antes))
    return True
