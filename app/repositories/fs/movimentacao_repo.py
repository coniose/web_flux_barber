"""Repositório de movimentações de estoque — Firestore."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Optional

from ._util import new_id, stream_to_list
from .store import BarberStore


def _col(store: BarberStore):
    return store.col("movimentacao_estoque")


def _periodo(store: BarberStore, de: date | str, ate: date | str) -> list[dict]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    return stream_to_list(
        _col(store).where("data", ">=", de_s).where("data", "<=", ate_s)
    )


def inserir(
    store: BarberStore,
    *,
    produto_id: int,
    produto_nome: str = "",
    tipo: str,
    quantidade: int,
    preco_unitario: int,
    data_mov: date | str,
    observacao: Optional[str] = None,
) -> int:
    data_str = data_mov.isoformat() if isinstance(data_mov, date) else data_mov
    total = abs(quantidade) * preco_unitario
    mid = new_id()
    _col(store).document(str(mid)).set({
        "id": mid,
        "produto_id": produto_id,
        "produto_nome": produto_nome,
        "tipo": tipo,
        "quantidade": quantidade,
        "preco_unitario": preco_unitario,
        "total_centavos": total,
        "data": data_str,
        "observacao": observacao,
    })
    return mid


def listar_periodo(
    store: BarberStore,
    de: date | str,
    ate: date | str,
    produto_id: Optional[int] = None,
    tipo: Optional[str] = None,
) -> list[dict]:
    docs = _periodo(store, de, ate)
    if produto_id is not None:
        docs = [d for d in docs if d.get("produto_id") == produto_id]
    if tipo is not None:
        docs = [d for d in docs if d.get("tipo") == tipo]
    return sorted(docs, key=lambda d: (d.get("data", ""), d.get("id", 0)), reverse=True)


def totais_periodo(store: BarberStore, de: date | str, ate: date | str) -> dict:
    """Retorna totais separados por tipo: {"COMPRA": {total, qtd}, "VENDA": {...}}."""
    docs = _periodo(store, de, ate)
    result: dict = {"COMPRA": {"total": 0, "qtd": 0}, "VENDA": {"total": 0, "qtd": 0}}
    for d in docs:
        tipo = d.get("tipo")
        if tipo in result:
            result[tipo]["total"] += d.get("total_centavos", 0)
            result[tipo]["qtd"] += abs(d.get("quantidade", 0))
    return result


def margem_periodo(store: BarberStore, de: date | str, ate: date | str) -> int:
    totais = totais_periodo(store, de, ate)
    return totais["VENDA"]["total"] - totais["COMPRA"]["total"]


def ranking_produtos(store: BarberStore, de: date | str, ate: date | str, limite: int = 10) -> list[dict]:
    docs = [d for d in _periodo(store, de, ate) if d.get("tipo") == "VENDA"]
    by_prod: dict = defaultdict(lambda: {"id": 0, "nome": "", "receita_venda": 0, "qtd_vendida": 0})
    for d in docs:
        pid = d.get("produto_id")
        by_prod[pid]["id"] = pid
        by_prod[pid]["nome"] = d.get("produto_nome", "")
        by_prod[pid]["receita_venda"] += d.get("total_centavos", 0)
        by_prod[pid]["qtd_vendida"] += abs(d.get("quantidade", 0))
    return sorted(by_prod.values(), key=lambda x: x["receita_venda"], reverse=True)[:limite]
