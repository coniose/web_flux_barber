"""Repositório de receitas (atendimentos) — SQLite."""

from __future__ import annotations

import uuid as uuid_lib
from collections import defaultdict
from datetime import date
from typing import Optional

import sqlite3


def _periodo(conn: sqlite3.Connection, de: date | str, ate: date | str) -> list[dict]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    rows = conn.execute(
        "SELECT * FROM receita WHERE data >= ? AND data <= ? ORDER BY data DESC, id DESC",
        (de_s, ate_s),
    ).fetchall()
    return [dict(r) for r in rows]


def inserir(
    conn: sqlite3.Connection,
    *,
    data_atendimento: date | str,
    servico_id: int,
    servico_nome: str = "",
    valor: int,
    forma_pagamento: Optional[str],
    cliente_id: Optional[int] = None,
    assinatura_id: Optional[int] = None,
    observacao: Optional[str] = None,
) -> int:
    data_str = data_atendimento.isoformat() if isinstance(data_atendimento, date) else data_atendimento
    uid = uuid_lib.uuid4().hex
    cur = conn.execute(
        """INSERT INTO receita
               (uuid, data, servico_id, servico_nome, cliente_id, assinatura_id,
                valor, forma_pagamento, observacao)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (uid, data_str, servico_id, servico_nome, cliente_id, assinatura_id,
         valor, forma_pagamento, observacao),
    )
    return cur.lastrowid


def obter(conn: sqlite3.Connection, receita_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM receita WHERE id = ?", (receita_id,)).fetchone()
    return dict(row) if row else None


def listar_periodo(conn: sqlite3.Connection, de: date | str, ate: date | str) -> list[dict]:
    return _periodo(conn, de, ate)


def total_periodo(conn: sqlite3.Connection, de: date | str, ate: date | str) -> tuple[int, int]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    row = conn.execute(
        "SELECT COALESCE(SUM(valor), 0), COUNT(*) FROM receita WHERE data >= ? AND data <= ?",
        (de_s, ate_s),
    ).fetchone()
    return int(row[0]), int(row[1])


def atualizar(
    conn: sqlite3.Connection,
    receita_id: int,
    *,
    data_atendimento: Optional[date | str] = None,
    servico_id: Optional[int] = None,
    valor: Optional[int] = None,
    forma_pagamento: Optional[str] = None,
    observacao: Optional[str] = None,
) -> bool:
    row = conn.execute("SELECT id FROM receita WHERE id = ?", (receita_id,)).fetchone()
    if not row:
        return False

    sets = ["editado_em = datetime('now')", "updated_at = datetime('now')"]
    params = []
    if data_atendimento is not None:
        sets.append("data = ?")
        params.append(
            data_atendimento.isoformat() if isinstance(data_atendimento, date) else data_atendimento
        )
    if servico_id is not None:
        sets.append("servico_id = ?")
        params.append(servico_id)
    if valor is not None:
        sets.append("valor = ?")
        params.append(valor)
    if forma_pagamento is not None:
        sets.append("forma_pagamento = ?")
        params.append(forma_pagamento)
    if observacao is not None:
        sets.append("observacao = ?")
        params.append(observacao)

    params.append(receita_id)
    conn.execute(f"UPDATE receita SET {', '.join(sets)} WHERE id = ?", params)
    return True


def excluir(conn: sqlite3.Connection, receita_id: int) -> bool:
    row = conn.execute("SELECT id FROM receita WHERE id = ?", (receita_id,)).fetchone()
    if not row:
        return False
    conn.execute("DELETE FROM receita WHERE id = ?", (receita_id,))
    return True


# ---------------------------------------------------------------------------
# Agregacoes
# ---------------------------------------------------------------------------


def serie_diaria(conn: sqlite3.Connection, de: date | str, ate: date | str) -> list[dict]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    rows = conn.execute(
        """SELECT data, SUM(valor) AS total, COUNT(*) AS qtd
           FROM receita
           WHERE data >= ? AND data <= ?
           GROUP BY data
           ORDER BY data""",
        (de_s, ate_s),
    ).fetchall()
    return [dict(r) for r in rows]


def ranking_servicos(
    conn: sqlite3.Connection, de: date | str, ate: date | str, limite: int = 10
) -> list[dict]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    rows = conn.execute(
        """SELECT servico_id, servico_nome,
                  SUM(valor) AS total, COUNT(*) AS qtd
           FROM receita
           WHERE data >= ? AND data <= ?
           GROUP BY servico_id, servico_nome
           ORDER BY total DESC
           LIMIT ?""",
        (de_s, ate_s, limite),
    ).fetchall()
    return [dict(r) for r in rows]


def mix_forma_pagamento(
    conn: sqlite3.Connection, de: date | str, ate: date | str
) -> list[dict]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    rows = conn.execute(
        """SELECT COALESCE(forma_pagamento, 'ASSINATURA') AS forma,
                  SUM(valor) AS total, COUNT(*) AS qtd
           FROM receita
           WHERE data >= ? AND data <= ?
           GROUP BY forma
           ORDER BY total DESC""",
        (de_s, ate_s),
    ).fetchall()
    return [dict(r) for r in rows]
