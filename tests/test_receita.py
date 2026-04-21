"""Testes integrados do fluxo de receitas (repo + service)."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from app.domain.enums import FormaPagamento
from app.repositories import receita_repo, servico_repo
from app.services import receita_service
from app.utils.validators import ValidacaoError


def _servico_id(conn: sqlite3.Connection, nome: str) -> int:
    return conn.execute("SELECT id FROM servico WHERE nome = ?", (nome,)).fetchone()["id"]


def test_registrar_atendimento_avulso(conn: sqlite3.Connection) -> None:
    sid = _servico_id(conn, "Corte de cabelo")
    rid = receita_service.registrar_atendimento_avulso(
        conn,
        servico_id=sid,
        valor_centavos=3500,
        forma_pagamento=FormaPagamento.PIX,
    )
    assert rid > 0

    row = receita_repo.obter(conn, rid)
    assert row["valor"] == 3500
    assert row["forma_pagamento"] == "PIX"
    assert row["data"] == date.today().isoformat()


def test_forma_pagamento_string(conn: sqlite3.Connection) -> None:
    sid = _servico_id(conn, "Barba")
    rid = receita_service.registrar_atendimento_avulso(
        conn, servico_id=sid, valor_centavos=2500, forma_pagamento="DINHEIRO"
    )
    assert receita_repo.obter(conn, rid)["forma_pagamento"] == "DINHEIRO"


def test_valor_zero_rejeita(conn: sqlite3.Connection) -> None:
    sid = _servico_id(conn, "Corte de cabelo")
    with pytest.raises(ValidacaoError, match="maior que zero"):
        receita_service.registrar_atendimento_avulso(
            conn, servico_id=sid, valor_centavos=0, forma_pagamento=FormaPagamento.PIX
        )


def test_forma_invalida_rejeita(conn: sqlite3.Connection) -> None:
    sid = _servico_id(conn, "Corte de cabelo")
    with pytest.raises(ValidacaoError, match="Forma de pagamento"):
        receita_service.registrar_atendimento_avulso(
            conn, servico_id=sid, valor_centavos=3500, forma_pagamento="CHEQUE"
        )


def test_data_futura_rejeita_por_padrao(conn: sqlite3.Connection) -> None:
    sid = _servico_id(conn, "Corte de cabelo")
    futuro = date.today() + timedelta(days=10)
    with pytest.raises(ValidacaoError, match="futuro"):
        receita_service.registrar_atendimento_avulso(
            conn, servico_id=sid, valor_centavos=3500,
            forma_pagamento=FormaPagamento.PIX, data_atendimento=futuro,
        )


def test_data_futura_com_confirmacao(conn: sqlite3.Connection) -> None:
    sid = _servico_id(conn, "Corte de cabelo")
    futuro = date.today() + timedelta(days=10)
    rid = receita_service.registrar_atendimento_avulso(
        conn, servico_id=sid, valor_centavos=3500,
        forma_pagamento=FormaPagamento.PIX, data_atendimento=futuro,
        permitir_data_futura=True,
    )
    assert receita_repo.obter(conn, rid) is not None


def test_servico_inexistente_rejeita(conn: sqlite3.Connection) -> None:
    with pytest.raises(ValidacaoError, match="não existe"):
        receita_service.registrar_atendimento_avulso(
            conn, servico_id=99999, valor_centavos=3500,
            forma_pagamento=FormaPagamento.PIX,
        )


def test_listar_periodo(conn: sqlite3.Connection) -> None:
    sid1 = _servico_id(conn, "Corte de cabelo")
    sid2 = _servico_id(conn, "Barba")
    hoje = date.today()
    ontem = hoje - timedelta(days=1)

    receita_service.registrar_atendimento_avulso(
        conn, servico_id=sid1, valor_centavos=3500, forma_pagamento=FormaPagamento.PIX,
        data_atendimento=ontem,
    )
    receita_service.registrar_atendimento_avulso(
        conn, servico_id=sid2, valor_centavos=2500, forma_pagamento=FormaPagamento.DINHEIRO,
    )

    rows = receita_service.listar_periodo(conn, hoje - timedelta(days=3), hoje)
    assert len(rows) == 2
    assert rows[0]["data"] == hoje.isoformat()        # ordenado desc
    assert rows[0]["servico_nome"] == "Barba"


def test_totais_periodo(conn: sqlite3.Connection) -> None:
    sid = _servico_id(conn, "Corte de cabelo")
    for _ in range(3):
        receita_service.registrar_atendimento_avulso(
            conn, servico_id=sid, valor_centavos=3500,
            forma_pagamento=FormaPagamento.PIX,
        )
    r = receita_service.totais_periodo(conn, date.today(), date.today())
    assert r == {"total_centavos": 10500, "qtd_atendimentos": 3}


def test_editar_atendimento(conn: sqlite3.Connection) -> None:
    sid = _servico_id(conn, "Corte de cabelo")
    rid = receita_service.registrar_atendimento_avulso(
        conn, servico_id=sid, valor_centavos=3500, forma_pagamento=FormaPagamento.PIX
    )
    assert receita_service.editar_atendimento(conn, rid, valor_centavos=4000)
    assert receita_repo.obter(conn, rid)["valor"] == 4000


def test_excluir_atendimento_grava_auditoria(conn: sqlite3.Connection) -> None:
    sid = _servico_id(conn, "Corte de cabelo")
    rid = receita_service.registrar_atendimento_avulso(
        conn, servico_id=sid, valor_centavos=3500, forma_pagamento=FormaPagamento.PIX
    )
    assert receita_service.excluir_atendimento(conn, rid)
    assert receita_repo.obter(conn, rid) is None

    n = conn.execute(
        "SELECT COUNT(*) FROM auditoria WHERE tabela='receita' AND registro_id=? AND acao='DELETE'",
        (rid,),
    ).fetchone()[0]
    assert n == 1


def test_periodo_invalido_rejeita(conn: sqlite3.Connection) -> None:
    with pytest.raises(ValidacaoError, match="anterior"):
        receita_service.listar_periodo(conn, date(2026, 5, 1), date(2026, 4, 1))


def test_servico_repo_listar_ativos(conn: sqlite3.Connection) -> None:
    ativos = servico_repo.listar_ativos(conn)
    assert len(ativos) == 37
    # Ordenados por `ordem`
    assert ativos[0]["nome"] == "Corte de cabelo"
