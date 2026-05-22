"""Repositório de produtos (catálogo do estoque)."""

from __future__ import annotations

import sqlite3
from typing import Optional


def inserir(
    conn: sqlite3.Connection,
    *,
    nome: str,
    preco_custo: int,
    preco_venda: int,
    descricao: Optional[str] = None,
    quantidade_inicial: int = 0,
) -> int:
    cur = conn.execute(
        """INSERT INTO produto (nome, descricao, preco_custo, preco_venda, quantidade_estoque)
           VALUES (?, ?, ?, ?, ?)""",
        (nome.strip(), descricao, preco_custo, preco_venda, quantidade_inicial),
    )
    return cur.lastrowid


def obter(conn: sqlite3.Connection, produto_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM produto WHERE id = ?", (produto_id,)).fetchone()


def listar_ativos(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM produto WHERE ativo = 1 ORDER BY nome"
    ).fetchall()


def listar_todos(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM produto ORDER BY ativo DESC, nome").fetchall()


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
    campos, valores = [], []
    if nome is not None:
        campos.append("nome = ?"); valores.append(nome.strip())
    if descricao is not None:
        campos.append("descricao = ?"); valores.append(descricao)
    if preco_custo is not None:
        campos.append("preco_custo = ?"); valores.append(preco_custo)
    if preco_venda is not None:
        campos.append("preco_venda = ?"); valores.append(preco_venda)
    if ativo is not None:
        campos.append("ativo = ?"); valores.append(ativo)
    if not campos:
        return False
    valores.append(produto_id)
    conn.execute(f"UPDATE produto SET {', '.join(campos)} WHERE id = ?", valores)
    return True


def ajustar_quantidade(conn: sqlite3.Connection, produto_id: int, delta: int) -> None:
    """Incrementa (delta > 0) ou decrementa (delta < 0) o estoque."""
    conn.execute(
        "UPDATE produto SET quantidade_estoque = quantidade_estoque + ? WHERE id = ?",
        (delta, produto_id),
    )
