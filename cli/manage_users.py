"""CLI para gerenciar usuários — liberar/revogar acesso ao plano Pro (chat IA)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from app.repositories.db import get_connection

cli = typer.Typer(help="Gerenciamento de usuários — Flux Barber")
console = Console()


def _get_usuario(conn, user_id: int):
    return conn.execute(
        "SELECT id, nome, email, plano, criado_em FROM usuario WHERE id = ?", (user_id,)
    ).fetchone()


@cli.command()
def criar(
    email: str = typer.Option(..., prompt=True, help="E-mail do novo usuário"),
    nome: str = typer.Option(..., prompt=True, help="Nome do usuário"),
    senha: str = typer.Option(..., prompt=True, hide_input=True, help="Senha"),
    pro: bool = typer.Option(False, "--pro/--free", help="Criar já com plano Pro"),
):
    """Cria um novo usuário diretamente no banco de autenticação."""
    import uuid as _uuid
    from werkzeug.security import generate_password_hash

    email = email.lower().strip()
    conn = get_connection()
    existing = conn.execute("SELECT id, plano FROM usuario WHERE email = ?", (email,)).fetchone()
    if existing:
        rprint(f"[yellow]Usuário {email} já existe (id={existing['id']}, plano={existing['plano']}).[/yellow]")
        if pro and existing["plano"] != "pro":
            conn.execute("UPDATE usuario SET plano = 'pro' WHERE email = ?", (email,))
            rprint(f"[bold green]Plano Pro ativado para {email}.[/bold green]")
        conn.close()
        return

    device_id = _uuid.uuid4().hex
    plano = "pro" if pro else "free"
    conn.execute(
        "INSERT INTO usuario (email, nome, senha_hash, device_id, plano) VALUES (?, ?, ?, ?, ?)",
        (email, nome.strip(), generate_password_hash(senha), device_id, plano),
    )
    conn.close()
    rprint(f"[bold green]Usuário criado: {nome} ({email}) — plano {plano.upper()}[/bold green]")


@cli.command()
def listar():
    """Lista todos os usuários cadastrados."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, nome, email, plano, criado_em FROM usuario ORDER BY id"
    ).fetchall()
    conn.close()

    if not rows:
        rprint("[yellow]Nenhum usuário cadastrado.[/yellow]")
        return

    table = Table(title="Usuários — Flux Barber", show_lines=True)
    table.add_column("ID", style="dim", justify="right", width=5)
    table.add_column("Nome", min_width=20)
    table.add_column("E-mail", min_width=25)
    table.add_column("Plano", justify="center", width=8)
    table.add_column("Criado em", style="dim", width=20)

    for r in rows:
        plano_str = "[bold green]PRO[/bold green]" if r["plano"] == "pro" else "[dim]free[/dim]"
        table.add_row(str(r["id"]), r["nome"], r["email"], plano_str, r["criado_em"] or "—")

    console.print(table)


@cli.command()
def promover(user_id: int = typer.Argument(..., help="ID do usuário a promover para Pro")):
    """Promove um usuário para o plano Pro (libera acesso ao chat IA)."""
    conn = get_connection()
    row = _get_usuario(conn, user_id)
    if not row:
        rprint(f"[red]Usuário #{user_id} não encontrado.[/red]")
        conn.close()
        raise typer.Exit(1)

    if row["plano"] == "pro":
        rprint(f"[yellow]{row['nome']} ({row['email']}) já é Pro.[/yellow]")
        conn.close()
        return

    conn.execute("UPDATE usuario SET plano = 'pro' WHERE id = ?", (user_id,))
    conn.close()
    rprint(f"[bold green]OK {row['nome']} ({row['email']}) - Plano Pro ativado.[/bold green]")


@cli.command()
def rebaixar(user_id: int = typer.Argument(..., help="ID do usuário a remover do Pro")):
    """Remove o acesso Pro de um usuário (revoga acesso ao chat IA)."""
    conn = get_connection()
    row = _get_usuario(conn, user_id)
    if not row:
        rprint(f"[red]Usuário #{user_id} não encontrado.[/red]")
        conn.close()
        raise typer.Exit(1)

    if row["plano"] == "free":
        rprint(f"[yellow]{row['nome']} ({row['email']}) já é Free.[/yellow]")
        conn.close()
        return

    conn.execute("UPDATE usuario SET plano = 'free' WHERE id = ?", (user_id,))
    conn.close()
    rprint(f"[bold yellow]OK {row['nome']} ({row['email']}) - Plano Free.[/bold yellow]")


if __name__ == "__main__":
    cli()
