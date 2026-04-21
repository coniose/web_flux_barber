"""Entidade Despesa."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.domain.enums import FormaPagamento


@dataclass(frozen=True, slots=True)
class Despesa:
    id: Optional[int]
    data: date
    categoria_id: int
    descricao: str
    valor: int                                  # centavos, sempre > 0
    forma_pagamento: FormaPagamento
    item_frequente_id: Optional[int] = None

    def __post_init__(self) -> None:
        if self.valor <= 0:
            raise ValueError("valor da despesa deve ser > 0")
        if not self.descricao or not self.descricao.strip():
            raise ValueError("descricao é obrigatória")
