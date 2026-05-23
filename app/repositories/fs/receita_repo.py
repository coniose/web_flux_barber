"""Repositório de receitas (atendimentos) — Firestore."""

from __future__ import annotations

import uuid as uuid_lib
from collections import defaultdict
from datetime import date
from typing import Optional

from ._util import new_id, stream_to_list
from .store import BarberStore


def _col(store: BarberStore):
    return store.col("receita")


def _periodo(store: BarberStore, de: date | str, ate: date | str) -> list[dict]:
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    return stream_to_list(
        _col(store).where("data", ">=", de_s).where("data", "<=", ate_s)
    )


def inserir(
    store: BarberStore,
    *,
    data_atendimento: date | str,
    servico_id: int,
    servico_nome: str = "",
    valor: int,
    forma_pagamento: Optional[str],
    cliente_id: Optional[int] = None,
    assinatura_id: Optional[int] = None,
    observacao: Optional[str] = None,
) -> int:
    data_str = data_atendimento.isoformat() if isinstance(data_atendimento, date) else data_atendimento
    rec_id = new_id()
    _col(store).document(str(rec_id)).set({
        "id": rec_id,
        "uuid": uuid_lib.uuid4().hex,
        "data": data_str,
        "servico_id": servico_id,
        "servico_nome": servico_nome,
        "cliente_id": cliente_id,
        "valor": valor,
        "forma_pagamento": forma_pagamento,
        "observacao": observacao,
    })
    return rec_id


def obter(store: BarberStore, receita_id: int) -> Optional[dict]:
    from ._util import doc_to_dict
    return doc_to_dict(_col(store).document(str(receita_id)).get())


def listar_periodo(store: BarberStore, de: date | str, ate: date | str) -> list[dict]:
    docs = _periodo(store, de, ate)
    return sorted(docs, key=lambda d: (d.get("data", ""), d.get("id", 0)), reverse=True)


def total_periodo(store: BarberStore, de: date | str, ate: date | str) -> tuple[int, int]:
    docs = _periodo(store, de, ate)
    total = sum(d.get("valor", 0) for d in docs)
    return int(total), len(docs)


def atualizar(
    store: BarberStore,
    receita_id: int,
    *,
    data_atendimento: Optional[date | str] = None,
    servico_id: Optional[int] = None,
    valor: Optional[int] = None,
    forma_pagamento: Optional[str] = None,
    observacao: Optional[str] = None,
) -> bool:
    doc_ref = _col(store).document(str(receita_id))
    if not doc_ref.get().exists:
        return False
    update: dict = {}
    if data_atendimento is not None:
        update["data"] = data_atendimento.isoformat() if isinstance(data_atendimento, date) else data_atendimento
    if servico_id is not None:
        update["servico_id"] = servico_id
    if valor is not None:
        update["valor"] = valor
    if forma_pagamento is not None:
        update["forma_pagamento"] = forma_pagamento
    if observacao is not None:
        update["observacao"] = observacao
    if not update:
        return False
    doc_ref.update(update)
    return True


def excluir(store: BarberStore, receita_id: int) -> bool:
    doc_ref = _col(store).document(str(receita_id))
    if not doc_ref.get().exists:
        return False
    doc_ref.delete()
    return True


# ---------------------------------------------------------------------------
# Agregações — Python-side (Firestore não tem GROUP BY / SUM)
# ---------------------------------------------------------------------------


def serie_diaria(store: BarberStore, de: date | str, ate: date | str) -> list[dict]:
    docs = _periodo(store, de, ate)
    by_day: dict = defaultdict(lambda: {"total": 0, "qtd": 0})
    for d in docs:
        day = d["data"]
        by_day[day]["total"] += d.get("valor", 0)
        by_day[day]["qtd"] += 1
    return [{"data": day, **v} for day, v in sorted(by_day.items())]


def ranking_servicos(store: BarberStore, de: date | str, ate: date | str, limite: int = 10) -> list[dict]:
    docs = _periodo(store, de, ate)
    by_srv: dict = defaultdict(lambda: {"servico_id": 0, "servico_nome": "", "total": 0, "qtd": 0})
    for d in docs:
        sid = d.get("servico_id")
        by_srv[sid]["servico_id"] = sid
        by_srv[sid]["servico_nome"] = d.get("servico_nome", "")
        by_srv[sid]["total"] += d.get("valor", 0)
        by_srv[sid]["qtd"] += 1
    return sorted(by_srv.values(), key=lambda x: x["total"], reverse=True)[:limite]


def mix_forma_pagamento(store: BarberStore, de: date | str, ate: date | str) -> list[dict]:
    docs = _periodo(store, de, ate)
    by_forma: dict = defaultdict(lambda: {"total": 0, "qtd": 0})
    for d in docs:
        forma = d.get("forma_pagamento") or "ASSINATURA"
        by_forma[forma]["total"] += d.get("valor", 0)
        by_forma[forma]["qtd"] += 1
    return [{"forma": f, **v} for f, v in sorted(by_forma.items(), key=lambda x: x[1]["total"], reverse=True)]
