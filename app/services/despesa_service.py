"""Regras de negócio para despesas."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Optional

from app.domain.enums import FormaPagamento
from app.repositories import categoria_repo, despesa_repo, item_frequente_repo
from app.utils.validators import (
    ValidacaoError,
    validar_data,
    validar_descricao,
    validar_forma_pagamento,
    validar_valor_positivo,
)


def registrar_despesa(
    conn: sqlite3.Connection,
    *,
    categoria_id: int,
    descricao: str,
    valor_centavos: int,
    forma_pagamento: FormaPagamento | str,
    data_despesa: date | None = None,
    item_frequente_id: Optional[int] = None,
    permitir_data_futura: bool = False,
) -> int:
    """Registra uma despesa. Se ``item_frequente_id`` for fornecido, incrementa seu contador de uso."""
    data_despesa = data_despesa or date.today()
    validar_data(data_despesa, permitir_futuro=permitir_data_futura)
    validar_valor_positivo(valor_centavos)
    validar_descricao(descricao)

    forma_str = forma_pagamento.value if isinstance(forma_pagamento, FormaPagamento) else forma_pagamento
    validar_forma_pagamento(forma_str)

    if categoria_repo.obter(conn, categoria_id) is None:
        raise ValidacaoError(f"Categoria de despesa #{categoria_id} não existe.")

    if item_frequente_id is not None and item_frequente_repo.obter(conn, item_frequente_id) is None:
        raise ValidacaoError(f"Item frequente #{item_frequente_id} não existe.")

    try:
        despesa_id = despesa_repo.inserir(
            conn,
            data_despesa=data_despesa,
            categoria_id=categoria_id,
            descricao=descricao.strip(),
            valor=valor_centavos,
            forma_pagamento=forma_str,
            item_frequente_id=item_frequente_id,
        )
    except sqlite3.IntegrityError as e:
        raise ValidacaoError(f"Não foi possível registrar: {e}") from e

    if item_frequente_id is not None:
        item_frequente_repo.bump_uso(conn, item_frequente_id)

    return despesa_id


def registrar_item_frequente(
    conn: sqlite3.Connection,
    item_frequente_id: int,
    *,
    valor_centavos: Optional[int] = None,
    forma_pagamento: FormaPagamento | str = FormaPagamento.DINHEIRO,
    data_despesa: Optional[date] = None,
) -> int:
    """Atalho usado pelos botões de 1 clique da tela Lançar.

    Usa o ``valor_sugerido`` do item quando ``valor_centavos`` é None.
    """
    item = item_frequente_repo.obter(conn, item_frequente_id)
    if item is None:
        raise ValidacaoError(f"Item #{item_frequente_id} não existe.")

    valor = valor_centavos if valor_centavos is not None else item["valor_sugerido"]
    if valor is None:
        raise ValidacaoError(
            f"Item '{item['descricao']}' não tem valor sugerido — informe um valor."
        )

    return registrar_despesa(
        conn,
        categoria_id=item["categoria_id"],
        descricao=item["descricao"],
        valor_centavos=int(valor),
        forma_pagamento=forma_pagamento,
        data_despesa=data_despesa,
        item_frequente_id=item_frequente_id,
    )


def listar_periodo(
    conn: sqlite3.Connection,
    de: date,
    ate: date,
    categoria_id: Optional[int] = None,
) -> list[sqlite3.Row]:
    if de > ate:
        raise ValidacaoError("A data inicial deve ser anterior ou igual à final.")
    return despesa_repo.listar_periodo(conn, de, ate, categoria_id=categoria_id)


def totais_periodo(conn: sqlite3.Connection, de: date, ate: date) -> dict:
    total, qtd = despesa_repo.total_periodo(conn, de, ate)
    return {"total_centavos": total, "qtd_despesas": qtd}


def editar_despesa(
    conn: sqlite3.Connection,
    despesa_id: int,
    *,
    data_despesa: Optional[date] = None,
    categoria_id: Optional[int] = None,
    descricao: Optional[str] = None,
    valor_centavos: Optional[int] = None,
    forma_pagamento: Optional[FormaPagamento | str] = None,
) -> bool:
    if data_despesa is not None:
        validar_data(data_despesa)
    if valor_centavos is not None:
        validar_valor_positivo(valor_centavos)
    if descricao is not None:
        validar_descricao(descricao)
    forma_str: Optional[str] = None
    if forma_pagamento is not None:
        forma_str = forma_pagamento.value if isinstance(forma_pagamento, FormaPagamento) else forma_pagamento
        validar_forma_pagamento(forma_str)

    return despesa_repo.atualizar(
        conn,
        despesa_id,
        data_despesa=data_despesa,
        categoria_id=categoria_id,
        descricao=descricao.strip() if descricao else None,
        valor=valor_centavos,
        forma_pagamento=forma_str,
    )


def excluir_despesa(conn: sqlite3.Connection, despesa_id: int) -> bool:
    return despesa_repo.excluir(conn, despesa_id)


# ---------------------------------------------------------------------------
# Agregações para o Dashboard
# ---------------------------------------------------------------------------


def serie_diaria_despesa(
    conn: sqlite3.Connection, de: date, ate: date,
) -> list[dict]:
    if de > ate:
        raise ValidacaoError("A data inicial deve ser anterior ou igual à final.")
    return [dict(r) for r in despesa_repo.serie_diaria(conn, de, ate)]


def total_por_categoria(
    conn: sqlite3.Connection, de: date, ate: date,
) -> list[dict]:
    if de > ate:
        raise ValidacaoError("A data inicial deve ser anterior ou igual à final.")
    return [dict(r) for r in despesa_repo.total_por_categoria(conn, de, ate)]
