"""Fixtures compartilhadas pelos testes.

Cada teste que pede ``conn`` recebe um DB SQLite em arquivo temporário,
com schema aplicado e seed opcional. Totalmente isolado entre testes.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator

import pytest

from app.repositories.db import ensure_db, get_connection, init_schema
from app.repositories.seed import apply_seed


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Caminho para um DB temporário por teste."""
    return tmp_path / "fluxo_barber_test.db"


@pytest.fixture
def empty_conn(db_path: Path) -> Iterator[sqlite3.Connection]:
    """DB com schema aplicado, sem seed."""
    conn = get_connection(db_path)
    init_schema(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def conn(db_path: Path) -> Iterator[sqlite3.Connection]:
    """DB com schema aplicado E seed populado."""
    c = ensure_db(db_path, seed=True)
    try:
        yield c
    finally:
        c.close()


@pytest.fixture
def conn_seeded_manual(empty_conn: sqlite3.Connection) -> sqlite3.Connection:
    """DB com schema e seed — versão que aplica seed explicitamente (para testar apply_seed)."""
    apply_seed(empty_conn)
    return empty_conn
