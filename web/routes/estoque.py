"""Tela de controle de estoque — produtos, compras e vendas."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from app.repositories.fs import produto_repo, movimentacao_repo
from app.services import estoque_service
from app.utils.validators import ValidacaoError
from web.models import get_store

estoque_bp = Blueprint("estoque", __name__)


@estoque_bp.route("/estoque")
@login_required
def index():
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    store = get_store()
    produtos = produto_repo.listar_todos(store)
    resumo = estoque_service.resumo_periodo(store, inicio_mes, hoje)
    movs = movimentacao_repo.listar_periodo(store, inicio_mes, hoje)
    return render_template(
        "estoque.html",
        produtos=produtos,
        resumo=resumo,
        movimentacoes=movs,
        hoje=hoje,
        inicio_mes=inicio_mes,
    )


@estoque_bp.route("/estoque/compra", methods=["POST"])
@login_required
def registrar_compra():
    store = get_store()
    try:
        pid_raw = request.form["produto_id"]
        quantidade = int(request.form["quantidade"])
        preco_str = request.form["preco_custo"].replace(",", ".")
        preco_unitario = round(float(preco_str) * 100)
        data_str = request.form.get("data") or date.today().isoformat()
        observacao = request.form.get("observacao") or None

        if pid_raw == "__novo__":
            nome = (request.form.get("novo_nome") or "").strip()
            custo_str = (request.form.get("novo_preco_custo") or "0").replace(",", ".")
            venda_str = (request.form.get("novo_preco_venda") or "0").replace(",", ".")
            produto_id = estoque_service.cadastrar_produto(
                store,
                nome=nome,
                preco_custo=round(float(custo_str) * 100),
                preco_venda=round(float(venda_str) * 100),
            )
        else:
            produto_id = int(pid_raw)

        estoque_service.registrar_compra(
            store,
            produto_id=produto_id,
            quantidade=quantidade,
            preco_custo_unitario=preco_unitario,
            data_compra=date.fromisoformat(data_str),
            observacao=observacao,
        )
        flash("Compra registrada! Estoque atualizado.", "success")
    except (ValidacaoError, ValueError, KeyError) as e:
        flash(str(e), "error")
    return redirect(url_for("estoque.index"))


@estoque_bp.route("/estoque/venda", methods=["POST"])
@login_required
def registrar_venda():
    store = get_store()
    try:
        produto_id = int(request.form["produto_id"])
        quantidade = int(request.form["quantidade"])
        preco_str = request.form["preco_venda"].replace(",", ".")
        preco_unitario = round(float(preco_str) * 100)
        data_str = request.form.get("data") or date.today().isoformat()
        observacao = request.form.get("observacao") or None

        estoque_service.registrar_venda(
            store,
            produto_id=produto_id,
            quantidade=quantidade,
            preco_venda_unitario=preco_unitario,
            data_venda=date.fromisoformat(data_str),
            observacao=observacao,
        )
        flash("Venda registrada!", "success")
    except (ValidacaoError, ValueError, KeyError) as e:
        flash(str(e), "error")
    return redirect(url_for("estoque.index"))


@estoque_bp.route("/estoque/ajuste", methods=["POST"])
@login_required
def ajustar():
    store = get_store()
    try:
        produto_id = int(request.form["produto_id"])
        nova_qtd = int(request.form["nova_quantidade"])
        observacao = request.form.get("observacao") or None
        estoque_service.ajustar_estoque(store, produto_id=produto_id, nova_quantidade=nova_qtd, observacao=observacao)
        flash("Estoque ajustado.", "success")
    except (ValidacaoError, ValueError, KeyError) as e:
        flash(str(e), "error")
    return redirect(url_for("estoque.index"))


@estoque_bp.route("/api/produto/<int:produto_id>")
@login_required
def api_produto(produto_id: int):
    store = get_store()
    row = produto_repo.obter(store, produto_id)
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "id": row["id"],
        "nome": row["nome"],
        "preco_custo": row["preco_custo"],
        "preco_venda": row["preco_venda"],
        "quantidade_estoque": row["quantidade_estoque"],
    })
