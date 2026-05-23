"""Repositório de serviços — Firestore."""

from __future__ import annotations

from typing import Optional

from app.utils.validators import ValidacaoError

from ._util import new_id, doc_to_dict, stream_to_list
from .store import BarberStore


def _col(store: BarberStore):
    return store.col("servico")


def listar_ativos(store: BarberStore) -> list[dict]:
    docs = stream_to_list(_col(store))
    ativos = [d for d in docs if d.get("ativo", True)]
    return sorted(ativos, key=lambda d: (d.get("ordem", 999), d.get("nome", "")))


def listar_todos(store: BarberStore) -> list[dict]:
    docs = stream_to_list(_col(store))
    return sorted(docs, key=lambda d: (
        0 if d.get("ativo", True) else 1,
        d.get("ordem", 999),
        d.get("nome", ""),
    ))


def obter(store: BarberStore, servico_id: int) -> Optional[dict]:
    doc = _col(store).document(str(servico_id)).get()
    return doc_to_dict(doc)


def criar(
    store: BarberStore,
    nome: str,
    preco_padrao: int,
    categoria_servico: Optional[str] = None,
    ordem: int = 999,
) -> int:
    existentes = [d for d in stream_to_list(_col(store)) if d.get("nome") == nome]
    if existentes:
        raise ValidacaoError(f"Já existe um serviço com o nome '{nome}'.")

    sid = new_id()
    _col(store).document(str(sid)).set({
        "id": sid,
        "nome": nome,
        "preco_padrao": preco_padrao,
        "categoria_servico": categoria_servico,
        "ordem": ordem,
        "ativo": True,
    })
    return sid


def atualizar(
    store: BarberStore,
    servico_id: int,
    *,
    nome: Optional[str] = None,
    preco_padrao: Optional[int] = None,
    categoria_servico: Optional[str] = None,
    ordem: Optional[int] = None,
    ativo: Optional[bool] = None,
) -> bool:
    doc_ref = _col(store).document(str(servico_id))
    if not doc_ref.get().exists:
        return False
    update: dict = {}
    if nome is not None:
        update["nome"] = nome
    if preco_padrao is not None:
        update["preco_padrao"] = preco_padrao
    if categoria_servico is not None:
        update["categoria_servico"] = categoria_servico
    if ordem is not None:
        update["ordem"] = ordem
    if ativo is not None:
        update["ativo"] = bool(ativo)
    if not update:
        return False
    doc_ref.update(update)
    return True
