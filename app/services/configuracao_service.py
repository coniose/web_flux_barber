"""Regras de negócio para configurações chave-valor."""

from __future__ import annotations

import sqlite3

from app.repositories import config_repo


def nome_empresa(conn: sqlite3.Connection) -> str:
    return config_repo.obter(conn, "nome_empresa", "brodz") or "brodz"


def definir_nome_empresa(conn: sqlite3.Connection, nome: str) -> None:
    if not nome or not nome.strip():
        raise ValueError("Nome da empresa não pode ser vazio.")
    config_repo.definir(conn, "nome_empresa", nome.strip())


def meta_mensal_centavos(conn: sqlite3.Connection) -> int:
    v = config_repo.obter(conn, "meta_mensal", "0")
    try:
        return int(v or "0")
    except ValueError:
        return 0


def definir_meta_mensal(conn: sqlite3.Connection, centavos: int) -> None:
    if centavos < 0:
        raise ValueError("Meta mensal não pode ser negativa.")
    config_repo.definir(conn, "meta_mensal", str(int(centavos)))


def ano_contabil(conn: sqlite3.Connection) -> int:
    from datetime import date
    v = config_repo.obter(conn, "ano_contabil", str(date.today().year))
    try:
        return int(v or str(date.today().year))
    except ValueError:
        return date.today().year
