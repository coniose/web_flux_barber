"""Repositórios SQLite por usuário — substitui app/repositories/fs/ na camada web."""

from . import (  # noqa: F401
    categoria_repo,
    config_repo,
    despesa_repo,
    item_frequente_repo,
    movimentacao_repo,
    produto_repo,
    receita_repo,
    seed,
    servico_repo,
)
