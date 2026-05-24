"""Regras de negócio para controle de estoque."""

from __future__ import annotations

from datetime import date
from typing import Optional

from app.repositories.sql import produto_repo, movimentacao_repo
from app.utils.validators import ValidacaoError, validar_data, validar_valor_positivo


def cadastrar_produto(
    conn,
    *,
    nome: str,
    preco_custo: int,
    preco_venda: int,
    descricao: Optional[str] = None,
    quantidade_inicial: int = 0,
) -> int:
    if not nome.strip():
        raise ValidacaoError("Nome do produto é obrigatório.")
    validar_valor_positivo(preco_custo, zero_permitido=True)
    validar_valor_positivo(preco_venda, zero_permitido=True)
    if preco_venda < preco_custo:
        raise ValidacaoError("Preço de venda não pode ser menor que o custo.")
    if quantidade_inicial < 0:
        raise ValidacaoError("Quantidade inicial não pode ser negativa.")
    return produto_repo.inserir(
        conn,
        nome=nome,
        preco_custo=preco_custo,
        preco_venda=preco_venda,
        descricao=descricao,
        quantidade_inicial=quantidade_inicial,
    )


def registrar_compra(
    conn,
    *,
    produto_id: int,
    quantidade: int,
    preco_custo_unitario: int,
    data_compra: Optional[date] = None,
    observacao: Optional[str] = None,
    permitir_data_futura: bool = False,
) -> int:
    data_compra = data_compra or date.today()
    validar_data(data_compra, permitir_futuro=permitir_data_futura)
    if quantidade <= 0:
        raise ValidacaoError("Quantidade deve ser maior que zero.")
    validar_valor_positivo(preco_custo_unitario, zero_permitido=True)

    produto = produto_repo.obter(conn, produto_id)
    if produto is None:
        raise ValidacaoError(f"Produto #{produto_id} não encontrado.")

    mov_id = movimentacao_repo.inserir(
        conn,
        produto_id=produto_id,
        produto_nome=produto.get("nome", ""),
        tipo="COMPRA",
        quantidade=quantidade,
        preco_unitario=preco_custo_unitario,
        data_mov=data_compra,
        observacao=observacao,
    )
    produto_repo.ajustar_quantidade(conn, produto_id, +quantidade)
    return mov_id


def registrar_venda(
    conn,
    *,
    produto_id: int,
    quantidade: int,
    preco_venda_unitario: int,
    data_venda: Optional[date] = None,
    observacao: Optional[str] = None,
    permitir_data_futura: bool = False,
) -> int:
    data_venda = data_venda or date.today()
    validar_data(data_venda, permitir_futuro=permitir_data_futura)
    if quantidade <= 0:
        raise ValidacaoError("Quantidade deve ser maior que zero.")
    validar_valor_positivo(preco_venda_unitario)

    produto = produto_repo.obter(conn, produto_id)
    if produto is None:
        raise ValidacaoError(f"Produto #{produto_id} não encontrado.")
    if produto["quantidade_estoque"] < quantidade:
        raise ValidacaoError(
            f"Estoque insuficiente: {produto['quantidade_estoque']} unidade(s) disponível(is)."
        )

    mov_id = movimentacao_repo.inserir(
        conn,
        produto_id=produto_id,
        produto_nome=produto.get("nome", ""),
        tipo="VENDA",
        quantidade=-quantidade,
        preco_unitario=preco_venda_unitario,
        data_mov=data_venda,
        observacao=observacao,
    )
    produto_repo.ajustar_quantidade(conn, produto_id, -quantidade)
    return mov_id


def ajustar_estoque(
    conn,
    *,
    produto_id: int,
    nova_quantidade: int,
    observacao: Optional[str] = None,
) -> int:
    if nova_quantidade < 0:
        raise ValidacaoError("Quantidade não pode ser negativa.")
    produto = produto_repo.obter(conn, produto_id)
    if produto is None:
        raise ValidacaoError(f"Produto #{produto_id} não encontrado.")

    delta = nova_quantidade - produto["quantidade_estoque"]
    if delta == 0:
        raise ValidacaoError("Nova quantidade igual à atual — nenhum ajuste necessário.")

    mov_id = movimentacao_repo.inserir(
        conn,
        produto_id=produto_id,
        produto_nome=produto.get("nome", ""),
        tipo="AJUSTE",
        quantidade=delta,
        preco_unitario=0,
        data_mov=date.today(),
        observacao=observacao or "Ajuste manual de inventário",
    )
    produto_repo.ajustar_quantidade(conn, produto_id, delta)
    return mov_id


def excluir_movimentacao(conn, *, mov_id: int) -> None:
    mov = movimentacao_repo.obter(conn, mov_id)
    if mov is None:
        raise ValidacaoError("Movimentação não encontrada.")

    produto = produto_repo.obter(conn, mov["produto_id"])
    if produto is None:
        raise ValidacaoError("Produto associado não encontrado.")

    # Reverte o delta: COMPRA guardou +N, VENDA guardou -N, AJUSTE guardou delta
    delta_reverso = -mov["quantidade"]

    nova_qtd = produto["quantidade_estoque"] + delta_reverso
    if nova_qtd < 0:
        raise ValidacaoError(
            f"Não é possível excluir: o estoque de '{produto['nome']}' ficaria negativo ({nova_qtd})."
        )

    movimentacao_repo.excluir(conn, mov_id)
    produto_repo.ajustar_quantidade(conn, mov["produto_id"], delta_reverso)


def resumo_periodo(conn, de: date, ate: date) -> dict:
    totais = movimentacao_repo.totais_periodo(conn, de, ate)
    ranking = movimentacao_repo.ranking_produtos(conn, de, ate, limite=5)
    margem = totais["VENDA"]["total"] - totais["COMPRA"]["total"]
    return {
        "compras": totais["COMPRA"],
        "vendas": totais["VENDA"],
        "margem_centavos": margem,
        "ranking_produtos": ranking,
    }
