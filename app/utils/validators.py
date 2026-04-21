"""Validações de campos que entram do UI."""

from __future__ import annotations

from datetime import date


class ValidacaoError(ValueError):
    """Erro de validação de entrada — mensagem amigável ao usuário final."""


def validar_data(d: date, *, permitir_futuro: bool = False, hoje: date | None = None) -> None:
    """Bloqueia datas futuras a menos que ``permitir_futuro=True``."""
    hoje = hoje or date.today()
    if not permitir_futuro and d > hoje:
        raise ValidacaoError(
            f"A data {d.strftime('%d/%m/%Y')} está no futuro. Confirme antes de prosseguir."
        )


def validar_valor_positivo(centavos: int, *, zero_permitido: bool = False) -> None:
    if centavos < 0:
        raise ValidacaoError("Valor não pode ser negativo.")
    if centavos == 0 and not zero_permitido:
        raise ValidacaoError("Valor deve ser maior que zero.")


def validar_forma_pagamento(forma: str) -> None:
    from app.domain.enums import FormaPagamento
    if forma not in FormaPagamento.valores():
        raise ValidacaoError(
            f"Forma de pagamento inválida: {forma!r}. Use PIX, DINHEIRO ou MAQUININHA."
        )


def validar_descricao(descricao: str) -> None:
    if not descricao or not descricao.strip():
        raise ValidacaoError("A descrição não pode ficar em branco.")
