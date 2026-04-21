"""Repositório de serviços do catálogo."""

from __future__ import annotations

import sqlite3
from typing import Optional

from app.repositories.audit import log_audit, row_to_dict


def listar_ativos(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Serviços ativos ordenados por ``ordem`` (asc) e depois nome."""
    return conn.execute(
        "SELECT * FROM servico WHERE ativo = 1 ORDER BY ordem, nome"
    ).fetchall()


def listar_todos(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM servico ORDER BY ativo DESC, ordem, nome"
    ).fetchall()


def obter(conn: sqlite3.Connection, servico_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM servico WHERE id = ?", (servico_id,)).fetchone()


def criar(
    conn: sqlite3.Connection,
    nome: str,
    preco_padrao: int,
    categoria_servico: Optional[str] = None,
    ordem: int = 999,
) -> int:
    cur = conn.execute(
        """INSERT INTO servico (nome, preco_padrao, categoria_servico, ordem)
           VALUES (?, ?, ?, ?)""",
        (nome, preco_padrao, categoria_servico, ordem),
    )
    new_id = cur.lastrowid
    log_audit(conn, "servico", new_id, "INSERT", {
        "nome": nome, "preco_padrao": preco_padrao,
        "categoria_servico": categoria_servico, "ordem": ordem,
    })
    return new_id


def atualizar(
    conn: sqlite3.Connection,
    servico_id: int,
    *,
    nome: Optional[str] = None,
    preco_padrao: Optional[int] = None,
    categoria_servico: Optional[str] = None,
    ordem: Optional[int] = None,
    ativo: Optional[bool] = None,
) -> bool:
    antes = obter(conn, servico_id)
    if antes is None:
        return False

    campos = []
    valores: list = []
    if nome is not None:
        campos.append("nome = ?"); valores.append(nome)
    if preco_padrao is not None:
        campos.append("preco_padrao = ?"); valores.append(preco_padrao)
    if categoria_servico is not None:
        campos.append("categoria_servico = ?"); valores.append(categoria_servico)
    if ordem is not None:
        campos.append("ordem = ?"); valores.append(ordem)
    if ativo is not None:
        campos.append("ativo = ?"); valores.append(1 if ativo else 0)

    if not campos:
        return False

    valores.append(servico_id)
    conn.execute(f"UPDATE servico SET {', '.join(campos)} WHERE id = ?", valores)
    log_audit(conn, "servico", servico_id, "UPDATE", row_to_dict(antes))
    return True


def arquivar(conn: sqlite3.Connection, servico_id: int) -> bool:
    """Marca serviço como inativo (soft-delete). Não apaga — mantém histórico de receitas."""
    return atualizar(conn, servico_id, ativo=False)


def reativar(conn: sqlite3.Connection, servico_id: int) -> bool:
    return atualizar(conn, servico_id, ativo=True)
