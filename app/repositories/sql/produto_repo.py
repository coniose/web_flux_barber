"""Repositório de produtos (estoque) — SQLite."""

from __future__ import annotations

import sqlite3
from typing import Optional

from app.utils.validators import ValidacaoError


def inserir(
    conn: sqlite3.Connection,
    *,
    nome: str,
    preco_custo: int,
    preco_venda: int,
    descricao: Optional[str] = None,
    quantidade_inicial: int = 0,
) -> int:
    existing = conn.execute(
        "SELECT id FROM produto WHERE nome = ?", (nome.strip(),)
    ).fetchone()
    if existing:
        raise ValidacaoError(f"Produto '{nome}' já existe no catálogo.")

    cur = conn.execute(
        """INSERT INTO produto (nome, descricao, preco_custo, preco_venda, quantidade_estoque, ativo)
           VALUES (?, ?, ?, ?, ?, 1)""",
        (nome.strip(), descricao, preco_custo, preco_venda, quantidade_inicial),
    )
    return cur.lastrowid


def obter(conn: sqlite3.Connection, produto_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM produto WHERE id = ?", (produto_id,)).fetchone()
    return dict(row) if row else None


def listar_ativos(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM produto WHERE ativo = 1 ORDER BY nome"
    ).fetchall()
    return [dict(r) for r in rows]


def listar_todos(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM produto ORDER BY (CASE WHEN ativo=1 THEN 0 ELSE 1 END), nome"
    ).fetchall()
    return [dict(r) for r in rows]


def atualizar(
    conn: sqlite3.Connection,
    produto_id: int,
    *,
    nome: Optional[str] = None,
    descricao: Optional[str] = None,
    preco_custo: Optional[int] = None,
    preco_venda: Optional[int] = None,
    ativo: Optional[int] = None,
) -> bool:
    row = conn.execute("SELECT id FROM produto WHERE id = ?", (produto_id,)).fetchone()
    if not row:
        return False

    sets = []
    params = []
    if nome is not None:
        sets.append("nome = ?")
        params.append(nome.strip())
    if descricao is not None:
        sets.append("descricao = ?")
        params.append(descricao)
    if preco_custo is not None:
        sets.append("preco_custo = ?")
        params.append(preco_custo)
    if preco_venda is not None:
        sets.append("preco_venda = ?")
        params.append(preco_venda)
    if ativo is not None:
        sets.append("ativo = ?")
        params.append(1 if ativo else 0)

    if not sets:
        return False

    params.append(produto_id)
    conn.execute(f"UPDATE produto SET {', '.join(sets)} WHERE id = ?", params)
    return True


def ajustar_quantidade(conn: sqlite3.Connection, produto_id: int, delta: int) -> None:
    """Incrementa (delta > 0) ou decrementa (delta < 0) o estoque atomicamente."""
    conn.execute(
        "UPDATE produto SET quantidade_estoque = quantidade_estoque + ? WHERE id = ?",
        (delta, produto_id),
    )
