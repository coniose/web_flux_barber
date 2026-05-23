"""Seed inicial do Firestore — catálogo completo da barbearia brodz.

Chamado uma vez quando um novo usuário se registra.
Idempotente: só aplica se a coleção servico estiver vazia.
"""

from __future__ import annotations

from app.repositories.seed import (
    CATEGORIAS_DESPESA,
    CONFIGS,
    ITENS_FREQUENTES,
    SERVICOS,
)

from . import categoria_repo, config_repo, item_frequente_repo, servico_repo
from ._util import new_id
from .store import BarberStore


def apply_seed(store: BarberStore) -> None:
    """Popula o espaço Firestore do usuário com o catálogo inicial. Idempotente."""
    # Verifica se já foi populado
    if list(store.col("servico").limit(1).stream()):
        return

    cat_ids: dict[str, int] = {}

    for nome, icone in CATEGORIAS_DESPESA:
        cid = new_id()
        store.col("categoria_despesa").document(str(cid)).set({
            "id": cid, "nome": nome, "icone": icone, "ativo": True,
        })
        cat_ids[nome] = cid

    for nome, preco, categoria_servico, ordem in SERVICOS:
        sid = new_id()
        store.col("servico").document(str(sid)).set({
            "id": sid,
            "nome": nome,
            "preco_padrao": preco,
            "categoria_servico": categoria_servico,
            "ordem": ordem,
            "ativo": True,
        })

    for descricao, cat_nome, valor_sugerido in ITENS_FREQUENTES:
        cid = cat_ids.get(cat_nome)
        if cid is None:
            continue
        iid = new_id()
        store.col("item_despesa_frequente").document(str(iid)).set({
            "id": iid,
            "descricao": descricao,
            "categoria_id": cid,
            "valor_sugerido": valor_sugerido,
            "vezes_usado": 0,
            "ativo": True,
        })

    for chave, valor in CONFIGS:
        store.col("config").document(chave).set({"chave": chave, "valor": valor})
