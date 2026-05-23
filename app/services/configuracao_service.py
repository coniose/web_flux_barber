"""Regras de negócio para configurações da empresa."""

from __future__ import annotations

from app.repositories.sql import config_repo


def nome_empresa(conn) -> str:
    return config_repo.get_config(conn, "nome_empresa") or "Minha Barbearia"


def definir_nome_empresa(conn, nome: str) -> None:
    if not nome or not nome.strip():
        raise ValueError("Nome da empresa não pode ser vazio.")
    config_repo.set_config(conn, "nome_empresa", nome.strip())


def meta_mensal_centavos(conn) -> int:
    val = config_repo.get_config(conn, "meta_mensal")
    try:
        return int(val or "0")
    except ValueError:
        return 0


def definir_meta_mensal(conn, centavos: int) -> None:
    if centavos < 0:
        raise ValueError("Meta mensal não pode ser negativa.")
    config_repo.set_config(conn, "meta_mensal", str(int(centavos)))


def ano_contabil(conn) -> int:
    from datetime import date as _date
    val = config_repo.get_config(conn, "ano_contabil")
    try:
        return int(val or str(_date.today().year))
    except ValueError:
        return _date.today().year
