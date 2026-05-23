"""Repositório de serviços — SQLite."""

from __future__ import annotations

import sqlite3
from typing import Optional

from app.utils.validators import ValidacaoError


def listar_ativos(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM servico WHERE ativo = 1 ORDER BY ordem, nome"
    ).fetchall()
    return [dict(r) for r in rows]


def listar_todos(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM servico ORDER BY (CASE WHEN ativo=1 THEN 0 ELSE 1 END), ordem, nome"
    ).fetchall()
    return [dict(r) for r in rows]


def obter(conn: sqlite3.Connection, servico_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM servico WHERE id = ?", (servico_id,)).fetchone()
    return dict(row) if row else None


def criar(
    conn: sqlite3.Connection,
    nome: str,
    preco_padrao: int,
    categoria_servico: Optional[str] = None,
    ordem: int = 999,
) -> int:
    existing = conn.execute(
        "SELECT id FROM servico WHERE nome = ?", (nome,)
    ).fetchone()
    if existing:
        raise ValidacaoError(f"Já existe um serviço com o nome '{nome}'.")

    cur = conn.execute(
        """INSERT INTO servico (nome, preco_padrao, categoria_servico, ordem, ativo)
           VALUES (?, ?, ?, ?, 1)""",
        (nome, preco_padrao, categoria_servico, ordem),
    )
    return cur.lastrowid


def atualizar(
    conn: sqlite3.Connection,
    servico_id: int,
    *,
    nome: Optional[str] = None,
    preco_padrao: Optional[int] = None,
    categoria_servico: Optional[str] = None,
    ordem: Optional[int] = None,
    ativo: Optional[bool] = None,
) -> bool:
    row = conn.execute("SELECT id FROM servico WHERE id = ?", (servico_id,)).fetchone()
    if not row:
        return False

    sets = []
    params = []
    if nome is not None:
        sets.append("nome = ?")
        params.append(nome)
    if preco_padrao is not None:
        sets.append("preco_padrao = ?")
        params.append(preco_padrao)
    if categoria_servico is not None:
        sets.append("categoria_servico = ?")
        params.append(categoria_servico)
    if ordem is not None:
        sets.append("ordem = ?")
        params.append(ordem)
    if ativo is not None:
        sets.append("ativo = ?")
        params.append(1 if ativo else 0)

    if not sets:
        return False

    params.append(servico_id)
    conn.execute(f"UPDATE servico SET {', '.join(sets)} WHERE id = ?", params)
    return True
