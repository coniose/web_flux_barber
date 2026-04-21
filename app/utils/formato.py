"""Conversões e formatações pt-BR.

Regra dourada do projeto: valores monetários circulam internamente em
CENTAVOS (int) e só viram string/float na hora de apresentar.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Union

_MESES_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


# --------------------------------------------------------------- moeda ----


def reais_para_centavos(valor: Union[str, float, int]) -> int:
    """Converte um valor em reais (str 'R$ 1.234,50' / float 1234.50 / int 1234)
    para centavos (int).

    Aceita formatação brasileira (ponto milhar, vírgula decimal) e americana.
    """
    if isinstance(valor, int):
        return valor * 100
    if isinstance(valor, float):
        return int(round(valor * 100))

    s = valor.strip().replace("R$", "").replace(" ", "")
    if not s:
        raise ValueError("valor vazio")

    negativo = s.startswith("-")
    if negativo:
        s = s[1:]

    # Se tiver vírgula, assumimos que vírgula é decimal.
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    # Se só tiver ponto, deixa como está (decimal americano).

    try:
        reais = float(s)
    except ValueError as e:
        raise ValueError(f"valor monetário inválido: {valor!r}") from e

    centavos = int(round(reais * 100))
    return -centavos if negativo else centavos


def centavos_para_reais(centavos: int) -> float:
    """Converte centavos para reais em float. Útil para serialização/export."""
    return centavos / 100.0


def formatar_moeda(centavos: int, com_simbolo: bool = True) -> str:
    """Formata centavos em 'R$ 1.234,50' (pt-BR). Negativo: '-R$ 50,00'."""
    reais = abs(centavos) / 100.0
    # Formata com milhar/decimal americanos e depois inverte pra pt-BR.
    s = f"{reais:,.2f}"
    s = s.replace(",", "_").replace(".", ",").replace("_", ".")
    sinal = "-" if centavos < 0 else ""
    if com_simbolo:
        return f"{sinal}R$ {s}"
    return f"{sinal}{s}"


# --------------------------------------------------------------- datas ----


def formatar_data(d: Union[date, datetime, str]) -> str:
    """Formata data como 'dd/mm/aaaa'."""
    if isinstance(d, str):
        d = datetime.strptime(d, "%Y-%m-%d").date()
    elif isinstance(d, datetime):
        d = d.date()
    return d.strftime("%d/%m/%Y")


def mes_por_extenso(mes: int) -> str:
    """Retorna nome do mês em pt-BR (1 → 'janeiro')."""
    if not 1 <= mes <= 12:
        raise ValueError("mês deve estar entre 1 e 12")
    return _MESES_PT[mes - 1]


def iso_mes(d: Union[date, datetime, str]) -> str:
    """Retorna 'YYYY-MM' a partir de uma data."""
    if isinstance(d, str):
        d = datetime.strptime(d, "%Y-%m-%d").date()
    elif isinstance(d, datetime):
        d = d.date()
    return d.strftime("%Y-%m")
