"""Regras de negócio para receitas (Fase 1: atendimentos avulsos)."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Optional

from app.domain.enums import FormaPagamento
from app.repositories import receita_repo, servico_repo
from app.utils.validators import (
    ValidacaoError,
    validar_data,
    validar_forma_pagamento,
    validar_valor_positivo,
)


def registrar_atendimento_avulso(
    conn: sqlite3.Connection,
    *,
    servico_id: int,
    valor_centavos: int,
    forma_pagamento: FormaPagamento | str,
    data_atendimento: date | None = None,
    cliente_id: Optional[int] = None,
    observacao: Optional[str] = None,
    permitir_data_futura: bool = False,
) -> int:
    """Registra atendimento avulso (sem vínculo de assinatura).

    Retorna o ID da receita criada.
    Lança ``ValidacaoError`` para erros amigáveis (sem quebrar a UI).
    """
    data_atendimento = data_atendimento or date.today()
    validar_data(data_atendimento, permitir_futuro=permitir_data_futura)
    validar_valor_positivo(valor_centavos)

    if isinstance(forma_pagamento, FormaPagamento):
        forma_str = forma_pagamento.value
    else:
        forma_str = forma_pagamento
        validar_forma_pagamento(forma_str)

    if servico_repo.obter(conn, servico_id) is None:
        raise ValidacaoError(f"Serviço #{servico_id} não existe.")

    try:
        return receita_repo.inserir(
            conn,
            data_atendimento=data_atendimento,
            servico_id=servico_id,
            valor=valor_centavos,
            forma_pagamento=forma_str,
            cliente_id=cliente_id,
            observacao=observacao,
        )
    except sqlite3.IntegrityError as e:
        raise ValidacaoError(f"Não foi possível registrar: {e}") from e


def listar_periodo(conn: sqlite3.Connection, de: date, ate: date) -> list[sqlite3.Row]:
    if de > ate:
        raise ValidacaoError("A data inicial deve ser anterior ou igual à final.")
    return receita_repo.listar_periodo(conn, de, ate)


def totais_periodo(conn: sqlite3.Connection, de: date, ate: date) -> dict:
    total, qtd = receita_repo.total_periodo(conn, de, ate)
    return {"total_centavos": total, "qtd_atendimentos": qtd}


def editar_atendimento(
    conn: sqlite3.Connection,
    receita_id: int,
    *,
    data_atendimento: Optional[date] = None,
    servico_id: Optional[int] = None,
    valor_centavos: Optional[int] = None,
    forma_pagamento: Optional[FormaPagamento | str] = None,
    observacao: Optional[str] = None,
) -> bool:
    if data_atendimento is not None:
        validar_data(data_atendimento)
    if valor_centavos is not None:
        validar_valor_positivo(valor_centavos, zero_permitido=True)
    forma_str: Optional[str] = None
    if forma_pagamento is not None:
        forma_str = forma_pagamento.value if isinstance(forma_pagamento, FormaPagamento) else forma_pagamento
        validar_forma_pagamento(forma_str)

    return receita_repo.atualizar(
        conn,
        receita_id,
        data_atendimento=data_atendimento,
        servico_id=servico_id,
        valor=valor_centavos,
        forma_pagamento=forma_str,
        observacao=observacao,
    )


def excluir_atendimento(conn: sqlite3.Connection, receita_id: int) -> bool:
    return receita_repo.excluir(conn, receita_id)


# ---------------------------------------------------------------------------
# Agregações para o Dashboard
# ---------------------------------------------------------------------------


def serie_diaria_receita(
    conn: sqlite3.Connection, de: date, ate: date,
) -> list[dict]:
    """Retorna [{data: 'YYYY-MM-DD', total: int, qtd: int}] para o período."""
    if de > ate:
        raise ValidacaoError("A data inicial deve ser anterior ou igual à final.")
    return [dict(r) for r in receita_repo.serie_diaria(conn, de, ate)]


def ranking_servicos(
    conn: sqlite3.Connection, de: date, ate: date, limite: int = 10,
) -> list[dict]:
    if de > ate:
        raise ValidacaoError("A data inicial deve ser anterior ou igual à final.")
    return [dict(r) for r in receita_repo.ranking_servicos(conn, de, ate, limite)]


def mix_forma_pagamento(
    conn: sqlite3.Connection, de: date, ate: date,
) -> list[dict]:
    if de > ate:
        raise ValidacaoError("A data inicial deve ser anterior ou igual à final.")
    return [dict(r) for r in receita_repo.mix_forma_pagamento(conn, de, ate)]
