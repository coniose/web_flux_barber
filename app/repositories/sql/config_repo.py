"""Repositório de configurações chave-valor — SQLite."""

from __future__ import annotations

import sqlite3
from typing import Optional


def get_config(conn: sqlite3.Connection, chave: str) -> Optional[str]:
    row = conn.execute(
        "SELECT valor FROM config WHERE chave = ?", (chave,)
    ).fetchone()
    return row["valor"] if row else None


def set_config(conn: sqlite3.Connection, chave: str, valor: str) -> None:
    conn.execute(
        "INSERT INTO config (chave, valor) VALUES (?, ?)"
        " ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
        (chave, valor),
    )
