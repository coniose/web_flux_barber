"""Enums centrais do domínio."""

from __future__ import annotations

from enum import Enum


class FormaPagamento(str, Enum):
    """Formas de pagamento aceitas no app. Bate com o CHECK do schema SQL."""

    PIX = "PIX"
    DINHEIRO = "DINHEIRO"
    MAQUININHA = "MAQUININHA"

    @classmethod
    def valores(cls) -> list[str]:
        return [m.value for m in cls]


class CategoriaServico(str, Enum):
    """Categorias do catálogo de serviços (apenas informativo)."""

    CORTE = "Corte"
    BARBA = "Barba"
    COMBO = "Combo"
    COLORACAO = "Coloração"
    TRATAMENTO = "Tratamento"
    PENTEADO = "Penteado"
    PROTESE = "Prótese"
    ESTETICA = "Estética"


class AcaoAuditoria(str, Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
