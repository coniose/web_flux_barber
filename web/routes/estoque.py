"""Tela de controle de estoque — produtos, compras e vendas."""

from __future__ import annotations

from datetime import date, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from app.repositories.sql import produto_repo, movimentacao_repo
from app.services import estoque_service
from app.utils.validators import ValidacaoError
from web.models import get_user_conn

estoque_bp = Blueprint("estoque", __name__)


@estoque_bp.route("/estoque")
@login_required
def index():
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    sessenta_dias = hoje - timedelta(days=60)
    conn = get_user_conn()
    produtos = produto_repo.listar_todos(conn)
    resumo = estoque_service.resumo_periodo(conn, inicio_mes, hoje)
    movs = movimentacao_repo.listar_periodo(conn, sessenta_dias, hoje)
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
    conn = get_user_conn()
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
                conn,
                nome=nome,
                preco_custo=round(float(custo_str) * 100),
                preco_venda=round(float(venda_str) * 100),
            )
        else:
            produto_id = int(pid_raw)

        estoque_service.registrar_compra(
            conn,
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
    conn = get_user_conn()
    try:
        produto_id = int(request.form["produto_id"])
        quantidade = int(request.form["quantidade"])
        preco_str = request.form["preco_venda"].replace(",", ".")
        preco_unitario = round(float(preco_str) * 100)
        data_str = request.form.get("data") or date.today().isoformat()
        observacao = request.form.get("observacao") or None

        estoque_service.registrar_venda(
            conn,
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
    conn = get_user_conn()
    try:
        produto_id = int(request.form["produto_id"])
        nova_qtd = int(request.form["nova_quantidade"])
        observacao = request.form.get("observacao") or None
        estoque_service.ajustar_estoque(conn, produto_id=produto_id, nova_quantidade=nova_qtd, observacao=observacao)
        flash("Estoque ajustado.", "success")
    except (ValidacaoError, ValueError, KeyError) as e:
        flash(str(e), "error")
    return redirect(url_for("estoque.index"))


@estoque_bp.route("/estoque/movimentacao/<int:mov_id>/excluir", methods=["POST"])
@login_required
def excluir_movimentacao(mov_id: int):
    conn = get_user_conn()
    try:
        estoque_service.excluir_movimentacao(conn, mov_id=mov_id)
        flash("Movimentação excluída e estoque revertido.", "success")
    except (ValidacaoError, ValueError) as e:
        flash(str(e), "error")
    return redirect(url_for("estoque.index"))


@estoque_bp.route("/estoque/editar", methods=["POST"])
@login_required
def editar_produto():
    conn = get_user_conn()
    try:
        produto_id = int(request.form["produto_id"])
        nome = request.form["nome"].strip()
        custo_str = request.form["preco_custo"].replace(",", ".")
        venda_str = request.form["preco_venda"].replace(",", ".")
        descricao = request.form.get("descricao", "").strip() or None
        produto_repo.atualizar(
            conn,
            produto_id,
            nome=nome,
            preco_custo=round(float(custo_str) * 100),
            preco_venda=round(float(venda_str) * 100),
            descricao=descricao,
        )
        flash("Produto atualizado.", "success")
    except (ValidacaoError, ValueError, KeyError) as e:
        flash(str(e), "error")
    return redirect(url_for("estoque.index"))


@estoque_bp.route("/estoque/desativar", methods=["POST"])
@login_required
def desativar_produto():
    conn = get_user_conn()
    try:
        produto_id = int(request.form["produto_id"])
        produto = produto_repo.obter(conn, produto_id)
        if produto and produto["quantidade_estoque"] > 0:
            estoque_service.ajustar_estoque(
                conn, produto_id=produto_id, nova_quantidade=0, observacao="Produto desativado"
            )
        produto_repo.atualizar(conn, produto_id, ativo=0)
        flash("Produto desativado. Histórico de movimentações preservado.", "success")
    except (ValidacaoError, ValueError, KeyError) as e:
        flash(str(e), "error")
    return redirect(url_for("estoque.index"))


@estoque_bp.route("/api/produto/<int:produto_id>")
@login_required
def api_produto(produto_id: int):
    conn = get_user_conn()
    row = produto_repo.obter(conn, produto_id)
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "id": row["id"],
        "nome": row["nome"],
        "preco_custo": row["preco_custo"],
        "preco_venda": row["preco_venda"],
        "quantidade_estoque": row["quantidade_estoque"],
    })
