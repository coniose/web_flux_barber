"""Repositório de despesas — SQLite."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Optional


def _periodo(conn: sqlite3.Connection, de: date | str, ate: date | str) -> list[dict]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    rows = conn.execute(
        "SELECT * FROM despesa WHERE data >= ? AND data <= ? ORDER BY data DESC, id DESC",
        (de_s, ate_s),
    ).fetchall()
    return [dict(r) for r in rows]


def inserir(
    conn: sqlite3.Connection,
    *,
    data_despesa: date | str,
    categoria_id: int,
    categoria_nome: str = "",
    categoria_icone: str = "📦",
    descricao: str,
    valor: int,
    forma_pagamento: str,
    item_frequente_id: Optional[int] = None,
) -> int:
    data_str = data_despesa.isoformat() if isinstance(data_despesa, date) else data_despesa
    cur = conn.execute(
        """INSERT INTO despesa
               (data, categoria_id, categoria_nome, categoria_icone,
                item_frequente_id, descricao, valor, forma_pagamento)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (data_str, categoria_id, categoria_nome, categoria_icone,
         item_frequente_id, descricao, valor, forma_pagamento),
    )
    return cur.lastrowid


def obter(conn: sqlite3.Connection, despesa_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM despesa WHERE id = ?", (despesa_id,)).fetchone()
    return dict(row) if row else None


def listar_periodo(
    conn: sqlite3.Connection,
    de: date | str,
    ate: date | str,
    categoria_id: Optional[int] = None,
) -> list[dict]:
    docs = _periodo(conn, de, ate)
    if categoria_id is not None:
        docs = [d for d in docs if d.get("categoria_id") == categoria_id]
    return docs


def total_periodo(
    conn: sqlite3.Connection, de: date | str, ate: date | str
) -> tuple[int, int]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    row = conn.execute(
        "SELECT COALESCE(SUM(valor), 0), COUNT(*) FROM despesa WHERE data >= ? AND data <= ?",
        (de_s, ate_s),
    ).fetchone()
    return int(row[0]), int(row[1])


def atualizar(
    conn: sqlite3.Connection,
    despesa_id: int,
    *,
    data_despesa: Optional[date | str] = None,
    categoria_id: Optional[int] = None,
    descricao: Optional[str] = None,
    valor: Optional[int] = None,
    forma_pagamento: Optional[str] = None,
    item_frequente_id: Optional[int] = None,
) -> bool:
    row = conn.execute("SELECT id FROM despesa WHERE id = ?", (despesa_id,)).fetchone()
    if not row:
        return False

    sets = ["editado_em = datetime('now')", "updated_at = datetime('now')"]
    params = []
    if data_despesa is not None:
        sets.append("data = ?")
        params.append(
            data_despesa.isoformat() if isinstance(data_despesa, date) else data_despesa
        )
    if categoria_id is not None:
        sets.append("categoria_id = ?")
        params.append(categoria_id)
    if descricao is not None:
        sets.append("descricao = ?")
        params.append(descricao)
    if valor is not None:
        sets.append("valor = ?")
        params.append(valor)
    if forma_pagamento is not None:
        sets.append("forma_pagamento = ?")
        params.append(forma_pagamento)
    if item_frequente_id is not None:
        sets.append("item_frequente_id = ?")
        params.append(item_frequente_id)

    params.append(despesa_id)
    conn.execute(f"UPDATE despesa SET {', '.join(sets)} WHERE id = ?", params)
    return True


def excluir(conn: sqlite3.Connection, despesa_id: int) -> bool:
    row = conn.execute("SELECT id FROM despesa WHERE id = ?", (despesa_id,)).fetchone()
    if not row:
        return False
    conn.execute("DELETE FROM despesa WHERE id = ?", (despesa_id,))
    return True


# ---------------------------------------------------------------------------
# Agregacoes
# ---------------------------------------------------------------------------


def serie_diaria(
    conn: sqlite3.Connection, de: date | str, ate: date | str
) -> list[dict]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    rows = conn.execute(
        """SELECT data, SUM(valor) AS total, COUNT(*) AS qtd
           FROM despesa
           WHERE data >= ? AND data <= ?
           GROUP BY data
           ORDER BY data""",
        (de_s, ate_s),
    ).fetchall()
    return [dict(r) for r in rows]


def total_por_categoria(
    conn: sqlite3.Connection, de: date | str, ate: date | str
) -> list[dict]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    rows = conn.execute(
        """SELECT categoria_id, categoria_nome,
                  SUM(valor) AS total, COUNT(*) AS qtd
           FROM despesa
           WHERE data >= ? AND data <= ?
           GROUP BY categoria_id, categoria_nome
           ORDER BY total DESC""",
        (de_s, ate_s),
    ).fetchall()
    return [dict(r) for r in rows]
