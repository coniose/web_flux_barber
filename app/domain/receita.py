"""Entidade Receita (atendimento avulso ou consumo de plano)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.domain.enums import FormaPagamento


@dataclass(frozen=True, slots=True)
class Receita:
    """Um atendimento registrado.

    - ``valor`` em centavos. Zero quando a receita é 100% coberta por uma assinatura
      (nesse caso, ``assinatura_id`` é obrigatório e ``forma_pagamento`` pode ser None).
    - Quando ``valor > 0``, ``forma_pagamento`` é obrigatório.
    - Se ``assinatura_id`` não for None, ``cliente_id`` é obrigatório.
    """

    id: Optional[int]
    data: date
    servico_id: int
    valor: int                                  # centavos
    cliente_id: Optional[int] = None
    assinatura_id: Optional[int] = None
    forma_pagamento: Optional[FormaPagamento] = None
    observacao: Optional[str] = None

    def __post_init__(self) -> None:
        if self.valor < 0:
            raise ValueError("valor não pode ser negativo")
        if self.valor > 0 and self.forma_pagamento is None:
            raise ValueError("forma_pagamento é obrigatório quando valor > 0")
        if self.assinatura_id is not None and self.cliente_id is None:
            raise ValueError("cliente_id é obrigatório quando assinatura_id está presente")
