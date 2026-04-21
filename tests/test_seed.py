"""Testes do seed — contagens e mapeamentos do catálogo inicial."""

from __future__ import annotations

import sqlite3

from app.repositories.seed import (
    CATEGORIAS_DESPESA,
    CONFIGS,
    ITENS_FREQUENTES,
    PLANOS,
    SERVICOS,
    apply_seed,
)


def test_contagens(conn: sqlite3.Connection) -> None:
    assert conn.execute("SELECT COUNT(*) FROM servico").fetchone()[0] == len(SERVICOS) == 37
    assert conn.execute("SELECT COUNT(*) FROM plano_assinatura").fetchone()[0] == len(PLANOS) == 5
    assert conn.execute("SELECT COUNT(*) FROM categoria_despesa").fetchone()[0] == len(CATEGORIAS_DESPESA) == 7
    assert conn.execute("SELECT COUNT(*) FROM item_despesa_frequente").fetchone()[0] == len(ITENS_FREQUENTES) == 13
    assert conn.execute("SELECT COUNT(*) FROM config").fetchone()[0] == len(CONFIGS)


def test_seed_idempotente(conn: sqlite3.Connection) -> None:
    """Chamar apply_seed no DB já populado não deve duplicar nada."""
    antes = conn.execute("SELECT COUNT(*) FROM servico").fetchone()[0]
    apply_seed(conn)
    depois = conn.execute("SELECT COUNT(*) FROM servico").fetchone()[0]
    assert antes == depois


def test_servicos_ordenados(conn: sqlite3.Connection) -> None:
    top = conn.execute("SELECT nome FROM servico ORDER BY ordem LIMIT 5").fetchall()
    nomes = [r["nome"] for r in top]
    assert nomes == ["Corte de cabelo", "Corte + Barba", "Barba", "Sobrancelhas", "Pezinho"]


def test_precos_em_centavos(conn: sqlite3.Connection) -> None:
    """Confere preços-chave do catálogo em centavos."""
    row = conn.execute("SELECT preco_padrao FROM servico WHERE nome = ?", ("Corte de cabelo",)).fetchone()
    assert row["preco_padrao"] == 3500

    row = conn.execute("SELECT preco_padrao FROM servico WHERE nome = ?", ("Corte + Barba",)).fetchone()
    assert row["preco_padrao"] == 6000

    row = conn.execute("SELECT preco_padrao FROM servico WHERE nome = ?", ("Prótese fio a fio afro",)).fetchone()
    assert row["preco_padrao"] == 40000


def test_plano_ilimitado(conn: sqlite3.Connection) -> None:
    """Plano 'Corte + Barba' deve ter qtd_servicos_mes = NULL (ilimitado)."""
    row = conn.execute(
        "SELECT qtd_servicos_mes FROM plano_assinatura WHERE nome = ?",
        ("Corte + Barba",),
    ).fetchone()
    assert row["qtd_servicos_mes"] is None


def test_planos_com_cota(conn: sqlite3.Connection) -> None:
    """Planos com cota finita têm quantidade correta."""
    mapping = {
        "2 Cortes": 2,
        "4 Cortes": 4,
        "4× Corte + Barba": 4,
        "4× Corte + Sobrancelha": 4,
    }
    for nome, qtd in mapping.items():
        row = conn.execute(
            "SELECT qtd_servicos_mes, preco_mensal FROM plano_assinatura WHERE nome = ?",
            (nome,),
        ).fetchone()
        assert row is not None, f"plano ausente: {nome}"
        assert row["qtd_servicos_mes"] == qtd


def test_plano_servico_mapping(conn: sqlite3.Connection) -> None:
    """Plano '2 Cortes' deve cobrir o serviço 'Corte de cabelo'."""
    row = conn.execute(
        """SELECT s.nome
             FROM plano_servico ps
             JOIN plano_assinatura p ON p.id = ps.plano_id
             JOIN servico s ON s.id = ps.servico_id
            WHERE p.nome = ?""",
        ("2 Cortes",),
    ).fetchall()
    assert {r["nome"] for r in row} == {"Corte de cabelo"}


def test_item_frequente_categoria(conn: sqlite3.Connection) -> None:
    """Item 'Café' deve estar em 'Bebidas & Alimentos'."""
    row = conn.execute(
        """SELECT c.nome AS cat, i.valor_sugerido
             FROM item_despesa_frequente i
             JOIN categoria_despesa c ON c.id = i.categoria_id
            WHERE i.descricao = 'Café'"""
    ).fetchone()
    assert row["cat"] == "Bebidas & Alimentos"
    assert row["valor_sugerido"] == 5500
