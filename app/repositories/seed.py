"""Seed inicial do banco — catálogo da barbearia brodz.

Popula o DB na 1ª abertura. Idempotente: só aplica se as tabelas estiverem vazias.

Valores em CENTAVOS. Tudo editável em runtime pela tela de Configurações.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

# =============================================================================
# SERVIÇOS (catálogo completo — 37 serviços)
#
# Tupla: (nome, preco_centavos, categoria_servico, ordem)
# Ordem menor aparece primeiro na tela de lançamento.
# =============================================================================
SERVICOS: list[tuple[str, int, str, int]] = [
    # Top 5 (uso alto → botão em destaque)
    ("Corte de cabelo",              3500, "Corte",      1),
    ("Corte + Barba",                6000, "Combo",      2),
    ("Barba",                        2500, "Barba",      3),
    ("Sobrancelhas",                 1000, "Estética",   4),
    ("Pezinho",                      1500, "Corte",      5),

    # Combos
    ("Corte + Sobrancelha",          4500, "Combo",     10),
    ("Corte + Barba + Sobrancelha",  7000, "Combo",     11),
    ("Corte + Cavanhaque",           5000, "Combo",     12),
    ("Corte + Bigode",               4500, "Combo",     13),
    ("Corte + Alisamento",           5500, "Combo",     14),
    ("Corte e penteado selado",      6000, "Combo",     15),

    # Barba
    ("Cavanhaque",                   1500, "Barba",     20),
    ("Bigode",                       1000, "Barba",     21),
    ("Barboterapia",                 3500, "Barba",     22),

    # Estética
    ("Limpeza de pele",              2000, "Estética",  30),
    ("Depilação nariz",              1000, "Estética",  31),

    # Coloração
    ("Matização",                    1000, "Coloração", 40),
    ("Pigmentação",                  1500, "Coloração", 41),
    ("Camuflagem",                   2000, "Coloração", 42),
    ("Reflexo",                      6000, "Coloração", 43),
    ("Luzes",                        6000, "Coloração", 44),
    ("Luzes platinada",              7000, "Coloração", 45),
    ("Platinado",                   13000, "Coloração", 46),

    # Tratamentos
    ("Alisante",                     2000, "Tratamento", 50),
    ("Relaxamento cachos",           2000, "Tratamento", 51),
    ("Hidratação térmica",           2500, "Tratamento", 52),
    ("Cacheado dedo liss",           3000, "Tratamento", 53),
    ("Frisado",                      5000, "Tratamento", 54),
    ("Progressiva",                  6000, "Tratamento", 55),

    # Penteados
    ("Penteado afro nudred",         1000, "Penteado",  60),
    ("Penteado dimil",               2500, "Penteado",  61),
    ("Penteado selado",              2500, "Penteado",  62),
    ("Penteado franjinha",           2500, "Penteado",  63),
    ("Penteado fio a fio",           6000, "Penteado",  64),

    # Próteses
    ("Prótese média franja",         8000, "Prótese",   70),
    ("Manutenção prótese",          15000, "Prótese",   71),
    ("Prótese fio a fio afro",      40000, "Prótese",   72),
]


# =============================================================================
# PLANOS DE ASSINATURA (5 planos atuais da brodz)
#
# Tupla: (nome, descricao, preco_mensal_centavos, qtd_servicos_mes_ou_None, [servicos_inclusos])
# qtd_servicos_mes=None significa ilimitado.
# =============================================================================
PLANOS: list[tuple[str, str, int, Optional[int], list[str]]] = [
    (
        "2 Cortes",
        "2 cortes de cabelo por mês",
        6000,
        2,
        ["Corte de cabelo"],
    ),
    (
        "4 Cortes",
        "4 cortes de cabelo por mês (candidato a R$ 105 no futuro)",
        11200,
        4,
        ["Corte de cabelo"],
    ),
    (
        "Corte + Barba",
        "Corte + barba ILIMITADO no mês",
        10000,
        None,
        ["Corte + Barba"],
    ),
    (
        "4× Corte + Barba",
        "4 combos de corte + barba por mês",
        19200,
        4,
        ["Corte + Barba"],
    ),
    (
        "4× Corte + Sobrancelha",
        "4 combos de corte + sobrancelha por mês",
        14000,
        4,
        ["Corte + Sobrancelha"],
    ),
]


# =============================================================================
# CATEGORIAS DE DESPESA
# =============================================================================
CATEGORIAS_DESPESA: list[tuple[str, str]] = [
    ("Insumos / Produtos",    "🧴"),
    ("Bebidas & Alimentos",   "🥤"),
    ("Infraestrutura",        "🏠"),
    ("Manutenção",            "🔧"),
    ("Impostos",              "📄"),
    ("Pessoal",               "👤"),
    ("Outros",                "📦"),
]


# =============================================================================
# ITENS FREQUENTES DE DESPESA (botões de 1 clique no modal)
#
# Tupla: (descricao, categoria_nome, valor_sugerido_centavos_ou_None)
# =============================================================================
ITENS_FREQUENTES: list[tuple[str, str, Optional[int]]] = [
    ("Lâmina",        "Insumos / Produtos",   3000),
    ("Álcool",        "Insumos / Produtos",   1000),
    ("Pano",          "Insumos / Produtos",   1500),
    ("Embalagem",     "Insumos / Produtos",   3000),
    ("Desinfetante",  "Insumos / Produtos",    400),
    ("Cloro",         "Insumos / Produtos",    800),
    ("Água galão",    "Infraestrutura",       1300),
    ("Copo",          "Bebidas & Alimentos",   600),
    ("Café",          "Bebidas & Alimentos",  5500),
    ("Açúcar",        "Bebidas & Alimentos",  1800),
    ("Filtro de café","Bebidas & Alimentos",   600),
    ("Bala",          "Bebidas & Alimentos",   400),
    ("Pirulito",      "Bebidas & Alimentos",   800),
]


# =============================================================================
# CONFIG CHAVE-VALOR
# =============================================================================
CONFIGS: list[tuple[str, str]] = [
    ("nome_empresa", "brodz"),
    ("meta_mensal",  "0"),         # centavos; 0 = sem meta
    ("ano_contabil", "2026"),
]


# -------------------------------------------------------------- apply ------


def apply_seed(conn: sqlite3.Connection) -> None:
    """Popula o DB com o catálogo inicial se estiver vazio. Idempotente."""
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM servico")
    if cur.fetchone()[0] > 0:
        return  # já populado

    cur.execute("BEGIN")
    try:
        _seed_servicos(cur)
        _seed_categorias_despesa(cur)
        _seed_itens_frequentes(cur)
        _seed_planos(cur)
        _seed_config(cur)
        cur.execute("COMMIT")
    except Exception:
        cur.execute("ROLLBACK")
        raise


def _seed_servicos(cur: sqlite3.Cursor) -> None:
    cur.executemany(
        "INSERT INTO servico (nome, preco_padrao, categoria_servico, ordem) VALUES (?, ?, ?, ?)",
        SERVICOS,
    )


def _seed_categorias_despesa(cur: sqlite3.Cursor) -> None:
    cur.executemany(
        "INSERT INTO categoria_despesa (nome, icone) VALUES (?, ?)",
        CATEGORIAS_DESPESA,
    )


def _seed_itens_frequentes(cur: sqlite3.Cursor) -> None:
    # Resolve categoria_id a partir do nome
    categorias = dict(cur.execute("SELECT nome, id FROM categoria_despesa").fetchall())
    rows = [
        (desc, categorias[cat_nome], valor)
        for desc, cat_nome, valor in ITENS_FREQUENTES
    ]
    cur.executemany(
        "INSERT INTO item_despesa_frequente (descricao, categoria_id, valor_sugerido) VALUES (?, ?, ?)",
        rows,
    )


def _seed_planos(cur: sqlite3.Cursor) -> None:
    servico_ids = dict(cur.execute("SELECT nome, id FROM servico").fetchall())

    for nome, descricao, preco, qtd, inclusos in PLANOS:
        cur.execute(
            """INSERT INTO plano_assinatura (nome, descricao, preco_mensal, qtd_servicos_mes)
               VALUES (?, ?, ?, ?)""",
            (nome, descricao, preco, qtd),
        )
        plano_id = cur.lastrowid
        for nome_servico in inclusos:
            sid = servico_ids.get(nome_servico)
            if sid is None:
                raise RuntimeError(
                    f"Serviço '{nome_servico}' do plano '{nome}' não existe no catálogo."
                )
            cur.execute(
                "INSERT INTO plano_servico (plano_id, servico_id) VALUES (?, ?)",
                (plano_id, sid),
            )


def _seed_config(cur: sqlite3.Cursor) -> None:
    cur.executemany(
        "INSERT INTO config (chave, valor) VALUES (?, ?)",
        CONFIGS,
    )
