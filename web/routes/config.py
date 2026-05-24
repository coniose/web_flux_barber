"""Painel de configurações — serviços, categorias, itens, produtos, conta."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash

from app.repositories.db import get_connection
from app.repositories.sql import categoria_repo, config_repo, item_frequente_repo, produto_repo, servico_repo
from app.utils.validators import ValidacaoError
from web.models import get_user_conn

config_bp = Blueprint("config", __name__)

TABS = ("negocio", "servicos", "categorias", "itens", "produtos", "conta")


def _redir(tab: str):
    return redirect(url_for("config.index", tab=tab))


@config_bp.route("/config")
@login_required
def index():
    tab = request.args.get("tab", "servicos")
    if tab not in TABS:
        tab = "servicos"
    conn = get_user_conn()
    servicos = servico_repo.listar_todos(conn)
    categorias = categoria_repo.listar_todas(conn)
    itens_raw = item_frequente_repo.listar_todos(conn)
    cat_map = {c["id"]: c for c in categorias}
    itens = [{**i, "cat_nome": cat_map.get(i.get("categoria_id"), {}).get("nome", ""), "cat_icone": cat_map.get(i.get("categoria_id"), {}).get("icone", "📦")} for i in itens_raw]
    produtos = produto_repo.listar_todos(conn)
    negocio = {
        "nome_negocio": config_repo.get_config(conn, "nome_negocio") or "",
        "descricao_negocio": config_repo.get_config(conn, "descricao_negocio") or "",
        "tipo_trabalho": config_repo.get_config(conn, "tipo_trabalho") or "ambos",
        "formas_pagamento": (config_repo.get_config(conn, "formas_pagamento") or "PIX,DINHEIRO,MAQUININHA").split(","),
        "horario_trabalho": config_repo.get_config(conn, "horario_trabalho") or "",
    }
    return render_template(
        "config.html",
        tab=tab,
        servicos=servicos,
        categorias=categorias,
        itens=itens,
        produtos=produtos,
        negocio=negocio,
    )


# ── Serviços ──────────────────────────────────────────────────────────────────

@config_bp.route("/config/servico/novo", methods=["POST"])
@login_required
def servico_novo():
    conn = get_user_conn()
    try:
        nome = request.form["nome"].strip()
        preco = round(float(request.form["preco_padrao"].replace(",", ".")) * 100)
        categoria = request.form.get("categoria_servico") or None
        ordem = int(request.form.get("ordem") or 999)
        if not nome:
            raise ValidacaoError("Nome é obrigatório.")
        servico_repo.criar(conn, nome=nome, preco_padrao=preco,
                           categoria_servico=categoria, ordem=ordem)
        flash("Serviço criado.", "success")
    except (ValidacaoError, ValueError) as e:
        flash(str(e), "error")
    return _redir("servicos")


@config_bp.route("/config/servico/<int:sid>/edit", methods=["POST"])
@login_required
def servico_edit(sid: int):
    conn = get_user_conn()
    try:
        nome = request.form["nome"].strip()
        preco = round(float(request.form["preco_padrao"].replace(",", ".")) * 100)
        categoria = request.form.get("categoria_servico") or None
        ordem = int(request.form.get("ordem") or 999)
        if not nome:
            raise ValidacaoError("Nome é obrigatório.")
        servico_repo.atualizar(conn, sid, nome=nome, preco_padrao=preco,
                               categoria_servico=categoria, ordem=ordem)
        flash("Serviço atualizado.", "success")
    except (ValidacaoError, ValueError) as e:
        flash(str(e), "error")
    return _redir("servicos")


@config_bp.route("/config/servico/<int:sid>/toggle", methods=["POST"])
@login_required
def servico_toggle(sid: int):
    conn = get_user_conn()
    row = servico_repo.obter(conn, sid)
    if row:
        novo = not bool(row.get("ativo", True))
        servico_repo.atualizar(conn, sid, ativo=novo)
        flash("Serviço " + ("ativado" if novo else "desativado") + ".", "success")
    return _redir("servicos")


# ── Categorias ────────────────────────────────────────────────────────────────

@config_bp.route("/config/categoria/nova", methods=["POST"])
@login_required
def categoria_nova():
    conn = get_user_conn()
    try:
        nome = request.form["nome"].strip()
        icone = request.form.get("icone") or "📦"
        if not nome:
            raise ValidacaoError("Nome é obrigatório.")
        categoria_repo.criar(conn, nome=nome, icone=icone)
        flash("Categoria criada.", "success")
    except (ValidacaoError, ValueError) as e:
        flash(str(e), "error")
    return _redir("categorias")


@config_bp.route("/config/categoria/<int:cid>/edit", methods=["POST"])
@login_required
def categoria_edit(cid: int):
    conn = get_user_conn()
    try:
        nome = request.form["nome"].strip()
        icone = request.form.get("icone") or "📦"
        if not nome:
            raise ValidacaoError("Nome é obrigatório.")
        categoria_repo.atualizar(conn, cid, nome=nome, icone=icone)
        flash("Categoria atualizada.", "success")
    except (ValidacaoError, ValueError) as e:
        flash(str(e), "error")
    return _redir("categorias")


@config_bp.route("/config/categoria/<int:cid>/toggle", methods=["POST"])
@login_required
def categoria_toggle(cid: int):
    conn = get_user_conn()
    row = categoria_repo.obter(conn, cid)
    if row:
        novo = not bool(row.get("ativo", True))
        categoria_repo.atualizar(conn, cid, ativo=novo)
        flash("Categoria " + ("ativada" if novo else "desativada") + ".", "success")
    return _redir("categorias")


# ── Itens frequentes ──────────────────────────────────────────────────────────

@config_bp.route("/config/item/novo", methods=["POST"])
@login_required
def item_novo():
    conn = get_user_conn()
    try:
        descricao = request.form["descricao"].strip()
        categoria_id = int(request.form["categoria_id"])
        val_str = (request.form.get("valor_sugerido") or "").strip()
        valor = round(float(val_str.replace(",", ".")) * 100) if val_str else None
        if not descricao:
            raise ValidacaoError("Descrição é obrigatória.")
        item_frequente_repo.criar(conn, descricao=descricao,
                                  categoria_id=categoria_id, valor_sugerido=valor)
        flash("Item criado.", "success")
    except (ValidacaoError, ValueError) as e:
        flash(str(e), "error")
    return _redir("itens")


@config_bp.route("/config/item/<int:iid>/edit", methods=["POST"])
@login_required
def item_edit(iid: int):
    conn = get_user_conn()
    try:
        descricao = request.form["descricao"].strip()
        categoria_id = int(request.form["categoria_id"])
        val_str = (request.form.get("valor_sugerido") or "").strip()
        valor = round(float(val_str.replace(",", ".")) * 100) if val_str else None
        if not descricao:
            raise ValidacaoError("Descrição é obrigatória.")
        item_frequente_repo.atualizar(conn, iid, descricao=descricao,
                                     categoria_id=categoria_id, valor_sugerido=valor)
        flash("Item atualizado.", "success")
    except (ValidacaoError, ValueError) as e:
        flash(str(e), "error")
    return _redir("itens")


@config_bp.route("/config/item/<int:iid>/toggle", methods=["POST"])
@login_required
def item_toggle(iid: int):
    conn = get_user_conn()
    row = item_frequente_repo.obter(conn, iid)
    if row:
        novo = not bool(row.get("ativo", True))
        item_frequente_repo.atualizar(conn, iid, ativo=novo)
        flash("Item " + ("ativado" if novo else "desativado") + ".", "success")
    return _redir("itens")


# ── Produtos ──────────────────────────────────────────────────────────────────

@config_bp.route("/config/produto/<int:pid>/edit", methods=["POST"])
@login_required
def produto_edit(pid: int):
    conn = get_user_conn()
    try:
        nome = request.form["nome"].strip()
        descricao = request.form.get("descricao") or None
        custo = round(float(request.form["preco_custo"].replace(",", ".")) * 100)
        venda = round(float(request.form["preco_venda"].replace(",", ".")) * 100)
        if not nome:
            raise ValidacaoError("Nome é obrigatório.")
        if venda < custo:
            raise ValidacaoError("Preço de venda não pode ser menor que o custo.")
        produto_repo.atualizar(conn, pid, nome=nome, descricao=descricao,
                               preco_custo=custo, preco_venda=venda)
        flash("Produto atualizado.", "success")
    except (ValidacaoError, ValueError) as e:
        flash(str(e), "error")
    return _redir("produtos")


@config_bp.route("/config/produto/<int:pid>/toggle", methods=["POST"])
@login_required
def produto_toggle(pid: int):
    conn = get_user_conn()
    row = produto_repo.obter(conn, pid)
    if row:
        novo = not bool(row.get("ativo", True))
        produto_repo.atualizar(conn, pid, ativo=novo)
        flash("Produto " + ("ativado" if novo else "desativado") + ".", "success")
    return _redir("produtos")


# ── Negócio ───────────────────────────────────────────────────────────────────

@config_bp.route("/config/negocio", methods=["POST"])
@login_required
def negocio_update():
    conn = get_user_conn()
    try:
        nome = request.form.get("nome_negocio", "").strip()
        descricao = request.form.get("descricao_negocio", "").strip()
        tipo = request.form.get("tipo_trabalho") or "ambos"
        formas = request.form.getlist("formas_pagamento")
        horario = request.form.get("horario_trabalho", "").strip()

        if not nome:
            raise ValidacaoError("Nome do negócio é obrigatório.")
        if tipo not in ("servicos", "produtos", "ambos"):
            tipo = "ambos"
        formas_validas = {"PIX", "DINHEIRO", "MAQUININHA"}
        formas = [f for f in formas if f in formas_validas] or ["PIX", "DINHEIRO", "MAQUININHA"]

        config_repo.set_config(conn, "nome_negocio", nome)
        config_repo.set_config(conn, "descricao_negocio", descricao)
        config_repo.set_config(conn, "tipo_trabalho", tipo)
        config_repo.set_config(conn, "formas_pagamento", ",".join(formas))
        config_repo.set_config(conn, "horario_trabalho", horario)
        flash("Perfil do negócio atualizado.", "success")
    except (ValidacaoError, ValueError) as e:
        flash(str(e), "error")
    return _redir("negocio")


# ── Conta (continua em SQLite — autenticação) ─────────────────────────────────

@config_bp.route("/config/conta", methods=["POST"])
@login_required
def conta_update():
    conn = get_connection()
    try:
        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
        if not nome:
            raise ValidacaoError("Nome é obrigatório.")
        if not email or "@" not in email:
            raise ValidacaoError("E-mail inválido.")
        dup = conn.execute(
            "SELECT id FROM usuario WHERE email = ? AND id != ?",
            (email, current_user.id),
        ).fetchone()
        if dup:
            raise ValidacaoError("E-mail já cadastrado em outra conta.")
        conn.execute(
            "UPDATE usuario SET nome = ?, email = ? WHERE id = ?",
            (nome, email, current_user.id),
        )
        current_user.nome = nome
        current_user.email = email
        flash("Dados atualizados.", "success")
    except (ValidacaoError, ValueError) as e:
        flash(str(e), "error")
    finally:
        conn.close()
    return _redir("conta")


@config_bp.route("/config/senha", methods=["POST"])
@login_required
def conta_senha():
    conn = get_connection()
    try:
        senha_atual = request.form["senha_atual"]
        nova = request.form["nova_senha"]
        confirmar = request.form["confirmar_senha"]
        row = conn.execute(
            "SELECT senha_hash FROM usuario WHERE id = ?", (current_user.id,)
        ).fetchone()
        if not check_password_hash(row["senha_hash"], senha_atual):
            raise ValidacaoError("Senha atual incorreta.")
        if nova != confirmar:
            raise ValidacaoError("As senhas não coincidem.")
        if len(nova) < 6:
            raise ValidacaoError("Senha deve ter ao menos 6 caracteres.")
        conn.execute(
            "UPDATE usuario SET senha_hash = ? WHERE id = ?",
            (generate_password_hash(nova), current_user.id),
        )
        flash("Senha alterada com sucesso.", "success")
    except (ValidacaoError, ValueError) as e:
        flash(str(e), "error")
    finally:
        conn.close()
    return _redir("conta")
