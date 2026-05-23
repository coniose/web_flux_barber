"""Regras de negócio para despesas."""

from __future__ import annotations

from datetime import date
from typing import Optional

from app.domain.enums import FormaPagamento
from app.repositories.fs import despesa_repo, categoria_repo, item_frequente_repo
from app.repositories.fs.store import BarberStore
from app.utils.validators import (
    ValidacaoError,
    validar_data,
    validar_descricao,
    validar_forma_pagamento,
    validar_valor_positivo,
)


def registrar_despesa(
    store: BarberStore,
    *,
    categoria_id: int,
    descricao: str,
    valor_centavos: int,
    forma_pagamento: FormaPagamento | str,
    data_despesa: date | None = None,
    item_frequente_id: Optional[int] = None,
    permitir_data_futura: bool = False,
) -> int:
    data_despesa = data_despesa or date.today()
    validar_data(data_despesa, permitir_futuro=permitir_data_futura)
    validar_valor_positivo(valor_centavos)
    validar_descricao(descricao)

    forma_str = forma_pagamento.value if isinstance(forma_pagamento, FormaPagamento) else forma_pagamento
    validar_forma_pagamento(forma_str)

    categoria = categoria_repo.obter(store, categoria_id)
    if categoria is None:
        raise ValidacaoError(f"Categoria de despesa #{categoria_id} não existe.")

    if item_frequente_id is not None:
        item = item_frequente_repo.obter(store, item_frequente_id)
        if item is None:
            raise ValidacaoError(f"Item frequente #{item_frequente_id} não existe.")
        item_frequente_repo.bump_uso(store, item_frequente_id)

    return despesa_repo.inserir(
        store,
        data_despesa=data_despesa,
        categoria_id=categoria_id,
        categoria_nome=categoria.get("nome", ""),
        categoria_icone=categoria.get("icone", "📦"),
        descricao=descricao,
        valor=valor_centavos,
        forma_pagamento=forma_str,
        item_frequente_id=item_frequente_id,
    )


def listar_periodo(
    store: BarberStore,
    de: date,
    ate: date,
    categoria_id: Optional[int] = None,
) -> list[dict]:
    if de > ate:
        raise ValidacaoError("A data inicial deve ser anterior ou igual à final.")
    return despesa_repo.listar_periodo(store, de, ate, categoria_id=categoria_id)


def totais_periodo(store: BarberStore, de: date, ate: date) -> dict:
    total, qtd = despesa_repo.total_periodo(store, de, ate)
    return {"total_centavos": total, "qtd_despesas": qtd}


def excluir_despesa(store: BarberStore, despesa_id: int) -> bool:
    return despesa_repo.excluir(store, despesa_id)


# ---------------------------------------------------------------------------
# Agregações para o Dashboard
# ---------------------------------------------------------------------------


def serie_diaria_despesa(store: BarberStore, de: date, ate: date) -> list[dict]:
    if de > ate:
        raise ValidacaoError("A data inicial deve ser anterior ou igual à final.")
    return despesa_repo.serie_diaria(store, de, ate)


def total_por_categoria(store: BarberStore, de: date, ate: date) -> list[dict]:
    if de > ate:
        raise ValidacaoError("A data inicial deve ser anterior ou igual à final.")
    return despesa_repo.total_por_categoria(store, de, ate)
