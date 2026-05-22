"""Repositório de movimentações de estoque."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Optional


def inserir(
    conn: sqlite3.Connection,
    *,
    produto_id: int,
    tipo: str,
    quantidade: int,
    preco_unitario: int,
    data_mov: date | str,
    observacao: Optional[str] = None,
) -> int:
    data_str = data_mov.isoformat() if isinstance(data_mov, date) else data_mov
    total = abs(quantidade) * preco_unitario
    cur = conn.execute(
        """INSERT INTO movimentacao_estoque
             (produto_id, tipo, quantidade, preco_unitario, total_centavos, data, observacao)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (produto_id, tipo, quantidade, preco_unitario, total, data_str, observacao),
    )
    return cur.lastrowid


def listar_periodo(
    conn: sqlite3.Connection,
    de: date | str,
    ate: date | str,
    produto_id: Optional[int] = None,
    tipo: Optional[str] = None,
) -> list[sqlite3.Row]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    sql = """SELECT m.*, p.nome AS produto_nome
               FROM movimentacao_estoque m
               JOIN produto p ON p.id = m.produto_id
              WHERE m.data BETWEEN ? AND ?"""
    params: list = [de_s, ate_s]
    if produto_id is not None:
        sql += " AND m.produto_id = ?"; params.append(produto_id)
    if tipo is not None:
        sql += " AND m.tipo = ?"; params.append(tipo)
    sql += " ORDER BY m.data DESC, m.id DESC"
    return conn.execute(sql, params).fetchall()


def totais_periodo(
    conn: sqlite3.Connection,
    de: date | str,
    ate: date | str,
) -> dict:
    """Retorna totais separados por tipo para o período."""
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    rows = conn.execute(
        """SELECT tipo,
                  COALESCE(SUM(total_centavos), 0) AS total,
                  COALESCE(SUM(ABS(quantidade)), 0) AS qtd
             FROM movimentacao_estoque
            WHERE data BETWEEN ? AND ?
            GROUP BY tipo""",
        (de_s, ate_s),
    ).fetchall()
    result = {"COMPRA": {"total": 0, "qtd": 0}, "VENDA": {"total": 0, "qtd": 0}}
    for r in rows:
        if r["tipo"] in result:
            result[r["tipo"]] = {"total": r["total"], "qtd": r["qtd"]}
    return result


def margem_periodo(
    conn: sqlite3.Connection,
    de: date | str,
    ate: date | str,
) -> int:
    """Receita de vendas menos custo de compras no período (centavos)."""
    totais = totais_periodo(conn, de, ate)
    return totais["VENDA"]["total"] - totais["COMPRA"]["total"]


def ranking_produtos(
    conn: sqlite3.Connection,
    de: date | str,
    ate: date | str,
    limite: int = 10,
) -> list[sqlite3.Row]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    return conn.execute(
        """SELECT p.id, p.nome,
                  COALESCE(SUM(CASE WHEN m.tipo='VENDA' THEN m.total_centavos ELSE 0 END), 0) AS receita_venda,
                  COALESCE(SUM(CASE WHEN m.tipo='VENDA' THEN ABS(m.quantidade) ELSE 0 END), 0) AS qtd_vendida
             FROM movimentacao_estoque m
             JOIN produto p ON p.id = m.produto_id
            WHERE m.data BETWEEN ? AND ? AND m.tipo = 'VENDA'
            GROUP BY p.id, p.nome
            ORDER BY receita_venda DESC
            LIMIT ?""",
        (de_s, ate_s, limite),
    ).fetchall()
