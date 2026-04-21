"""Entidade Cliente."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True, slots=True)
class Cliente:
    id: Optional[int]
    nome: str
    telefone: Optional[str] = None
    aniversario: Optional[date] = None
    observacao: Optional[str] = None
