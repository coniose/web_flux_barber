"""Testes das regras de integridade do schema (CHECKs, UNIQUE, FKs)
e validações do domínio (dataclasses)."""

from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from app.domain.assinatura import Assinatura, PagamentoAssinatura
from app.domain.despesa import Despesa
from app.domain.enums import FormaPagamento
from app.domain.receita import Receita


# =============================================================================
# Helpers para montar cenário mínimo
# =============================================================================


def _criar_cliente(conn: sqlite3.Connection, nome: str = "João Teste") -> int:
    cur = conn.execute(
        "INSERT INTO cliente (nome, telefone) VALUES (?, ?)", (nome, "11999999999")
    )
    return cur.lastrowid


def _id_servico(conn: sqlite3.Connection, nome: str) -> int:
    return conn.execute("SELECT id FROM servico WHERE nome = ?", (nome,)).fetchone()["id"]


def _id_plano(conn: sqlite3.Connection, nome: str) -> int:
    return conn.execute("SELECT id FROM plano_assinatura WHERE nome = ?", (nome,)).fetchone()["id"]


def _criar_assinatura(conn: sqlite3.Connection, cliente_id: int, plano_nome: str) -> int:
    cur = conn.execute(
        """INSERT INTO assinatura (cliente_id, plano_id, data_inicio, dia_cobranca)
           VALUES (?, ?, ?, ?)""",
        (cliente_id, _id_plano(conn, plano_nome), "2026-04-01", 5),
    )
    return cur.lastrowid


# =============================================================================
# Testes: schema (CHECKs, UNIQUE, FKs)
# =============================================================================


def test_receita_valor_positivo_exige_forma_pagamento(conn: sqlite3.Connection) -> None:
    """CHECK (valor = 0 OR forma_pagamento IS NOT NULL)"""
    sid = _id_servico(conn, "Corte de cabelo")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO receita (data, servico_id, valor) VALUES (?, ?, ?)",
            ("2026-04-17", sid, 3500),  # valor > 0 mas sem forma
        )


def test_receita_coberta_por_plano_aceita_valor_zero_sem_forma(conn: sqlite3.Connection) -> None:
    cid = _criar_cliente(conn)
    aid = _criar_assinatura(conn, cid, "4 Cortes")
    sid = _id_servico(conn, "Corte de cabelo")
    conn.execute(
        """INSERT INTO receita (data, servico_id, cliente_id, assinatura_id, valor)
           VALUES (?, ?, ?, ?, 0)""",
        ("2026-04-17", sid, cid, aid),
    )


def test_receita_com_assinatura_exige_cliente(conn: sqlite3.Connection) -> None:
    """CHECK (assinatura_id IS NULL OR cliente_id IS NOT NULL)"""
    cid = _criar_cliente(conn)
    aid = _criar_assinatura(conn, cid, "4 Cortes")
    sid = _id_servico(conn, "Corte de cabelo")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO receita (data, servico_id, assinatura_id, valor)
               VALUES (?, ?, ?, 0)""",
            ("2026-04-17", sid, aid),  # cliente_id ausente
        )


def test_pagamento_assinatura_unique_mes(conn: sqlite3.Connection) -> None:
    """UNIQUE(assinatura_id, mes_referencia) — impede duplicar cobrança do mesmo mês."""
    cid = _criar_cliente(conn)
    aid = _criar_assinatura(conn, cid, "4 Cortes")

    conn.execute(
        """INSERT INTO pagamento_assinatura
             (assinatura_id, mes_referencia, data_pagamento, valor, forma_pagamento)
           VALUES (?, ?, ?, ?, ?)""",
        (aid, "2026-04", "2026-04-05", 11200, "PIX"),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO pagamento_assinatura
                 (assinatura_id, mes_referencia, data_pagamento, valor, forma_pagamento)
               VALUES (?, ?, ?, ?, ?)""",
            (aid, "2026-04", "2026-04-06", 11200, "DINHEIRO"),
        )


def test_forma_pagamento_invalida_rejeita(conn: sqlite3.Connection) -> None:
    cid = _criar_cliente(conn)
    aid = _criar_assinatura(conn, cid, "4 Cortes")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO pagamento_assinatura
                 (assinatura_id, mes_referencia, data_pagamento, valor, forma_pagamento)
               VALUES (?, ?, ?, ?, ?)""",
            (aid, "2026-05", "2026-05-01", 10000, "CHEQUE"),
        )


def test_fk_violation_receita_sem_servico(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO receita (data, servico_id, valor, forma_pagamento) VALUES (?, ?, ?, ?)",
            ("2026-04-17", 99999, 3500, "PIX"),
        )


def test_despesa_valor_positivo(conn: sqlite3.Connection) -> None:
    """CHECK (valor > 0) na despesa."""
    cat_id = conn.execute("SELECT id FROM categoria_despesa WHERE nome = 'Outros'").fetchone()["id"]
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO despesa (data, categoria_id, descricao, valor, forma_pagamento)
               VALUES (?, ?, ?, ?, ?)""",
            ("2026-04-17", cat_id, "teste", 0, "PIX"),
        )


def test_dia_cobranca_entre_1_e_28(conn: sqlite3.Connection) -> None:
    cid = _criar_cliente(conn)
    pid = _id_plano(conn, "4 Cortes")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO assinatura (cliente_id, plano_id, data_inicio, dia_cobranca)
               VALUES (?, ?, ?, ?)""",
            (cid, pid, "2026-04-01", 31),
        )


def test_assinatura_data_fim_nao_anterior_a_inicio(conn: sqlite3.Connection) -> None:
    cid = _criar_cliente(conn)
    pid = _id_plano(conn, "4 Cortes")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO assinatura (cliente_id, plano_id, data_inicio, data_fim, dia_cobranca)
               VALUES (?, ?, ?, ?, ?)""",
            (cid, pid, "2026-04-01", "2026-03-01", 1),
        )


# =============================================================================
# Testes: validações de domínio (dataclasses)
# =============================================================================


def test_receita_dataclass_valida() -> None:
    r = Receita(
        id=None,
        data=date(2026, 4, 17),
        servico_id=1,
        valor=3500,
        forma_pagamento=FormaPagamento.PIX,
    )
    assert r.valor == 3500


def test_receita_valor_positivo_exige_forma_pagamento_dataclass() -> None:
    with pytest.raises(ValueError, match="forma_pagamento"):
        Receita(id=None, data=date(2026, 4, 17), servico_id=1, valor=3500, forma_pagamento=None)


def test_receita_assinatura_exige_cliente_dataclass() -> None:
    with pytest.raises(ValueError, match="cliente_id"):
        Receita(id=None, data=date(2026, 4, 17), servico_id=1, valor=0, assinatura_id=1)


def test_receita_valor_negativo_rejeita() -> None:
    with pytest.raises(ValueError, match="negativo"):
        Receita(
            id=None, data=date(2026, 4, 17), servico_id=1, valor=-100,
            forma_pagamento=FormaPagamento.PIX,
        )


def test_despesa_valor_zero_rejeita() -> None:
    with pytest.raises(ValueError, match="valor"):
        Despesa(
            id=None, data=date(2026, 4, 17), categoria_id=1,
            descricao="teste", valor=0, forma_pagamento=FormaPagamento.PIX,
        )


def test_despesa_descricao_vazia_rejeita() -> None:
    with pytest.raises(ValueError, match="descricao"):
        Despesa(
            id=None, data=date(2026, 4, 17), categoria_id=1,
            descricao="   ", valor=100, forma_pagamento=FormaPagamento.PIX,
        )


def test_assinatura_dia_cobranca_invalido() -> None:
    with pytest.raises(ValueError, match="dia_cobranca"):
        Assinatura(id=None, cliente_id=1, plano_id=1, data_inicio=date(2026, 4, 1), dia_cobranca=30)


def test_assinatura_data_fim_invalida() -> None:
    with pytest.raises(ValueError, match="data_fim"):
        Assinatura(
            id=None, cliente_id=1, plano_id=1,
            data_inicio=date(2026, 4, 1), data_fim=date(2026, 3, 1),
        )


def test_pagamento_mes_referencia_formato() -> None:
    with pytest.raises(ValueError, match="mes_referencia"):
        PagamentoAssinatura(
            id=None, assinatura_id=1, mes_referencia="04/2026",
            data_pagamento=date(2026, 4, 5), valor=10000,
            forma_pagamento=FormaPagamento.PIX,
        )
