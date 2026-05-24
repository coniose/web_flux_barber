"""Rastreamento de consumo de tokens da API Claude por usuário."""

from __future__ import annotations

import sqlite3
from datetime import date


LIMITE_TOKENS_DIA_PRO = 150_000  # ~300–400 mensagens com contexto moderado


def get_tokens_hoje(conn: sqlite3.Connection, user_id: int) -> int:
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT COALESCE(SUM(tokens_entrada + tokens_saida), 0) AS total "
        "FROM consumo_chat WHERE user_id = ? AND data = ?",
        (user_id, today),
    ).fetchone()
    return int(row["total"]) if row else 0


def registrar(
    conn: sqlite3.Connection,
    user_id: int,
    tokens_entrada: int,
    tokens_saida: int,
) -> None:
    today = date.today().isoformat()
    conn.execute(
        "INSERT INTO consumo_chat (user_id, data, tokens_entrada, tokens_saida) "
        "VALUES (?, ?, ?, ?)",
        (user_id, today, tokens_entrada, tokens_saida),
    )


def resumo_usuario(conn: sqlite3.Connection, user_id: int, dias: int = 30) -> list[dict]:
    """Retorna consumo diário dos últimos N dias (para painel admin futuro)."""
    rows = conn.execute(
        "SELECT data, SUM(tokens_entrada) AS entrada, SUM(tokens_saida) AS saida "
        "FROM consumo_chat WHERE user_id = ? "
        "AND data >= date('now', ? || ' days') "
        "GROUP BY data ORDER BY data DESC",
        (user_id, f"-{dias}"),
    ).fetchall()
    return [dict(r) for r in rows]
