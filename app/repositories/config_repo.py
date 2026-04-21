"""Repositório chave-valor de configuração."""

from __future__ import annotations

import sqlite3
from typing import Optional


def obter(conn: sqlite3.Connection, chave: str, padrao: Optional[str] = None) -> Optional[str]:
    row = conn.execute("SELECT valor FROM config WHERE chave = ?", (chave,)).fetchone()
    return row["valor"] if row is not None else padrao


def definir(conn: sqlite3.Connection, chave: str, valor: str) -> None:
    conn.execute(
        """INSERT INTO config (chave, valor) VALUES (?, ?)
           ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor""",
        (chave, valor),
    )


def obter_todos(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT chave, valor FROM config").fetchall()
    return {r["chave"]: r["valor"] for r in rows}
