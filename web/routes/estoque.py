"""Tela de controle de estoque — produtos, compras e vendas."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from app.repositories.db import get_connection
from app.repositories import produto_repo, movimentacao_repo
from app.services import estoque_service
from app.utils.validators import ValidacaoError

estoque_bp = Blueprint("estoque", __name__)


@estoque_bp.route("/estoque")
@login_required
def index():
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    conn = get_connection()
    produtos = produto_repo.listar_todos(conn)
    resumo = estoque_service.resumo_periodo(conn, inicio_mes, hoje)
    movs = movimentacao_repo.listar_periodo(conn, inicio_mes, hoje)
    conn.close()
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
    conn = get_connection()
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
            custo_novo = round(float(custo_str) * 100)
            venda_novo = round(float(venda_str) * 100)
            produto_id = estoque_service.cadastrar_produto(
                conn,
                nome=nome,
                preco_custo=custo_novo,
                preco_venda=venda_novo,
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
    finally:
        conn.close()
    return redirect(url_for("estoque.index"))


@estoque_bp.route("/estoque/venda", methods=["POST"])
@login_required
def registrar_venda():
    conn = get_connection()
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
    finally:
        conn.close()
    return redirect(url_for("estoque.index"))


@estoque_bp.route("/estoque/ajuste", methods=["POST"])
@login_required
def ajustar():
    conn = get_connection()
    try:
        produto_id = int(request.form["produto_id"])
        nova_qtd = int(request.form["nova_quantidade"])
        observacao = request.form.get("observacao") or None
        estoque_service.ajustar_estoque(conn, produto_id=produto_id, nova_quantidade=nova_qtd, observacao=observacao)
        flash("Estoque ajustado.", "success")
    except (ValidacaoError, ValueError, KeyError) as e:
        flash(str(e), "error")
    finally:
        conn.close()
    return redirect(url_for("estoque.index"))


@estoque_bp.route("/api/produto/<int:produto_id>")
@login_required
def api_produto(produto_id: int):
    conn = get_connection()
    row = produto_repo.obter(conn, produto_id)
    conn.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "id": row["id"],
        "nome": row["nome"],
        "preco_custo": row["preco_custo"],
        "preco_venda": row["preco_venda"],
        "quantidade_estoque": row["quantidade_estoque"],
    })
