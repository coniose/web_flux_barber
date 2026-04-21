"""Testes dos utilitários de formatação."""

from __future__ import annotations

from datetime import date

import pytest

from app.utils.formato import (
    centavos_para_reais,
    formatar_data,
    formatar_moeda,
    iso_mes,
    mes_por_extenso,
    reais_para_centavos,
)


def test_reais_para_centavos_string_pt_br() -> None:
    assert reais_para_centavos("R$ 1.234,50") == 123450
    assert reais_para_centavos("35,00") == 3500
    assert reais_para_centavos("100") == 10000
    assert reais_para_centavos("R$ 0,01") == 1


def test_reais_para_centavos_float() -> None:
    assert reais_para_centavos(35.0) == 3500
    assert reais_para_centavos(0.1) == 10  # arredondamento correto
    assert reais_para_centavos(1234.56) == 123456


def test_reais_para_centavos_int() -> None:
    assert reais_para_centavos(35) == 3500


def test_reais_para_centavos_negativo() -> None:
    assert reais_para_centavos("-R$ 50,00") == -5000


def test_reais_para_centavos_invalido() -> None:
    with pytest.raises(ValueError):
        reais_para_centavos("abc")
    with pytest.raises(ValueError):
        reais_para_centavos("")


def test_formatar_moeda_pt_br() -> None:
    assert formatar_moeda(3500) == "R$ 35,00"
    assert formatar_moeda(123450) == "R$ 1.234,50"
    assert formatar_moeda(1) == "R$ 0,01"
    assert formatar_moeda(0) == "R$ 0,00"
    assert formatar_moeda(-5000) == "-R$ 50,00"


def test_formatar_moeda_sem_simbolo() -> None:
    assert formatar_moeda(3500, com_simbolo=False) == "35,00"


def test_round_trip_centavos() -> None:
    """reais_para_centavos(formatar_moeda(x)) == x"""
    for valor in (1, 100, 3500, 12345, 999999):
        s = formatar_moeda(valor)
        assert reais_para_centavos(s) == valor


def test_centavos_para_reais() -> None:
    assert centavos_para_reais(3500) == 35.0
    assert centavos_para_reais(1) == 0.01


def test_formatar_data() -> None:
    assert formatar_data(date(2026, 4, 17)) == "17/04/2026"
    assert formatar_data("2026-04-17") == "17/04/2026"


def test_mes_por_extenso() -> None:
    assert mes_por_extenso(3) == "março"
    assert mes_por_extenso(12) == "dezembro"
    with pytest.raises(ValueError):
        mes_por_extenso(13)


def test_iso_mes() -> None:
    assert iso_mes(date(2026, 4, 17)) == "2026-04"
    assert iso_mes("2026-04-17") == "2026-04"
