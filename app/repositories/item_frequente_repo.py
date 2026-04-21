"""Repositório de itens frequentes de despesa."""

from __future__ import annotations

import sqlite3
from typing import Optional

from app.repositories.audit import log_audit, row_to_dict


def listar_ativos_ordenado_por_uso(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Itens ativos ordenados por uso (mais usados primeiro) e depois alfabeticamente."""
    return conn.execute(
        """SELECT i.*, c.nome AS categoria_nome, c.icone AS categoria_icone
             FROM item_despesa_frequente i
             JOIN categoria_despesa c ON c.id = i.categoria_id
            WHERE i.ativo = 1
            ORDER BY i.vezes_usado DESC, i.descricao"""
    ).fetchall()


def listar_todos(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT i.*, c.nome AS categoria_nome
             FROM item_despesa_frequente i
             JOIN categoria_despesa c ON c.id = i.categoria_id
            ORDER BY i.ativo DESC, i.descricao"""
    ).fetchall()


def obter(conn: sqlite3.Connection, item_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM item_despesa_frequente WHERE id = ?", (item_id,)
    ).fetchone()


def criar(
    conn: sqlite3.Connection,
    descricao: str,
    categoria_id: int,
    valor_sugerido: Optional[int] = None,
) -> int:
    cur = conn.execute(
        """INSERT INTO item_despesa_frequente (descricao, categoria_id, valor_sugerido)
           VALUES (?, ?, ?)""",
        (descricao, categoria_id, valor_sugerido),
    )
    new_id = cur.lastrowid
    log_audit(conn, "item_despesa_frequente", new_id, "INSERT", {
        "descricao": descricao, "categoria_id": categoria_id,
        "valor_sugerido": valor_sugerido,
    })
    return new_id


def bump_uso(conn: sqlite3.Connection, item_id: int) -> None:
    """Incrementa ``vezes_usado`` — chamado quando uma despesa referencia o item."""
    conn.execute(
        "UPDATE item_despesa_frequente SET vezes_usado = vezes_usado + 1 WHERE id = ?",
        (item_id,),
    )


def atualizar(
    conn: sqlite3.Connection,
    item_id: int,
    *,
    descricao: Optional[str] = None,
    categoria_id: Optional[int] = None,
    valor_sugerido: Optional[int] = None,
    ativo: Optional[bool] = None,
) -> bool:
    antes = obter(conn, item_id)
    if antes is None:
        return False

    campos = []
    valores: list = []
    if descricao is not None:
        campos.append("descricao = ?"); valores.append(descricao)
    if categoria_id is not None:
        campos.append("categoria_id = ?"); valores.append(categoria_id)
    if valor_sugerido is not None:
        campos.append("valor_sugerido = ?"); valores.append(valor_sugerido)
    if ativo is not None:
        campos.append("ativo = ?"); valores.append(1 if ativo else 0)

    if not campos:
        return False

    valores.append(item_id)
    conn.execute(
        f"UPDATE item_despesa_frequente SET {', '.join(campos)} WHERE id = ?", valores
    )
    log_audit(conn, "item_despesa_frequente", item_id, "UPDATE", row_to_dict(antes))
    return True
