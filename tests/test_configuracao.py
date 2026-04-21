"""Testes do config_repo e configuracao_service."""

from __future__ import annotations

import sqlite3

import pytest

from app.repositories import config_repo
from app.services import configuracao_service


def test_get_set(conn: sqlite3.Connection) -> None:
    config_repo.definir(conn, "teste", "hello")
    assert config_repo.obter(conn, "teste") == "hello"
    # Atualizar chave existente
    config_repo.definir(conn, "teste", "world")
    assert config_repo.obter(conn, "teste") == "world"


def test_default_quando_ausente(conn: sqlite3.Connection) -> None:
    assert config_repo.obter(conn, "nao_existe", "fallback") == "fallback"


def test_nome_empresa_seed(conn: sqlite3.Connection) -> None:
    assert configuracao_service.nome_empresa(conn) == "brodz"


def test_meta_mensal_default(conn: sqlite3.Connection) -> None:
    assert configuracao_service.meta_mensal_centavos(conn) == 0


def test_definir_meta(conn: sqlite3.Connection) -> None:
    configuracao_service.definir_meta_mensal(conn, 1500000)
    assert configuracao_service.meta_mensal_centavos(conn) == 1500000


def test_definir_meta_negativa_rejeita(conn: sqlite3.Connection) -> None:
    with pytest.raises(ValueError, match="negativa"):
        configuracao_service.definir_meta_mensal(conn, -100)


def test_definir_nome_empresa(conn: sqlite3.Connection) -> None:
    configuracao_service.definir_nome_empresa(conn, "Barbearia Brodz")
    assert configuracao_service.nome_empresa(conn) == "Barbearia Brodz"


def test_nome_vazio_rejeita(conn: sqlite3.Connection) -> None:
    with pytest.raises(ValueError, match="vazio"):
        configuracao_service.definir_nome_empresa(conn, "   ")


def test_obter_todos(conn: sqlite3.Connection) -> None:
    d = config_repo.obter_todos(conn)
    assert "nome_empresa" in d
    assert "meta_mensal" in d
    assert "ano_contabil" in d
