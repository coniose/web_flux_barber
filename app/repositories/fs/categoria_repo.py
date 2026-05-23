"""Repositório de categorias de despesa — Firestore."""

from __future__ import annotations

from typing import Optional

from app.utils.validators import ValidacaoError

from ._util import new_id, doc_to_dict, stream_to_list
from .store import BarberStore


def _col(store: BarberStore):
    return store.col("categoria_despesa")


def listar_ativas(store: BarberStore) -> list[dict]:
    docs = stream_to_list(_col(store))
    return sorted([d for d in docs if d.get("ativo", True)], key=lambda d: d.get("nome", ""))


def listar_todas(store: BarberStore) -> list[dict]:
    docs = stream_to_list(_col(store))
    return sorted(docs, key=lambda d: (0 if d.get("ativo", True) else 1, d.get("nome", "")))


def obter(store: BarberStore, categoria_id: int) -> Optional[dict]:
    doc = _col(store).document(str(categoria_id)).get()
    return doc_to_dict(doc)


def criar(store: BarberStore, nome: str, icone: str = "📦") -> int:
    existentes = [d for d in stream_to_list(_col(store)) if d.get("nome") == nome]
    if existentes:
        raise ValidacaoError(f"Já existe uma categoria com o nome '{nome}'.")

    cid = new_id()
    _col(store).document(str(cid)).set({
        "id": cid,
        "nome": nome,
        "icone": icone,
        "ativo": True,
    })
    return cid


def atualizar(
    store: BarberStore,
    categoria_id: int,
    *,
    nome: Optional[str] = None,
    icone: Optional[str] = None,
    ativo: Optional[bool] = None,
) -> bool:
    doc_ref = _col(store).document(str(categoria_id))
    if not doc_ref.get().exists:
        return False
    update: dict = {}
    if nome is not None:
        update["nome"] = nome
    if icone is not None:
        update["icone"] = icone
    if ativo is not None:
        update["ativo"] = bool(ativo)
    if not update:
        return False
    doc_ref.update(update)
    return True
