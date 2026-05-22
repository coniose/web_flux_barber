"""Tela de lançamento rápido — atendimentos e despesas."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from app.repositories.db import get_connection
from app.repositories import servico_repo, categoria_repo, item_frequente_repo
from app.services import receita_service, despesa_service
from app.utils.validators import ValidacaoError

lancamento_bp = Blueprint("lancamento", __name__)


@lancamento_bp.route("/lancar")
@login_required
def index():
    conn = get_connection()
    servicos = conn.execute(
        "SELECT * FROM servico WHERE ativo = 1 ORDER BY ordem, nome"
    ).fetchall()
    categorias = conn.execute(
        "SELECT * FROM categoria_despesa WHERE ativo = 1 ORDER BY nome"
    ).fetchall()
    itens = conn.execute(
        """SELECT i.*, c.nome AS cat_nome, c.icone AS cat_icone
             FROM item_despesa_frequente i
             JOIN categoria_despesa c ON c.id = i.categoria_id
            WHERE i.ativo = 1
            ORDER BY i.vezes_usado DESC, i.descricao"""
    ).fetchall()
    conn.close()
    return render_template(
        "lancamento.html",
        servicos=servicos,
        categorias=categorias,
        itens=itens,
        hoje=date.today().isoformat(),
    )


@lancamento_bp.route("/lancar/atendimento", methods=["POST"])
@login_required
def registrar_atendimento():
    conn = get_connection()
    try:
        servico_id = int(request.form["servico_id"])
        valor_reais = float(request.form["valor"].replace(",", "."))
        valor_centavos = round(valor_reais * 100)
        forma = request.form["forma_pagamento"]
        data_str = request.form.get("data") or date.today().isoformat()
        observacao = request.form.get("observacao") or None
        data_obj = date.fromisoformat(data_str)

        receita_service.registrar_atendimento_avulso(
            conn,
            servico_id=servico_id,
            valor_centavos=valor_centavos,
            forma_pagamento=forma,
            data_atendimento=data_obj,
            observacao=observacao,
        )
        flash("Atendimento registrado!", "success")
    except (ValidacaoError, ValueError, KeyError) as e:
        flash(str(e), "error")
    finally:
        conn.close()

    return redirect(url_for("lancamento.index"))


@lancamento_bp.route("/lancar/despesa", methods=["POST"])
@login_required
def registrar_despesa():
    conn = get_connection()
    try:
        categoria_id = int(request.form["categoria_id"])
        descricao = request.form["descricao"].strip()
        valor_reais = float(request.form["valor"].replace(",", "."))
        valor_centavos = round(valor_reais * 100)
        forma = request.form["forma_pagamento"]
        data_str = request.form.get("data") or date.today().isoformat()
        item_id = request.form.get("item_frequente_id")
        data_obj = date.fromisoformat(data_str)

        despesa_service.registrar_despesa(
            conn,
            data_despesa=data_obj,
            categoria_id=categoria_id,
            descricao=descricao,
            valor_centavos=valor_centavos,
            forma_pagamento=forma,
            item_frequente_id=int(item_id) if item_id else None,
        )
        flash("Despesa registrada!", "success")
    except (ValidacaoError, ValueError, KeyError) as e:
        flash(str(e), "error")
    finally:
        conn.close()

    return redirect(url_for("lancamento.index"))


@lancamento_bp.route("/api/servico/<int:servico_id>")
@login_required
def api_servico(servico_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM servico WHERE id = ?", (servico_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({"id": row["id"], "nome": row["nome"], "preco_padrao": row["preco_padrao"]})
