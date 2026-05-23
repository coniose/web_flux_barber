"""Regras de negócio para receitas (Fase 1: atendimentos avulsos)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from app.domain.enums import FormaPagamento
from app.repositories.sql import receita_repo, servico_repo
from app.utils.validators import (
    ValidacaoError,
    validar_data,
    validar_forma_pagamento,
    validar_valor_positivo,
)


def registrar_atendimento_avulso(
    conn,
    *,
    servico_id: int,
    valor_centavos: int,
    forma_pagamento: FormaPagamento | str,
    data_atendimento: date | None = None,
    cliente_id: Optional[int] = None,
    observacao: Optional[str] = None,
    permitir_data_futura: bool = False,
) -> int:
    data_atendimento = data_atendimento or date.today()
    validar_data(data_atendimento, permitir_futuro=permitir_data_futura)
    validar_valor_positivo(valor_centavos)

    if isinstance(forma_pagamento, FormaPagamento):
        forma_str = forma_pagamento.value
    else:
        forma_str = forma_pagamento
        validar_forma_pagamento(forma_str)

    servico = servico_repo.obter(conn, servico_id)
    if servico is None:
        raise ValidacaoError(f"Serviço #{servico_id} não existe.")

    return receita_repo.inserir(
        conn,
        data_atendimento=data_atendimento,
        servico_id=servico_id,
        servico_nome=servico.get("nome", ""),
        valor=valor_centavos,
        forma_pagamento=forma_str,
        cliente_id=cliente_id,
        observacao=observacao,
    )


def listar_periodo(conn, de: date, ate: date) -> list[dict]:
    if de > ate:
        raise ValidacaoError("A data inicial deve ser anterior ou igual à final.")
    return receita_repo.listar_periodo(conn, de, ate)


def totais_periodo(conn, de: date, ate: date) -> dict:
    total, qtd = receita_repo.total_periodo(conn, de, ate)
    return {"total_centavos": total, "qtd_atendimentos": qtd}


def excluir_atendimento(conn, receita_id: int) -> bool:
    return receita_repo.excluir(conn, receita_id)


# ---------------------------------------------------------------------------
# Agregações para o Dashboard
# ---------------------------------------------------------------------------


def serie_diaria_receita(conn, de: date, ate: date) -> list[dict]:
    if de > ate:
        raise ValidacaoError("A data inicial deve ser anterior ou igual à final.")
    return receita_repo.serie_diaria(conn, de, ate)


def ranking_servicos(conn, de: date, ate: date, limite: int = 10) -> list[dict]:
    if de > ate:
        raise ValidacaoError("A data inicial deve ser anterior ou igual à final.")
    return receita_repo.ranking_servicos(conn, de, ate, limite)


def mix_forma_pagamento(conn, de: date, ate: date) -> list[dict]:
    if de > ate:
        raise ValidacaoError("A data inicial deve ser anterior ou igual à final.")
    return receita_repo.mix_forma_pagamento(conn, de, ate)
