"""Tela de lançamento rápido — atendimentos e despesas."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from app.repositories.fs import servico_repo, categoria_repo, item_frequente_repo, produto_repo
from app.services import receita_service, despesa_service, estoque_service
from app.utils.validators import ValidacaoError
from web.models import get_store

lancamento_bp = Blueprint("lancamento", __name__)


@lancamento_bp.route("/lancar")
@login_required
def index():
    store = get_store()
    servicos = servico_repo.listar_ativos(store)
    categorias = categoria_repo.listar_ativas(store)
    itens_raw = item_frequente_repo.listar_ativos_ordenado_por_uso(store)

    # Enriquecer itens com dados da categoria para o template
    cat_map = {c["id"]: c for c in categorias}
    itens = []
    for item in itens_raw:
        cat = cat_map.get(item.get("categoria_id"), {})
        itens.append({
            **item,
            "cat_nome": cat.get("nome", ""),
            "cat_icone": cat.get("icone", "📦"),
        })

    produtos = produto_repo.listar_ativos(store)
    return render_template(
        "lancamento.html",
        servicos=servicos,
        categorias=categorias,
        itens=itens,
        produtos=produtos,
        hoje=date.today().isoformat(),
    )


@lancamento_bp.route("/lancar/atendimento", methods=["POST"])
@login_required
def registrar_atendimento():
    store = get_store()
    try:
        servico_id = int(request.form["servico_id"])
        valor_reais = float(request.form["valor"].replace(",", "."))
        valor_centavos = round(valor_reais * 100)
        forma = request.form["forma_pagamento"]
        data_str = request.form.get("data") or date.today().isoformat()
        observacao = request.form.get("observacao") or None
        data_obj = date.fromisoformat(data_str)

        receita_service.registrar_atendimento_avulso(
            store,
            servico_id=servico_id,
            valor_centavos=valor_centavos,
            forma_pagamento=forma,
            data_atendimento=data_obj,
            observacao=observacao,
        )
        flash("Atendimento registrado!", "success")
    except (ValidacaoError, ValueError, KeyError) as e:
        flash(str(e), "error")

    return redirect(url_for("lancamento.index"))


@lancamento_bp.route("/lancar/despesa", methods=["POST"])
@login_required
def registrar_despesa():
    store = get_store()
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
            store,
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

    return redirect(url_for("lancamento.index"))


@lancamento_bp.route("/api/sync", methods=["POST"])
@login_required
def api_sync():
    """Recebe lote de operações da fila offline do cliente e persiste no Firestore."""
    store = get_store()
    payload = request.get_json(silent=True) or {}
    ops = payload.get("operations", [])
    synced = []
    failed = []

    for op in ops:
        op_id = op.get("id", "")
        try:
            tipo = op.get("type")
            d = op.get("data", {})
            data_obj = date.fromisoformat(d.get("data") or date.today().isoformat())

            if tipo == "atendimento":
                receita_service.registrar_atendimento_avulso(
                    store,
                    servico_id=int(d["servico_id"]),
                    valor_centavos=round(float(d["valor"]) * 100),
                    forma_pagamento=d["forma_pagamento"],
                    data_atendimento=data_obj,
                    observacao=d.get("observacao") or None,
                )
            elif tipo == "despesa":
                despesa_service.registrar_despesa(
                    store,
                    categoria_id=int(d["categoria_id"]),
                    descricao=d["descricao"],
                    valor_centavos=round(float(d["valor"]) * 100),
                    forma_pagamento=d["forma_pagamento"],
                    data_despesa=data_obj,
                    item_frequente_id=int(d["item_frequente_id"]) if d.get("item_frequente_id") else None,
                )
            elif tipo == "venda_produto":
                estoque_service.registrar_venda(
                    store,
                    produto_id=int(d["produto_id"]),
                    quantidade=int(d["quantidade"]),
                    preco_venda_unitario=round(float(d["preco_venda"]) * 100),
                    data_venda=data_obj,
                )
            else:
                failed.append(op_id)
                continue

            synced.append(op_id)
        except Exception:
            failed.append(op_id)

    return jsonify({"synced": synced, "failed": failed})


@lancamento_bp.route("/api/servico/<int:servico_id>")
@login_required
def api_servico(servico_id: int):
    store = get_store()
    row = servico_repo.obter(store, servico_id)
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({"id": row["id"], "nome": row["nome"], "preco_padrao": row["preco_padrao"]})
