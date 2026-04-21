"""Repositório de despesas."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Optional

from app.repositories.audit import log_audit, row_to_dict


def inserir(
    conn: sqlite3.Connection,
    *,
    data_despesa: date | str,
    categoria_id: int,
    descricao: str,
    valor: int,
    forma_pagamento: str,
    item_frequente_id: Optional[int] = None,
) -> int:
    data_str = data_despesa.isoformat() if isinstance(data_despesa, date) else data_despesa
    cur = conn.execute(
        """INSERT INTO despesa
             (data, categoria_id, item_frequente_id, descricao, valor, forma_pagamento)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (data_str, categoria_id, item_frequente_id, descricao, valor, forma_pagamento),
    )
    new_id = cur.lastrowid
    log_audit(conn, "despesa", new_id, "INSERT", {
        "data": data_str, "categoria_id": categoria_id,
        "item_frequente_id": item_frequente_id, "descricao": descricao,
        "valor": valor, "forma_pagamento": forma_pagamento,
    })
    return new_id


def obter(conn: sqlite3.Connection, despesa_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM despesa WHERE id = ?", (despesa_id,)).fetchone()


def listar_periodo(
    conn: sqlite3.Connection,
    de: date | str,
    ate: date | str,
    categoria_id: Optional[int] = None,
) -> list[sqlite3.Row]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    sql = """SELECT d.*, c.nome AS categoria_nome, c.icone AS categoria_icone,
                    i.descricao AS item_descricao
               FROM despesa d
               JOIN categoria_despesa c ON c.id = d.categoria_id
               LEFT JOIN item_despesa_frequente i ON i.id = d.item_frequente_id
              WHERE d.data BETWEEN ? AND ?"""
    params: list = [de_s, ate_s]
    if categoria_id is not None:
        sql += " AND d.categoria_id = ?"
        params.append(categoria_id)
    sql += " ORDER BY d.data DESC, d.id DESC"
    return conn.execute(sql, params).fetchall()


def total_periodo(conn: sqlite3.Connection, de: date | str, ate: date | str) -> tuple[int, int]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    row = conn.execute(
        """SELECT COALESCE(SUM(valor), 0) AS total, COUNT(*) AS qtd
             FROM despesa
            WHERE data BETWEEN ? AND ?""",
        (de_s, ate_s),
    ).fetchone()
    return int(row["total"]), int(row["qtd"])


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
    antes = obter(conn, despesa_id)
    if antes is None:
        return False

    campos = []
    valores: list = []
    if data_despesa is not None:
        s = data_despesa.isoformat() if isinstance(data_despesa, date) else data_despesa
        campos.append("data = ?"); valores.append(s)
    if categoria_id is not None:
        campos.append("categoria_id = ?"); valores.append(categoria_id)
    if descricao is not None:
        campos.append("descricao = ?"); valores.append(descricao)
    if valor is not None:
        campos.append("valor = ?"); valores.append(valor)
    if forma_pagamento is not None:
        campos.append("forma_pagamento = ?"); valores.append(forma_pagamento)
    if item_frequente_id is not None:
        campos.append("item_frequente_id = ?"); valores.append(item_frequente_id)

    if not campos:
        return False

    campos.append("editado_em = datetime('now')")
    valores.append(despesa_id)
    conn.execute(f"UPDATE despesa SET {', '.join(campos)} WHERE id = ?", valores)
    log_audit(conn, "despesa", despesa_id, "UPDATE", row_to_dict(antes))
    return True


def excluir(conn: sqlite3.Connection, despesa_id: int) -> bool:
    antes = obter(conn, despesa_id)
    if antes is None:
        return False
    log_audit(conn, "despesa", despesa_id, "DELETE", row_to_dict(antes))
    conn.execute("DELETE FROM despesa WHERE id = ?", (despesa_id,))
    return True


# ---------------------------------------------------------------------------
# Agregações para o Dashboard
# ---------------------------------------------------------------------------


def serie_diaria(
    conn: sqlite3.Connection,
    de: date | str,
    ate: date | str,
) -> list[sqlite3.Row]:
    """Soma de despesa por dia no período."""
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    return conn.execute(
        """SELECT data,
                  COALESCE(SUM(valor), 0) AS total,
                  COUNT(*) AS qtd
             FROM despesa
            WHERE data BETWEEN ? AND ?
            GROUP BY data
            ORDER BY data""",
        (de_s, ate_s),
    ).fetchall()


def total_por_categoria(
    conn: sqlite3.Connection,
    de: date | str,
    ate: date | str,
) -> list[sqlite3.Row]:
    """Total de despesa agrupado por categoria no período."""
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    return conn.execute(
        """SELECT c.id AS categoria_id,
                  c.nome AS categoria_nome,
                  COALESCE(SUM(d.valor), 0) AS total,
                  COUNT(*) AS qtd
             FROM despesa d
             JOIN categoria_despesa c ON c.id = d.categoria_id
            WHERE d.data BETWEEN ? AND ?
            GROUP BY c.id, c.nome
            ORDER BY total DESC""",
        (de_s, ate_s),
    ).fetchall()
