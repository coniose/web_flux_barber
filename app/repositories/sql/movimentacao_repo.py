"""Repositório de movimentações de estoque — SQLite."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Optional


def _periodo(conn: sqlite3.Connection, de: date | str, ate: date | str) -> list[dict]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    rows = conn.execute(
        "SELECT * FROM movimentacao_estoque WHERE data >= ? AND data <= ? ORDER BY data DESC, id DESC",
        (de_s, ate_s),
    ).fetchall()
    return [dict(r) for r in rows]


def inserir(
    conn: sqlite3.Connection,
    *,
    produto_id: int,
    produto_nome: str = "",
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
               (produto_id, produto_nome, tipo, quantidade, preco_unitario,
                total_centavos, data, observacao)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (produto_id, produto_nome, tipo, quantidade, preco_unitario, total, data_str, observacao),
    )
    return cur.lastrowid


def obter(conn: sqlite3.Connection, mov_id: int) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM movimentacao_estoque WHERE id = ?", (mov_id,)
    ).fetchone()
    return dict(row) if row else None


def excluir(conn: sqlite3.Connection, mov_id: int) -> bool:
    cur = conn.execute("DELETE FROM movimentacao_estoque WHERE id = ?", (mov_id,))
    return cur.rowcount > 0


def listar_periodo(
    conn: sqlite3.Connection,
    de: date | str,
    ate: date | str,
    produto_id: Optional[int] = None,
    tipo: Optional[str] = None,
) -> list[dict]:
    docs = _periodo(conn, de, ate)
    if produto_id is not None:
        docs = [d for d in docs if d.get("produto_id") == produto_id]
    if tipo is not None:
        docs = [d for d in docs if d.get("tipo") == tipo]
    return docs


def totais_periodo(
    conn: sqlite3.Connection, de: date | str, ate: date | str
) -> dict:
    """Retorna totais separados por tipo: {"COMPRA": {total, qtd}, "VENDA": {...}}."""
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    rows = conn.execute(
        """SELECT tipo,
                  COALESCE(SUM(total_centavos), 0) AS total,
                  COALESCE(SUM(ABS(quantidade)), 0) AS qtd
           FROM movimentacao_estoque
           WHERE data >= ? AND data <= ?
           GROUP BY tipo""",
        (de_s, ate_s),
    ).fetchall()

    result: dict = {"COMPRA": {"total": 0, "qtd": 0}, "VENDA": {"total": 0, "qtd": 0}}
    for r in rows:
        tipo = r["tipo"]
        if tipo in result:
            result[tipo]["total"] = r["total"]
            result[tipo]["qtd"] = r["qtd"]
    return result


def margem_periodo(
    conn: sqlite3.Connection, de: date | str, ate: date | str
) -> int:
    totais = totais_periodo(conn, de, ate)
    return totais["VENDA"]["total"] - totais["COMPRA"]["total"]


def ranking_produtos(
    conn: sqlite3.Connection, de: date | str, ate: date | str, limite: int = 10
) -> list[dict]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    rows = conn.execute(
        """SELECT produto_id AS id, produto_nome AS nome,
                  SUM(total_centavos) AS receita_venda,
                  SUM(ABS(quantidade)) AS qtd_vendida
           FROM movimentacao_estoque
           WHERE tipo = 'VENDA' AND data >= ? AND data <= ?
           GROUP BY produto_id, produto_nome
           ORDER BY receita_venda DESC
           LIMIT ?""",
        (de_s, ate_s, limite),
    ).fetchall()
    return [dict(r) for r in rows]
