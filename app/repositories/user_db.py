"""Gerenciador de conexões SQLite por usuário.

Cada usuário tem seu próprio arquivo de banco de dados em:
  /data/users/{device_id}.db

O caminho base é derivado da variável de ambiente FLUXO_BARBER_DB
(mesma lógica de db.py). Se FLUXO_BARBER_DB aponta para
/data/fluxo_barber.db, os DBs de usuário ficam em /data/users/{device_id}.db.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

# ------------------------------------------------------------------ schema ---

_USER_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS servico (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    nome              TEXT    NOT NULL UNIQUE,
    preco_padrao      INTEGER NOT NULL CHECK (preco_padrao >= 0),
    ativo             INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
    ordem             INTEGER NOT NULL DEFAULT 999,
    categoria_servico TEXT,
    criado_em         TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_servico_ativo_ordem ON servico(ativo, ordem);

CREATE TABLE IF NOT EXISTS categoria_despesa (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome  TEXT    NOT NULL UNIQUE,
    icone TEXT,
    ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS item_despesa_frequente (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao      TEXT    NOT NULL UNIQUE,
    categoria_id   INTEGER NOT NULL REFERENCES categoria_despesa(id),
    valor_sugerido INTEGER CHECK (valor_sugerido IS NULL OR valor_sugerido > 0),
    vezes_usado    INTEGER NOT NULL DEFAULT 0,
    ativo          INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);
CREATE INDEX IF NOT EXISTS idx_item_freq_uso ON item_despesa_frequente(ativo, vezes_usado DESC);

CREATE TABLE IF NOT EXISTS produto (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    nome               TEXT    NOT NULL UNIQUE,
    descricao          TEXT,
    preco_custo        INTEGER NOT NULL CHECK (preco_custo >= 0),
    preco_venda        INTEGER NOT NULL CHECK (preco_venda >= 0),
    quantidade_estoque INTEGER NOT NULL DEFAULT 0,
    ativo              INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
    criado_em          TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_produto_ativo ON produto(ativo);

CREATE TABLE IF NOT EXISTS receita (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid            TEXT    UNIQUE,
    data            TEXT    NOT NULL,
    servico_id      INTEGER NOT NULL REFERENCES servico(id),
    servico_nome    TEXT    NOT NULL DEFAULT '',
    cliente_id      INTEGER,
    assinatura_id   INTEGER,
    valor           INTEGER NOT NULL CHECK (valor >= 0),
    forma_pagamento TEXT CHECK (forma_pagamento IS NULL OR forma_pagamento IN ('PIX', 'DINHEIRO', 'MAQUININHA')),
    observacao      TEXT,
    criado_em       TEXT    NOT NULL DEFAULT (datetime('now')),
    editado_em      TEXT,
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_receita_data       ON receita(data);
CREATE INDEX IF NOT EXISTS idx_receita_updated_at ON receita(updated_at);

CREATE TABLE IF NOT EXISTS despesa (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid              TEXT    UNIQUE,
    data              TEXT    NOT NULL,
    categoria_id      INTEGER NOT NULL REFERENCES categoria_despesa(id),
    categoria_nome    TEXT    NOT NULL DEFAULT '',
    categoria_icone   TEXT    NOT NULL DEFAULT '📦',
    item_frequente_id INTEGER REFERENCES item_despesa_frequente(id),
    descricao         TEXT    NOT NULL,
    valor             INTEGER NOT NULL CHECK (valor > 0),
    forma_pagamento   TEXT    NOT NULL CHECK (forma_pagamento IN ('PIX', 'DINHEIRO', 'MAQUININHA')),
    criado_em         TEXT    NOT NULL DEFAULT (datetime('now')),
    editado_em        TEXT,
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_despesa_data       ON despesa(data);
CREATE INDEX IF NOT EXISTS idx_despesa_categoria  ON despesa(categoria_id);
CREATE INDEX IF NOT EXISTS idx_despesa_updated_at ON despesa(updated_at);

CREATE TABLE IF NOT EXISTS movimentacao_estoque (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id     INTEGER NOT NULL REFERENCES produto(id),
    produto_nome   TEXT    NOT NULL DEFAULT '',
    tipo           TEXT    NOT NULL CHECK (tipo IN ('COMPRA', 'VENDA', 'AJUSTE')),
    quantidade     INTEGER NOT NULL CHECK (quantidade != 0),
    preco_unitario INTEGER NOT NULL CHECK (preco_unitario >= 0),
    total_centavos INTEGER NOT NULL,
    data           TEXT    NOT NULL,
    observacao     TEXT,
    criado_em      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_mov_produto ON movimentacao_estoque(produto_id);
CREATE INDEX IF NOT EXISTS idx_mov_data    ON movimentacao_estoque(data);
CREATE INDEX IF NOT EXISTS idx_mov_tipo    ON movimentacao_estoque(tipo);

CREATE TABLE IF NOT EXISTS config (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
"""


# ------------------------------------------------------------------- paths ---


def _users_dir() -> Path:
    """Retorna o diretório onde ficam os DBs de usuário.

    Derivado de FLUXO_BARBER_DB: se essa env var aponta para
    /data/fluxo_barber.db, os DBs de usuário ficam em /data/users/.
    Se a variável não estiver definida, usa o mesmo diretório pai do
    default_db_path() de db.py.
    """
    override = os.environ.get("FLUXO_BARBER_DB")
    if override:
        base_dir = Path(override).expanduser().resolve().parent
    else:
        import sys

        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
            base_dir = Path(appdata) / "FluxoBarber"
        else:
            base_dir = Path.home() / ".fluxo_barber"

    users_dir = base_dir / "users"
    users_dir.mkdir(parents=True, exist_ok=True)
    return users_dir


def _user_db_path(device_id: str) -> Path:
    """Retorna o caminho do banco SQLite de um usuário específico."""
    return _users_dir() / f"{device_id}.db"


# ----------------------------------------------------------------- conexão ---


def get_user_connection(device_id: str) -> sqlite3.Connection:
    """Abre conexão SQLite para o usuário e garante que o schema existe.

    - WAL mode para melhor concorrência.
    - foreign_keys ON.
    - row_factory = sqlite3.Row para acesso por nome de coluna.
    - Aplica o schema (idempotente via CREATE IF NOT EXISTS).
    - Aplica o seed inicial se o banco estiver vazio.
    """
    db_path = _user_db_path(device_id)
    conn = sqlite3.connect(str(db_path), isolation_level=None)  # autocommit
    conn.row_factory = sqlite3.Row
    conn.executescript(_USER_SCHEMA_SQL)

    # Aplica seed inicial se ainda não foi populado
    from app.repositories.sql.seed import apply_seed
    apply_seed(conn)

    return conn


def ensure_user_db(device_id: str) -> sqlite3.Connection:
    """Alias legível para rotas — abre e inicializa o DB do usuário."""
    return get_user_connection(device_id)
