"""Entidades de assinatura: Plano, Assinatura e PagamentoAssinatura."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from app.domain.enums import FormaPagamento


@dataclass(frozen=True, slots=True)
class PlanoAssinatura:
    id: Optional[int]
    nome: str
    preco_mensal: int                           # centavos
    qtd_servicos_mes: Optional[int]             # None = ilimitado
    servicos_inclusos: tuple[int, ...] = field(default_factory=tuple)
    descricao: Optional[str] = None
    ativo: bool = True

    @property
    def ilimitado(self) -> bool:
        return self.qtd_servicos_mes is None


@dataclass(frozen=True, slots=True)
class Assinatura:
    id: Optional[int]
    cliente_id: int
    plano_id: int
    data_inicio: date
    dia_cobranca: int = 1
    data_fim: Optional[date] = None             # None = ativa

    def __post_init__(self) -> None:
        if not 1 <= self.dia_cobranca <= 28:
            raise ValueError("dia_cobranca deve estar entre 1 e 28")
        if self.data_fim is not None and self.data_fim < self.data_inicio:
            raise ValueError("data_fim não pode ser anterior a data_inicio")

    @property
    def ativa(self) -> bool:
        return self.data_fim is None


@dataclass(frozen=True, slots=True)
class PagamentoAssinatura:
    id: Optional[int]
    assinatura_id: int
    mes_referencia: str                         # "YYYY-MM"
    data_pagamento: date
    valor: int                                  # centavos
    forma_pagamento: FormaPagamento

    def __post_init__(self) -> None:
        if self.valor <= 0:
            raise ValueError("valor do pagamento deve ser > 0")
        if len(self.mes_referencia) != 7 or self.mes_referencia[4] != "-":
            raise ValueError("mes_referencia deve estar no formato 'YYYY-MM'")
