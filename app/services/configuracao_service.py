"""Regras de negócio para configurações da empresa."""

from __future__ import annotations

from app.repositories.fs import config_repo
from app.repositories.fs.store import BarberStore


def nome_empresa(store: BarberStore) -> str:
    return config_repo.obter(store, "nome_empresa") or "Minha Barbearia"


def definir_nome_empresa(store: BarberStore, nome: str) -> None:
    if not nome or not nome.strip():
        raise ValueError("Nome da empresa não pode ser vazio.")
    config_repo.definir(store, "nome_empresa", nome.strip())


def meta_mensal_centavos(store: BarberStore) -> int:
    val = config_repo.obter(store, "meta_mensal")
    try:
        return int(val or "0")
    except ValueError:
        return 0


def definir_meta_mensal(store: BarberStore, centavos: int) -> None:
    if centavos < 0:
        raise ValueError("Meta mensal não pode ser negativa.")
    config_repo.definir(store, "meta_mensal", str(int(centavos)))


def ano_contabil(store: BarberStore) -> int:
    from datetime import date as _date
    val = config_repo.obter(store, "ano_contabil")
    try:
        return int(val or str(_date.today().year))
    except ValueError:
        return _date.today().year
