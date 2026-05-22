#!/usr/bin/env python
"""Flux Barber CLI — lançamentos, consultas e configuração rápida.

Uso básico:
    python cli.py dashboard
    python cli.py servicos
    python cli.py lancar atendimento 1 35.00 PIX
    python cli.py --json estoque

Flag global --json/-j emite JSON puro (útil para integração com agentes de IA).
"""

from __future__ import annotations

import json
from datetime import date
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from app.repositories.db import get_connection
from app.repositories import (
    categoria_repo,
    despesa_repo,
    movimentacao_repo,
    produto_repo,
    receita_repo,
    servico_repo,
)
from app.services import despesa_service, estoque_service, receita_service
from app.utils.validators import ValidacaoError

# ── App e sub-app ─────────────────────────────────────────────────────────────

app = typer.Typer(
    help="Flux Barber CLI — gestão financeira da barbearia.",
    no_args_is_help=True,
)
lancar_app = typer.Typer(
    help="Registrar lançamentos: atendimento, despesa, compra, venda.",
    no_args_is_help=True,
)
app.add_typer(lancar_app, name="lancar")

console = Console()
err_console = Console(stderr=True)
_state: dict = {"json": False}


@app.callback()
def _global(
    json_mode: Annotated[
        bool, typer.Option("--json", "-j", help="Saída em JSON (para integrações).")
    ] = False,
) -> None:
    _state["json"] = json_mode


# ── Helpers ───────────────────────────────────────────────────────────────────

def _emit(data: object) -> None:
    """Emite JSON quando --json está ativo."""
    if _state["json"]:
        typer.echo(json.dumps(data, ensure_ascii=False, default=str))


def _brl(centavos: int) -> str:
    return f"R$ {centavos / 100:,.2f}"


def _err(msg: str) -> None:
    if _state["json"]:
        _emit({"ok": False, "error": msg})
    else:
        err_console.print(f"[red]Erro:[/red] {msg}")
    raise typer.Exit(1)


# ── dashboard ─────────────────────────────────────────────────────────────────

@app.command()
def dashboard() -> None:
    """KPIs do dia e do mês atual."""
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    conn = get_connection()
    rec_hoje, qtd_hoje = receita_repo.total_periodo(conn, hoje, hoje)
    desp_hoje, _ = despesa_repo.total_periodo(conn, hoje, hoje)
    rec_mes, qtd_mes = receita_repo.total_periodo(conn, inicio_mes, hoje)
    desp_mes, _ = despesa_repo.total_periodo(conn, inicio_mes, hoje)
    est_hoje = movimentacao_repo.totais_periodo(conn, hoje, hoje)
    est_mes = movimentacao_repo.totais_periodo(conn, inicio_mes, hoje)
    conn.close()

    data = {
        "data": hoje.isoformat(),
        "hoje": {
            "receita_servicos": rec_hoje,
            "despesa": desp_hoje,
            "resultado": rec_hoje - desp_hoje,
            "atendimentos": qtd_hoje,
            "vendas_produtos": est_hoje["VENDA"]["total"],
        },
        "mes": {
            "receita_servicos": rec_mes,
            "despesa": desp_mes,
            "resultado": rec_mes - desp_mes,
            "atendimentos": qtd_mes,
            "vendas_produtos": est_mes["VENDA"]["total"],
            "margem_estoque": est_mes["VENDA"]["total"] - est_mes["COMPRA"]["total"],
        },
    }

    if _state["json"]:
        _emit(data)
        return

    t = Table(title=f"Dashboard — {hoje.strftime('%d/%m/%Y')}", show_lines=False)
    t.add_column("", style="bold white")
    t.add_column("Receita serviços", justify="right", style="green")
    t.add_column("Despesa", justify="right", style="red")
    t.add_column("Resultado", justify="right")
    t.add_column("Atend.", justify="right", style="cyan")
    t.add_column("Vendas produtos", justify="right", style="blue")

    for label, d in [("Hoje", data["hoje"]), ("Mês", data["mes"])]:
        res = d["resultado"]
        res_str = f"[green]{_brl(res)}[/green]" if res >= 0 else f"[red]{_brl(res)}[/red]"
        t.add_row(
            label,
            _brl(d["receita_servicos"]),
            _brl(d["despesa"]),
            res_str,
            str(d["atendimentos"]),
            _brl(d["vendas_produtos"]),
        )
    console.print(t)


# ── receitas ──────────────────────────────────────────────────────────────────

@app.command()
def receitas(
    de: Annotated[Optional[str], typer.Option("--de", help="Data inicial YYYY-MM-DD.")] = None,
    ate: Annotated[Optional[str], typer.Option("--ate", help="Data final YYYY-MM-DD.")] = None,
    limite: Annotated[int, typer.Option("--limite", "-n", help="Máx. linhas.")] = 20,
) -> None:
    """Listar receitas do período."""
    hoje = date.today()
    d_ini = date.fromisoformat(de) if de else hoje.replace(day=1)
    d_fim = date.fromisoformat(ate) if ate else hoje
    conn = get_connection()
    rows = conn.execute(
        """SELECT r.id, r.data, s.nome AS servico, r.valor_centavos,
                  r.forma_pagamento, r.observacao
             FROM receita r JOIN servico s ON s.id = r.servico_id
            WHERE r.data BETWEEN ? AND ?
            ORDER BY r.data DESC, r.id DESC LIMIT ?""",
        (d_ini.isoformat(), d_fim.isoformat(), limite),
    ).fetchall()
    conn.close()

    data = [dict(r) for r in rows]
    if _state["json"]:
        _emit(data)
        return

    t = Table(title=f"Receitas {d_ini} → {d_fim} (últimas {len(data)})")
    t.add_column("ID", style="dim", justify="right")
    t.add_column("Data", style="dim")
    t.add_column("Serviço")
    t.add_column("Valor", justify="right", style="green")
    t.add_column("Forma", style="cyan")
    t.add_column("Obs", style="dim")
    for r in data:
        t.add_row(str(r["id"]), r["data"], r["servico"],
                  _brl(r["valor_centavos"]), r["forma_pagamento"], r["observacao"] or "")
    console.print(t)


# ── despesas ──────────────────────────────────────────────────────────────────

@app.command()
def despesas(
    de: Annotated[Optional[str], typer.Option("--de")] = None,
    ate: Annotated[Optional[str], typer.Option("--ate")] = None,
    limite: Annotated[int, typer.Option("--limite", "-n")] = 20,
) -> None:
    """Listar despesas do período."""
    hoje = date.today()
    d_ini = date.fromisoformat(de) if de else hoje.replace(day=1)
    d_fim = date.fromisoformat(ate) if ate else hoje
    conn = get_connection()
    rows = conn.execute(
        """SELECT d.id, d.data, c.nome AS categoria, d.descricao,
                  d.valor_centavos, d.forma_pagamento
             FROM despesa d JOIN categoria_despesa c ON c.id = d.categoria_id
            WHERE d.data BETWEEN ? AND ?
            ORDER BY d.data DESC, d.id DESC LIMIT ?""",
        (d_ini.isoformat(), d_fim.isoformat(), limite),
    ).fetchall()
    conn.close()

    data = [dict(r) for r in rows]
    if _state["json"]:
        _emit(data)
        return

    t = Table(title=f"Despesas {d_ini} → {d_fim} (últimas {len(data)})")
    t.add_column("ID", style="dim", justify="right")
    t.add_column("Data", style="dim")
    t.add_column("Categoria")
    t.add_column("Descrição")
    t.add_column("Valor", justify="right", style="red")
    t.add_column("Forma", style="cyan")
    for r in data:
        t.add_row(str(r["id"]), r["data"], r["categoria"],
                  r["descricao"], _brl(r["valor_centavos"]), r["forma_pagamento"])
    console.print(t)


# ── estoque ───────────────────────────────────────────────────────────────────

@app.command()
def estoque(
    todos: Annotated[bool, typer.Option("--todos", help="Incluir inativos.")] = False,
) -> None:
    """Listar produtos e quantidades em estoque."""
    conn = get_connection()
    produtos = produto_repo.listar_todos(conn) if todos else produto_repo.listar_ativos(conn)
    conn.close()

    data = [dict(p) for p in produtos]
    if _state["json"]:
        _emit(data)
        return

    t = Table(title="Estoque")
    t.add_column("ID", style="dim", justify="right")
    t.add_column("Produto")
    t.add_column("Custo", justify="right")
    t.add_column("Venda", justify="right", style="green")
    t.add_column("Qtd", justify="right")
    t.add_column("Status", justify="center")
    for p in data:
        qtd = p["quantidade_estoque"]
        qtd_str = (
            f"[red]{qtd}[/red]" if qtd <= 2
            else f"[yellow]{qtd}[/yellow]" if qtd <= 5
            else str(qtd)
        )
        status = "[green]Ativo[/green]" if p["ativo"] else "[dim]Inativo[/dim]"
        t.add_row(str(p["id"]), p["nome"],
                  _brl(p["preco_custo"]), _brl(p["preco_venda"]),
                  qtd_str, status)
    console.print(t)


# ── servicos ──────────────────────────────────────────────────────────────────

@app.command()
def servicos(
    todos: Annotated[bool, typer.Option("--todos")] = False,
) -> None:
    """Listar serviços do catálogo."""
    conn = get_connection()
    rows = servico_repo.listar_todos(conn) if todos else servico_repo.listar_ativos(conn)
    conn.close()

    data = [dict(r) for r in rows]
    if _state["json"]:
        _emit(data)
        return

    t = Table(title="Serviços")
    t.add_column("ID", style="dim", justify="right")
    t.add_column("Nome")
    t.add_column("Categoria", style="dim")
    t.add_column("Preço", justify="right", style="green")
    t.add_column("Ord.", justify="right")
    t.add_column("Status", justify="center")
    for s in data:
        status = "[green]Ativo[/green]" if s["ativo"] else "[dim]Inativo[/dim]"
        t.add_row(str(s["id"]), s["nome"],
                  s["categoria_servico"] or "—", _brl(s["preco_padrao"]),
                  str(s["ordem"]), status)
    console.print(t)


# ── categorias ────────────────────────────────────────────────────────────────

@app.command()
def categorias() -> None:
    """Listar categorias de despesa."""
    conn = get_connection()
    rows = categoria_repo.listar_todas(conn)
    conn.close()

    data = [dict(r) for r in rows]
    if _state["json"]:
        _emit(data)
        return

    t = Table(title="Categorias de Despesa")
    t.add_column("ID", style="dim", justify="right")
    t.add_column("Ícone", justify="center")
    t.add_column("Nome")
    t.add_column("Status", justify="center")
    for c in data:
        status = "[green]Ativa[/green]" if c["ativo"] else "[dim]Inativa[/dim]"
        t.add_row(str(c["id"]), c["icone"] or "📦", c["nome"], status)
    console.print(t)


# ── lancar atendimento ────────────────────────────────────────────────────────

@lancar_app.command("atendimento")
def lancar_atendimento(
    servico_id: Annotated[int, typer.Argument(help="ID do serviço.")],
    valor: Annotated[float, typer.Argument(help="Valor em R$ (ex: 35.00).")],
    forma: Annotated[str, typer.Argument(help="PIX | DINHEIRO | MAQUININHA.")],
    data: Annotated[Optional[str], typer.Option("--data", "-d", help="YYYY-MM-DD (padrão: hoje).")] = None,
    obs: Annotated[Optional[str], typer.Option("--obs", "-o", help="Observação.")] = None,
) -> None:
    """Registrar atendimento (receita de serviço)."""
    conn = get_connection()
    try:
        data_obj = date.fromisoformat(data) if data else date.today()
        mov_id = receita_service.registrar_atendimento_avulso(
            conn,
            servico_id=servico_id,
            valor_centavos=round(valor * 100),
            forma_pagamento=forma.upper(),
            data_atendimento=data_obj,
            observacao=obs,
        )
        result = {
            "ok": True, "id": mov_id,
            "servico_id": servico_id,
            "valor_centavos": round(valor * 100),
            "data": data_obj.isoformat(),
        }
        if _state["json"]:
            _emit(result)
        else:
            console.print(f"[green]OK[/green] Atendimento registrado — id={mov_id}  {_brl(round(valor * 100))}")
    except (ValidacaoError, ValueError) as e:
        _err(str(e))
    finally:
        conn.close()


# ── lancar despesa ────────────────────────────────────────────────────────────

@lancar_app.command("despesa")
def lancar_despesa(
    categoria_id: Annotated[int, typer.Argument(help="ID da categoria (ver: categorias).")],
    descricao: Annotated[str, typer.Argument(help="Descrição da despesa.")],
    valor: Annotated[float, typer.Argument(help="Valor em R$.")],
    forma: Annotated[str, typer.Argument(help="PIX | DINHEIRO | MAQUININHA.")],
    data: Annotated[Optional[str], typer.Option("--data", "-d")] = None,
    obs: Annotated[Optional[str], typer.Option("--obs", "-o", hidden=True)] = None,
) -> None:
    """Registrar despesa."""
    conn = get_connection()
    try:
        data_obj = date.fromisoformat(data) if data else date.today()
        desp_id = despesa_service.registrar_despesa(
            conn,
            categoria_id=categoria_id,
            descricao=descricao,
            valor_centavos=round(valor * 100),
            forma_pagamento=forma.upper(),
            data_despesa=data_obj,
        )
        result = {
            "ok": True, "id": desp_id,
            "categoria_id": categoria_id,
            "valor_centavos": round(valor * 100),
            "data": data_obj.isoformat(),
        }
        if _state["json"]:
            _emit(result)
        else:
            console.print(f"[green]OK[/green] Despesa registrada — id={desp_id}  {_brl(round(valor * 100))}")
    except (ValidacaoError, ValueError) as e:
        _err(str(e))
    finally:
        conn.close()


# ── lancar compra ─────────────────────────────────────────────────────────────

@lancar_app.command("compra")
def lancar_compra(
    produto_id: Annotated[int, typer.Argument(help="ID do produto (ver: estoque --todos).")],
    quantidade: Annotated[int, typer.Argument(help="Quantidade comprada.")],
    preco_custo: Annotated[float, typer.Argument(help="Preço de custo unitário em R$.")],
    data: Annotated[Optional[str], typer.Option("--data", "-d")] = None,
    obs: Annotated[Optional[str], typer.Option("--obs", "-o")] = None,
) -> None:
    """Registrar entrada de estoque (compra de produto)."""
    conn = get_connection()
    try:
        data_obj = date.fromisoformat(data) if data else date.today()
        mov_id = estoque_service.registrar_compra(
            conn,
            produto_id=produto_id,
            quantidade=quantidade,
            preco_custo_unitario=round(preco_custo * 100),
            data_compra=data_obj,
            observacao=obs,
        )
        result = {
            "ok": True, "id": mov_id,
            "produto_id": produto_id,
            "quantidade": quantidade,
            "data": data_obj.isoformat(),
        }
        if _state["json"]:
            _emit(result)
        else:
            console.print(
                f"[green]OK[/green] Compra registrada — id={mov_id}  "
                f"{quantidade} unid. × {_brl(round(preco_custo * 100))}"
            )
    except (ValidacaoError, ValueError) as e:
        _err(str(e))
    finally:
        conn.close()


# ── lancar venda ──────────────────────────────────────────────────────────────

@lancar_app.command("venda")
def lancar_venda(
    produto_id: Annotated[int, typer.Argument(help="ID do produto.")],
    quantidade: Annotated[int, typer.Argument(help="Quantidade vendida.")],
    preco_venda: Annotated[float, typer.Argument(help="Preço de venda unitário em R$.")],
    data: Annotated[Optional[str], typer.Option("--data", "-d")] = None,
    obs: Annotated[Optional[str], typer.Option("--obs", "-o")] = None,
) -> None:
    """Registrar saída de estoque (venda de produto)."""
    conn = get_connection()
    try:
        data_obj = date.fromisoformat(data) if data else date.today()
        mov_id = estoque_service.registrar_venda(
            conn,
            produto_id=produto_id,
            quantidade=quantidade,
            preco_venda_unitario=round(preco_venda * 100),
            data_venda=data_obj,
            observacao=obs,
        )
        result = {
            "ok": True, "id": mov_id,
            "produto_id": produto_id,
            "quantidade": quantidade,
            "data": data_obj.isoformat(),
        }
        if _state["json"]:
            _emit(result)
        else:
            console.print(
                f"[green]OK[/green] Venda registrada — id={mov_id}  "
                f"{quantidade} unid. × {_brl(round(preco_venda * 100))}"
            )
    except (ValidacaoError, ValueError) as e:
        _err(str(e))
    finally:
        conn.close()


if __name__ == "__main__":
    app()
