"""Repositório de configurações chave-valor — Firestore."""

from __future__ import annotations

from typing import Optional

from ._util import stream_to_list
from .store import BarberStore


def _col(store: BarberStore):
    return store.col("config")


def obter(store: BarberStore, chave: str) -> Optional[str]:
    doc = _col(store).document(chave).get()
    if doc.exists:
        return (doc.to_dict() or {}).get("valor")
    return None


def definir(store: BarberStore, chave: str, valor: str) -> None:
    _col(store).document(chave).set({"chave": chave, "valor": valor})


def obter_todos(store: BarberStore) -> list[dict]:
    return [{"chave": d.get("chave"), "valor": d.get("valor")} for d in stream_to_list(_col(store))]
