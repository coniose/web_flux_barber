"""Repositório de itens frequentes de despesa — Firestore."""

from __future__ import annotations

from typing import Optional

from firebase_admin import firestore

from app.utils.validators import ValidacaoError

from ._util import new_id, doc_to_dict, stream_to_list
from .store import BarberStore


def _col(store: BarberStore):
    return store.col("item_despesa_frequente")


def listar_ativos_ordenado_por_uso(store: BarberStore) -> list[dict]:
    docs = stream_to_list(_col(store))
    ativos = [d for d in docs if d.get("ativo", True)]
    return sorted(ativos, key=lambda d: d.get("vezes_usado", 0), reverse=True)


def listar_todos(store: BarberStore) -> list[dict]:
    docs = stream_to_list(_col(store))
    return sorted(docs, key=lambda d: (0 if d.get("ativo", True) else 1, d.get("descricao", "")))


def obter(store: BarberStore, item_id: int) -> Optional[dict]:
    doc = _col(store).document(str(item_id)).get()
    return doc_to_dict(doc)


def criar(
    store: BarberStore,
    descricao: str,
    categoria_id: int,
    valor_sugerido: Optional[int] = None,
) -> int:
    iid = new_id()
    _col(store).document(str(iid)).set({
        "id": iid,
        "descricao": descricao,
        "categoria_id": categoria_id,
        "valor_sugerido": valor_sugerido,
        "vezes_usado": 0,
        "ativo": True,
    })
    return iid


def atualizar(
    store: BarberStore,
    item_id: int,
    *,
    descricao: Optional[str] = None,
    categoria_id: Optional[int] = None,
    valor_sugerido: Optional[int] = None,
    ativo: Optional[bool] = None,
) -> bool:
    doc_ref = _col(store).document(str(item_id))
    if not doc_ref.get().exists:
        return False
    update: dict = {}
    if descricao is not None:
        update["descricao"] = descricao
    if categoria_id is not None:
        update["categoria_id"] = categoria_id
    if valor_sugerido is not None:
        update["valor_sugerido"] = valor_sugerido
    if ativo is not None:
        update["ativo"] = bool(ativo)
    if not update:
        return False
    doc_ref.update(update)
    return True


def bump_uso(store: BarberStore, item_id: int) -> None:
    _col(store).document(str(item_id)).update({"vezes_usado": firestore.Increment(1)})
