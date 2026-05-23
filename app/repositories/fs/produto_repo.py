"""Repositório de produtos (estoque) — Firestore."""

from __future__ import annotations

from typing import Optional

from firebase_admin import firestore

from app.utils.validators import ValidacaoError

from ._util import new_id, doc_to_dict, stream_to_list
from .store import BarberStore


def _col(store: BarberStore):
    return store.col("produto")


def inserir(
    store: BarberStore,
    *,
    nome: str,
    preco_custo: int,
    preco_venda: int,
    descricao: Optional[str] = None,
    quantidade_inicial: int = 0,
) -> int:
    existentes = [d for d in stream_to_list(_col(store)) if d.get("nome") == nome.strip()]
    if existentes:
        raise ValidacaoError(f"Produto '{nome}' já existe no catálogo.")

    pid = new_id()
    _col(store).document(str(pid)).set({
        "id": pid,
        "nome": nome.strip(),
        "descricao": descricao,
        "preco_custo": preco_custo,
        "preco_venda": preco_venda,
        "quantidade_estoque": quantidade_inicial,
        "ativo": True,
    })
    return pid


def obter(store: BarberStore, produto_id: int) -> Optional[dict]:
    return doc_to_dict(_col(store).document(str(produto_id)).get())


def listar_ativos(store: BarberStore) -> list[dict]:
    docs = stream_to_list(_col(store))
    return sorted([d for d in docs if d.get("ativo", True)], key=lambda d: d.get("nome", ""))


def listar_todos(store: BarberStore) -> list[dict]:
    docs = stream_to_list(_col(store))
    return sorted(docs, key=lambda d: (0 if d.get("ativo", True) else 1, d.get("nome", "")))


def atualizar(
    store: BarberStore,
    produto_id: int,
    *,
    nome: Optional[str] = None,
    descricao: Optional[str] = None,
    preco_custo: Optional[int] = None,
    preco_venda: Optional[int] = None,
    ativo: Optional[int] = None,
) -> bool:
    doc_ref = _col(store).document(str(produto_id))
    if not doc_ref.get().exists:
        return False
    update: dict = {}
    if nome is not None:
        update["nome"] = nome.strip()
    if descricao is not None:
        update["descricao"] = descricao
    if preco_custo is not None:
        update["preco_custo"] = preco_custo
    if preco_venda is not None:
        update["preco_venda"] = preco_venda
    if ativo is not None:
        update["ativo"] = bool(ativo)
    if not update:
        return False
    doc_ref.update(update)
    return True


def ajustar_quantidade(store: BarberStore, produto_id: int, delta: int) -> None:
    """Incrementa (delta > 0) ou decrementa (delta < 0) o estoque atomicamente."""
    _col(store).document(str(produto_id)).update(
        {"quantidade_estoque": firestore.Increment(delta)}
    )
