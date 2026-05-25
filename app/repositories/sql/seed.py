"""Seed inicial do banco SQLite por usuário (web).

Popula o DB com exemplos genéricos editáveis. Idempotente.
Valores em CENTAVOS.
"""

from __future__ import annotations

import sqlite3

# 2 serviços genéricos — renomeie em Configurações
_SERVICOS = [
    ("Serviço básico",    5000, "Serviço", 1),
    ("Serviço completo", 10000, "Serviço", 2),
]

# Categorias de despesa genéricas
_CATEGORIAS_DESPESA = [
    ("Insumos / Produtos",  "🧴"),
    ("Bebidas & Alimentos", "🥤"),
    ("Infraestrutura",      "🏠"),
    ("Manutenção",          "🔧"),
    ("Impostos",            "📄"),
    ("Pessoal",             "👤"),
    ("Outros",              "📦"),
]

# 2 itens frequentes de exemplo
_ITENS_FREQUENTES = [
    ("Material de uso",      "Insumos / Produtos", None),
    ("Conta fixa (aluguel)", "Infraestrutura",     None),
]

# 2 produtos genéricos no estoque — renomeie em Estoque
_PRODUTOS = [
    ("Produto exemplo 1", 1000, 2000, 5),
    ("Produto exemplo 2", 2000, 4000, 3),
]

_CONFIGS = [
    ("nome_empresa", "Meu Negócio"),
    ("meta_mensal",  "0"),
    ("ano_contabil", "2026"),
]


def apply_seed(conn: sqlite3.Connection) -> None:
    """Popula o espaço SQLite do usuário com o catálogo inicial. Idempotente."""
    row = conn.execute("SELECT COUNT(*) FROM servico").fetchone()
    if row[0] > 0:
        return  # já populado

    conn.execute("BEGIN")
    try:
        conn.executemany(
            "INSERT INTO servico (nome, preco_padrao, categoria_servico, ordem, ativo) VALUES (?, ?, ?, ?, 1)",
            _SERVICOS,
        )

        conn.executemany(
            "INSERT INTO categoria_despesa (nome, icone, ativo) VALUES (?, ?, 1)",
            _CATEGORIAS_DESPESA,
        )

        categorias = dict(
            conn.execute("SELECT nome, id FROM categoria_despesa").fetchall()
        )
        rows_itens = [
            (desc, categorias[cat_nome], valor)
            for desc, cat_nome, valor in _ITENS_FREQUENTES
            if cat_nome in categorias
        ]
        conn.executemany(
            "INSERT INTO item_despesa_frequente (descricao, categoria_id, valor_sugerido, vezes_usado, ativo) VALUES (?, ?, ?, 0, 1)",
            rows_itens,
        )

        conn.executemany(
            "INSERT OR IGNORE INTO config (chave, valor) VALUES (?, ?)",
            _CONFIGS,
        )

        conn.executemany(
            "INSERT OR IGNORE INTO produto (nome, preco_custo, preco_venda, quantidade_estoque) VALUES (?, ?, ?, ?)",
            _PRODUTOS,
        )

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
