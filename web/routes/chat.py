"""Interface conversacional — Claude API com tool-calling."""

from __future__ import annotations

import json
import os
from datetime import date, timedelta

import anthropic
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.repositories.sql import categoria_repo, movimentacao_repo, produto_repo, servico_repo
from app.services import despesa_service, estoque_service, receita_service
from app.utils.validators import ValidacaoError
from web.extensions import limiter
from web.models import get_user_conn

chat_bp = Blueprint("chat", __name__)

_TOOLS = [
    {
        "name": "listar_servicos",
        "description": "Lista todos os serviços ativos da barbearia com ID, nome e preço padrão em centavos.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "listar_categorias_despesa",
        "description": "Lista todas as categorias de despesa ativas com ID e nome.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "listar_produtos",
        "description": "Lista todos os produtos em estoque com ID, nome, preço de venda e quantidade disponível.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "registrar_atendimento",
        "description": (
            "Registra um atendimento/serviço prestado ao cliente. "
            "Use listar_servicos primeiro para obter o ID correto do serviço."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "servico_id": {
                    "type": "integer",
                    "description": "ID do serviço (obter via listar_servicos)",
                },
                "valor_centavos": {
                    "type": "integer",
                    "description": "Valor cobrado em centavos (ex: R$35,00 = 3500)",
                },
                "forma_pagamento": {
                    "type": "string",
                    "enum": ["PIX", "DINHEIRO", "MAQUININHA"],
                },
                "data": {
                    "type": "string",
                    "description": "Data no formato YYYY-MM-DD. Omitir para usar hoje.",
                },
                "observacao": {"type": "string", "description": "Observação opcional"},
            },
            "required": ["servico_id", "valor_centavos", "forma_pagamento"],
        },
    },
    {
        "name": "registrar_despesa",
        "description": (
            "Registra uma despesa (aluguel, insumos, salário, etc.). "
            "Use listar_categorias_despesa para obter o ID da categoria."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "categoria_id": {
                    "type": "integer",
                    "description": "ID da categoria de despesa",
                },
                "descricao": {"type": "string", "description": "Descrição da despesa"},
                "valor_centavos": {
                    "type": "integer",
                    "description": "Valor em centavos",
                },
                "forma_pagamento": {
                    "type": "string",
                    "enum": ["PIX", "DINHEIRO", "MAQUININHA"],
                },
                "data": {
                    "type": "string",
                    "description": "Data no formato YYYY-MM-DD. Omitir para usar hoje.",
                },
            },
            "required": ["categoria_id", "descricao", "valor_centavos", "forma_pagamento"],
        },
    },
    {
        "name": "registrar_venda_produto",
        "description": (
            "Registra a venda de um produto do estoque. "
            "Use listar_produtos para obter o ID correto. "
            "Sempre pergunte o nome do cliente se não for informado."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "produto_id": {
                    "type": "integer",
                    "description": "ID do produto (obter via listar_produtos)",
                },
                "quantidade": {"type": "integer", "description": "Quantidade vendida"},
                "preco_venda_unitario": {
                    "type": "integer",
                    "description": "Preço de venda unitário em centavos",
                },
                "cliente": {
                    "type": "string",
                    "description": "Nome do cliente que comprou (importante para o relatório do dia)",
                },
                "data": {
                    "type": "string",
                    "description": "Data no formato YYYY-MM-DD. Omitir para usar hoje.",
                },
            },
            "required": ["produto_id", "quantidade", "preco_venda_unitario"],
        },
    },
    {
        "name": "gerar_relatorio_vendas",
        "description": (
            "Gera um relatório de vendas de produtos formatado e pronto para copiar e enviar via WhatsApp. "
            "Use para fechamento do dia ou consulta de qualquer período."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "Data específica no formato YYYY-MM-DD. Omitir para usar hoje.",
                },
                "periodo": {
                    "type": "string",
                    "enum": ["hoje", "semana", "mes"],
                    "description": "Período alternativo. Ignorado se 'data' for informada.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "consultar_dashboard",
        "description": "Retorna o resumo financeiro (receitas, despesas, saldo) para um período.",
        "input_schema": {
            "type": "object",
            "properties": {
                "periodo": {
                    "type": "string",
                    "enum": ["hoje", "semana", "mes", "mes_anterior"],
                    "description": "Período para consulta",
                }
            },
            "required": ["periodo"],
        },
    },
]


def _build_system_prompt() -> str:
    from app.repositories.sql import config_repo

    conn = get_user_conn()
    nome_negocio = config_repo.get_config(conn, "nome_negocio") or "seu negócio"
    descricao = config_repo.get_config(conn, "descricao_negocio") or ""
    tipo = config_repo.get_config(conn, "tipo_trabalho") or "ambos"
    formas_raw = config_repo.get_config(conn, "formas_pagamento") or "PIX,DINHEIRO,MAQUININHA"
    horario = config_repo.get_config(conn, "horario_trabalho") or ""

    formas_lista = formas_raw.split(",")
    formas_str = ", ".join(formas_lista)

    contexto_negocio = f"Negócio: {nome_negocio}."
    if descricao:
        contexto_negocio += f" {descricao}"
    if horario:
        contexto_negocio += f" Horário: {horario}."

    if tipo == "servicos":
        foco = "O negócio trabalha com serviços (não com produtos físicos no estoque)."
    elif tipo == "produtos":
        foco = "O negócio trabalha com venda de produtos. Não há serviços avulsos."
    else:
        foco = "O negócio trabalha com serviços e venda de produtos."

    return (
        f"Você é o assistente financeiro de {nome_negocio}. "
        f"Seu trabalho é registrar vendas, despesas e serviços de forma conversacional — rápida e sem atrito.\n\n"
        f"Contexto do negócio: {contexto_negocio}\n"
        f"{foco}\n"
        f"Formas de pagamento aceitas: {formas_str}.\n"
        f"Data de hoje: {date.today().isoformat()}\n\n"
        "Comportamento:\n"
        "- Seja conciso. O usuário está ocupado.\n"
        "- Ao registrar uma venda de produto, sempre pergunte o nome do cliente se não foi informado — é essencial para o relatório do dia.\n"
        "- Após registrar, confirme com resumo: \"✓ [produto/serviço] — R$[valor] — [cliente se houver]\"\n"
        "- Se o usuário mencionar produto pelo nome, use listar_produtos para achar o ID antes de registrar.\n"
        "- Se o usuário mencionar serviço pelo nome, use listar_servicos para achar o ID antes de registrar.\n"
        "- Interprete valores sempre em Reais (\"150 pix\" = R$150,00 = 15000 centavos).\n"
        "- Para \"quanto vendi hoje?\", \"resumo do dia\" ou similar, use consultar_dashboard.\n"
        "- Para \"relatório do dia\", \"lista de vendas\", \"o que vendi hoje\" → use gerar_relatorio_vendas. "
        "O relatório retornado já está formatado — reproduza-o exatamente, sem reformatar.\n"
        "- Se faltar dado essencial, peça apenas o que falta — sem perguntas longas.\n"
        "- Nunca invente IDs — sempre busque via listar_servicos, listar_categorias_despesa ou listar_produtos.\n"
        "- Formato de valores na resposta: sempre \"R$XX,XX\" com vírgula decimal.\n"
        f"- Só sugira formas de pagamento que o negócio aceita: {formas_str}."
    )


def _execute_tool(name: str, inputs: dict) -> dict:
    conn = get_user_conn()
    try:
        if name == "listar_servicos":
            rows = servico_repo.listar_ativos(conn)
            return {"servicos": [{"id": r["id"], "nome": r["nome"], "preco_padrao": r["preco_padrao"]} for r in rows]}

        if name == "listar_categorias_despesa":
            rows = categoria_repo.listar_ativas(conn)
            return {"categorias": [{"id": r["id"], "nome": r["nome"]} for r in rows]}

        if name == "listar_produtos":
            rows = produto_repo.listar_ativos(conn)
            return {
                "produtos": [
                    {
                        "id": r["id"],
                        "nome": r["nome"],
                        "preco_venda": r["preco_venda"],
                        "quantidade_estoque": r["quantidade_estoque"],
                    }
                    for r in rows
                ]
            }

        if name == "registrar_atendimento":
            data_obj = date.fromisoformat(inputs["data"]) if inputs.get("data") else date.today()
            receita_id = receita_service.registrar_atendimento_avulso(
                conn,
                servico_id=inputs["servico_id"],
                valor_centavos=inputs["valor_centavos"],
                forma_pagamento=inputs["forma_pagamento"],
                data_atendimento=data_obj,
                observacao=inputs.get("observacao"),
            )
            return {"ok": True, "receita_id": receita_id}

        if name == "registrar_despesa":
            data_obj = date.fromisoformat(inputs["data"]) if inputs.get("data") else date.today()
            despesa_id = despesa_service.registrar_despesa(
                conn,
                categoria_id=inputs["categoria_id"],
                descricao=inputs["descricao"],
                valor_centavos=inputs["valor_centavos"],
                forma_pagamento=inputs["forma_pagamento"],
                data_despesa=data_obj,
            )
            return {"ok": True, "despesa_id": despesa_id}

        if name == "registrar_venda_produto":
            data_obj = date.fromisoformat(inputs["data"]) if inputs.get("data") else date.today()
            mov_id = estoque_service.registrar_venda(
                conn,
                produto_id=inputs["produto_id"],
                quantidade=inputs["quantidade"],
                preco_venda_unitario=inputs["preco_venda_unitario"],
                data_venda=data_obj,
                observacao=inputs.get("cliente"),
            )
            return {"ok": True, "movimentacao_id": mov_id}

        if name == "gerar_relatorio_vendas":
            today = date.today()
            data_str = inputs.get("data")
            periodo = inputs.get("periodo", "hoje")

            if data_str:
                de = ate = date.fromisoformat(data_str)
            elif periodo == "semana":
                de = today - timedelta(days=today.weekday())
                ate = today
            elif periodo == "mes":
                de = today.replace(day=1)
                ate = today
            else:
                de = ate = today

            movs = movimentacao_repo.listar_periodo(conn, de, ate, tipo="VENDA")

            label = (
                de.strftime("%d/%m/%Y")
                if de == ate
                else f"{de.strftime('%d/%m/%Y')} a {ate.strftime('%d/%m/%Y')}"
            )

            if not movs:
                return {"relatorio": f"Nenhuma venda registrada em {label}."}

            linhas = [f"Vendas de {label}\n"]
            total = 0
            for m in movs:
                qtd = abs(m["quantidade"])
                qtd_str = f" ×{qtd}" if qtd > 1 else ""
                cliente_str = f" — {m['observacao']}" if m.get("observacao") else ""
                valor_str = f"R${m['total_centavos'] / 100:.2f}".replace(".", ",")
                linhas.append(f"• {m['produto_nome']}{qtd_str} — {valor_str}{cliente_str}")
                total += m["total_centavos"]

            total_str = f"R${total / 100:.2f}".replace(".", ",")
            linhas.append(f"\nTotal: {total_str} | {len(movs)} venda(s)")
            return {"relatorio": "\n".join(linhas)}

        if name == "consultar_dashboard":
            today = date.today()
            periodo = inputs["periodo"]
            if periodo == "hoje":
                de, ate = today, today
            elif periodo == "semana":
                de = today - timedelta(days=today.weekday())
                ate = today
            elif periodo == "mes":
                de = today.replace(day=1)
                ate = today
            else:  # mes_anterior
                primeiro_atual = today.replace(day=1)
                ate = primeiro_atual - timedelta(days=1)
                de = ate.replace(day=1)

            rec = receita_service.totais_periodo(conn, de, ate)
            desp = despesa_service.totais_periodo(conn, de, ate)
            saldo = rec["total_centavos"] - desp["total_centavos"]
            return {
                "periodo": {"de": de.isoformat(), "ate": ate.isoformat()},
                "receitas_centavos": rec["total_centavos"],
                "receitas_reais": rec["total_centavos"] / 100,
                "qtd_atendimentos": rec["qtd_atendimentos"],
                "despesas_centavos": desp["total_centavos"],
                "despesas_reais": desp["total_centavos"] / 100,
                "saldo_centavos": saldo,
                "saldo_reais": saldo / 100,
            }

        return {"error": f"Ferramenta '{name}' não reconhecida"}

    except ValidacaoError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Erro interno: {e}"}


def _run_agentic_loop(messages: list[dict]) -> str:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    for _ in range(10):  # máximo de 10 iterações para evitar loops infinitos
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=_build_system_prompt(),
            tools=_TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text_blocks = [b for b in response.content if b.type == "text"]
            return text_blocks[0].text if text_blocks else "(sem resposta)"

        if response.stop_reason == "tool_use":
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            # Adiciona resposta do assistente (com tool_use) ao histórico
            assistant_content = []
            for b in response.content:
                if b.type == "text":
                    assistant_content.append({"type": "text", "text": b.text})
                elif b.type == "tool_use":
                    assistant_content.append(
                        {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input}
                    )
            messages.append({"role": "assistant", "content": assistant_content})

            # Executa cada ferramenta e acumula resultados
            tool_results = []
            for block in tool_use_blocks:
                result = _execute_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False),
                        "is_error": "error" in result,
                    }
                )

            messages.append({"role": "user", "content": tool_results})
            continue

        break  # stop_reason inesperado

    return "Não consegui processar sua solicitação. Tente novamente."


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------


@chat_bp.route("/chat")
@login_required
def index():
    # Verifica assinatura no Stripe se a última checagem foi há mais de 12h
    if current_user.is_pro:
        from web.routes.billing import verificar_plano_stripe
        if verificar_plano_stripe(current_user):
            flash("Sua assinatura Pro foi cancelada. Renove para continuar.", "info")
            return redirect(url_for("billing.upgrade"))

    if not current_user.is_pro:
        flash("O assistente de IA é exclusivo do plano Pro.", "info")
        return redirect(url_for("lancamento.index"))
    return render_template("chat.html")


@chat_bp.route("/api/chat", methods=["POST"])
@login_required
@limiter.limit("30 per minute", key_func=lambda: str(current_user.id))
def api_chat():
    if not current_user.is_pro:
        return jsonify({"error": "Recurso exclusivo do plano Pro."}), 403
    payload = request.get_json(silent=True) or {}
    user_message = (payload.get("message") or "").strip()[:2000]
    history = (payload.get("history") or [])[-20:]

    if not user_message:
        return jsonify({"error": "Mensagem vazia"}), 400

    # Monta mensagens para a API: histórico + nova mensagem do usuário
    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_message})

    try:
        response_text = _run_agentic_loop(messages)
    except anthropic.APIStatusError as e:
        return jsonify({"error": f"Erro na API Claude: {e.status_code}"}), 502
    except Exception as e:
        return jsonify({"error": f"Erro interno: {e}"}), 500

    return jsonify({"response": response_text})
