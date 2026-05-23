"""Repositório de despesas — Firestore."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Optional

from ._util import new_id, stream_to_list
from .store import BarberStore


def _col(store: BarberStore):
    return store.col("despesa")


def _periodo(store: BarberStore, de: date | str, ate: date | str) -> list[dict]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    return stream_to_list(
        _col(store).where("data", ">=", de_s).where("data", "<=", ate_s)
    )


def inserir(
    store: BarberStore,
    *,
    data_despesa: date | str,
    categoria_id: int,
    categoria_nome: str = "",
    categoria_icone: str = "📦",
    descricao: str,
    valor: int,
    forma_pagamento: str,
    item_frequente_id: Optional[int] = None,
) -> int:
    data_str = data_despesa.isoformat() if isinstance(data_despesa, date) else data_despesa
    did = new_id()
    _col(store).document(str(did)).set({
        "id": did,
        "data": data_str,
        "categoria_id": categoria_id,
        "categoria_nome": categoria_nome,
        "categoria_icone": categoria_icone,
        "item_frequente_id": item_frequente_id,
        "descricao": descricao,
        "valor": valor,
        "forma_pagamento": forma_pagamento,
    })
    return did


def obter(store: BarberStore, despesa_id: int) -> Optional[dict]:
    from ._util import doc_to_dict
    return doc_to_dict(_col(store).document(str(despesa_id)).get())


def listar_periodo(
    store: BarberStore,
    de: date | str,
    ate: date | str,
    categoria_id: Optional[int] = None,
) -> list[dict]:
    docs = _periodo(store, de, ate)
    if categoria_id is not None:
        docs = [d for d in docs if d.get("categoria_id") == categoria_id]
    return sorted(docs, key=lambda d: (d.get("data", ""), d.get("id", 0)), reverse=True)


def total_periodo(store: BarberStore, de: date | str, ate: date | str) -> tuple[int, int]:
    docs = _periodo(store, de, ate)
    total = sum(d.get("valor", 0) for d in docs)
    return int(total), len(docs)


def atualizar(
    store: BarberStore,
    despesa_id: int,
    *,
    data_despesa: Optional[date | str] = None,
    categoria_id: Optional[int] = None,
    descricao: Optional[str] = None,
    valor: Optional[int] = None,
    forma_pagamento: Optional[str] = None,
    item_frequente_id: Optional[int] = None,
) -> bool:
    doc_ref = _col(store).document(str(despesa_id))
    if not doc_ref.get().exists:
        return False
    update: dict = {}
    if data_despesa is not None:
        update["data"] = data_despesa.isoformat() if isinstance(data_despesa, date) else data_despesa
    if categoria_id is not None:
        update["categoria_id"] = categoria_id
    if descricao is not None:
        update["descricao"] = descricao
    if valor is not None:
        update["valor"] = valor
    if forma_pagamento is not None:
        update["forma_pagamento"] = forma_pagamento
    if item_frequente_id is not None:
        update["item_frequente_id"] = item_frequente_id
    if not update:
        return False
    doc_ref.update(update)
    return True


def excluir(store: BarberStore, despesa_id: int) -> bool:
    doc_ref = _col(store).document(str(despesa_id))
    if not doc_ref.get().exists:
        return False
    doc_ref.delete()
    return True


# ---------------------------------------------------------------------------
# Agregações
# ---------------------------------------------------------------------------


def serie_diaria(store: BarberStore, de: date | str, ate: date | str) -> list[dict]:
    docs = _periodo(store, de, ate)
    by_day: dict = defaultdict(lambda: {"total": 0, "qtd": 0})
    for d in docs:
        day = d["data"]
        by_day[day]["total"] += d.get("valor", 0)
        by_day[day]["qtd"] += 1
    return [{"data": day, **v} for day, v in sorted(by_day.items())]


def total_por_categoria(store: BarberStore, de: date | str, ate: date | str) -> list[dict]:
    docs = _periodo(store, de, ate)
    by_cat: dict = defaultdict(lambda: {"categoria_id": 0, "categoria_nome": "", "total": 0, "qtd": 0})
    for d in docs:
        cid = d.get("categoria_id")
        by_cat[cid]["categoria_id"] = cid
        by_cat[cid]["categoria_nome"] = d.get("categoria_nome", "")
        by_cat[cid]["total"] += d.get("valor", 0)
        by_cat[cid]["qtd"] += 1
    return sorted(by_cat.values(), key=lambda x: x["total"], reverse=True)
