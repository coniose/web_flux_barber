"""CLI de governança — Fluxo Barber.

Permite administrar o catálogo (serviços, categorias, itens frequentes)
e exportar dados, sem depender da interface gráfica. A proposta é
oferecer governance 100% via terminal: o dono cadastra um serviço novo
ou ajusta um item frequente com um comando, e o app reflete.

Uso geral::

    python -m tools.admin_cli <comando> <subcomando> [opções]

Comandos:

  servico       listar | adicionar | renomear | preco | arquivar | reativar | ordem
  categoria     listar | adicionar | renomear | arquivar | reativar
  item          listar | adicionar | renomear | preco | recategorizar | arquivar | reativar
  config        meta-mensal get | set
  export        xlsx --de YYYY-MM-DD --ate YYYY-MM-DD [--saida arquivo.xlsx]
  info          contagens das tabelas principais

Todos os subcomandos aceitam ``--db CAMINHO.db`` para apontar para um banco
específico. Sem isso, usa o caminho padrão do app (``FLUXO_BARBER_DB`` se
definido, ou %APPDATA%/FluxoBarber/fluxo_barber.db no Windows).

O uso de subparsers mantém a ajuda contextual::

    python -m tools.admin_cli servico adicionar --help
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from app.repositories import (
    categoria_repo,
    db as db_module,
    item_frequente_repo,
    servico_repo,
)
from app.services import configuracao_service, export_service
from app.utils.formato import formatar_moeda, reais_para_centavos
from app.utils.validators import ValidacaoError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _conn(args: argparse.Namespace) -> sqlite3.Connection:
    path: Optional[Path] = Path(args.db).expanduser().resolve() if args.db else None
    if path and not path.exists():
        print(f"AVISO: DB não existe ainda em {path}. Será criado.", file=sys.stderr)
    return db_module.ensure_db(path, seed=True)


def _parse_reais(txt: str) -> int:
    try:
        return reais_para_centavos(txt)
    except ValueError as e:
        raise SystemExit(f"Valor inválido: {txt!r} ({e})")


def _parse_data(txt: str) -> date:
    try:
        return datetime.strptime(txt, "%Y-%m-%d").date()
    except ValueError:
        raise SystemExit(f"Data inválida: {txt!r} — use YYYY-MM-DD.")


def _tabela(linhas: list[list[str]], cabecalho: list[str]) -> str:
    """Imprime uma tabela ASCII simples, bem alinhada."""
    matriz = [cabecalho] + linhas
    larguras = [max(len(str(l[i])) for l in matriz) for i in range(len(cabecalho))]
    sep = "  "
    linhas_out = [
        sep.join(str(c).ljust(larguras[i]) for i, c in enumerate(cabecalho)),
        sep.join("-" * larguras[i] for i in range(len(cabecalho))),
    ]
    for l in linhas:
        linhas_out.append(sep.join(str(c).ljust(larguras[i]) for i, c in enumerate(l)))
    return "\n".join(linhas_out)


# ---------------------------------------------------------------------------
# Comandos — SERVICO
# ---------------------------------------------------------------------------


def cmd_servico_listar(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    rows = servico_repo.listar_todos(conn) if args.todos else servico_repo.listar_ativos(conn)
    if not rows:
        print("(nenhum serviço cadastrado)")
        return 0
    linhas = [
        [
            str(r["id"]),
            r["nome"],
            formatar_moeda(int(r["preco_padrao"])),
            r["categoria_servico"] or "—",
            str(r["ordem"]),
            "sim" if r["ativo"] else "não",
        ]
        for r in rows
    ]
    print(_tabela(linhas, ["ID", "Nome", "Preço", "Categoria", "Ordem", "Ativo"]))
    return 0


def cmd_servico_adicionar(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    preco = _parse_reais(args.preco)
    novo_id = servico_repo.criar(
        conn,
        nome=args.nome,
        preco_padrao=preco,
        categoria_servico=args.categoria,
        ordem=args.ordem,
    )
    print(f"Serviço criado (#{novo_id}): {args.nome} — {formatar_moeda(preco)}")
    return 0


def cmd_servico_renomear(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    ok = servico_repo.atualizar(conn, args.id, nome=args.nome)
    if not ok:
        raise SystemExit(f"Serviço #{args.id} não encontrado.")
    print(f"Serviço #{args.id} renomeado para '{args.nome}'.")
    return 0


def cmd_servico_preco(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    preco = _parse_reais(args.preco)
    ok = servico_repo.atualizar(conn, args.id, preco_padrao=preco)
    if not ok:
        raise SystemExit(f"Serviço #{args.id} não encontrado.")
    print(f"Serviço #{args.id} atualizado para {formatar_moeda(preco)}.")
    return 0


def cmd_servico_ordem(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    ok = servico_repo.atualizar(conn, args.id, ordem=args.ordem)
    if not ok:
        raise SystemExit(f"Serviço #{args.id} não encontrado.")
    print(f"Ordem do serviço #{args.id} definida como {args.ordem}.")
    return 0


def cmd_servico_arquivar(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    if not servico_repo.arquivar(conn, args.id):
        raise SystemExit(f"Serviço #{args.id} não encontrado.")
    print(f"Serviço #{args.id} arquivado (soft-delete).")
    return 0


def cmd_servico_reativar(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    if not servico_repo.reativar(conn, args.id):
        raise SystemExit(f"Serviço #{args.id} não encontrado.")
    print(f"Serviço #{args.id} reativado.")
    return 0


# ---------------------------------------------------------------------------
# Comandos — CATEGORIA
# ---------------------------------------------------------------------------


def cmd_categoria_listar(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    rows = categoria_repo.listar_todas(conn) if args.todas else categoria_repo.listar_ativas(conn)
    if not rows:
        print("(nenhuma categoria cadastrada)")
        return 0
    linhas = [
        [str(r["id"]), r["nome"], r["icone"] or "—", "sim" if r["ativo"] else "não"]
        for r in rows
    ]
    print(_tabela(linhas, ["ID", "Nome", "Ícone", "Ativo"]))
    return 0


def cmd_categoria_adicionar(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    novo_id = categoria_repo.criar(conn, nome=args.nome, icone=args.icone)
    print(f"Categoria criada (#{novo_id}): {args.nome}")
    return 0


def cmd_categoria_renomear(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    if not categoria_repo.atualizar(conn, args.id, nome=args.nome):
        raise SystemExit(f"Categoria #{args.id} não encontrada.")
    print(f"Categoria #{args.id} renomeada para '{args.nome}'.")
    return 0


def cmd_categoria_arquivar(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    if not categoria_repo.atualizar(conn, args.id, ativo=False):
        raise SystemExit(f"Categoria #{args.id} não encontrada.")
    print(f"Categoria #{args.id} arquivada.")
    return 0


def cmd_categoria_reativar(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    if not categoria_repo.atualizar(conn, args.id, ativo=True):
        raise SystemExit(f"Categoria #{args.id} não encontrada.")
    print(f"Categoria #{args.id} reativada.")
    return 0


# ---------------------------------------------------------------------------
# Comandos — ITEM FREQUENTE
# ---------------------------------------------------------------------------


def cmd_item_listar(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    rows = (
        item_frequente_repo.listar_todos(conn)
        if args.todos else
        item_frequente_repo.listar_ativos_ordenado_por_uso(conn)
    )
    if not rows:
        print("(nenhum item frequente cadastrado)")
        return 0
    linhas = []
    for r in rows:
        valor = formatar_moeda(int(r["valor_sugerido"])) if r["valor_sugerido"] else "—"
        linhas.append([
            str(r["id"]),
            r["descricao"],
            r["categoria_nome"],
            valor,
            str(r["vezes_usado"]),
            "sim" if r["ativo"] else "não",
        ])
    print(_tabela(linhas, ["ID", "Descrição", "Categoria", "Valor sug.", "Usos", "Ativo"]))
    return 0


def cmd_item_adicionar(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    valor = _parse_reais(args.valor) if args.valor else None
    novo_id = item_frequente_repo.criar(
        conn,
        descricao=args.descricao,
        categoria_id=args.categoria_id,
        valor_sugerido=valor,
    )
    preco_msg = formatar_moeda(valor) if valor else "sem valor sugerido"
    print(f"Item frequente criado (#{novo_id}): {args.descricao} [{preco_msg}]")
    return 0


def cmd_item_renomear(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    if not item_frequente_repo.atualizar(conn, args.id, descricao=args.descricao):
        raise SystemExit(f"Item #{args.id} não encontrado.")
    print(f"Item #{args.id} renomeado para '{args.descricao}'.")
    return 0


def cmd_item_preco(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    valor = _parse_reais(args.valor)
    if not item_frequente_repo.atualizar(conn, args.id, valor_sugerido=valor):
        raise SystemExit(f"Item #{args.id} não encontrado.")
    print(f"Valor sugerido do item #{args.id} → {formatar_moeda(valor)}.")
    return 0


def cmd_item_recategorizar(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    if not item_frequente_repo.atualizar(conn, args.id, categoria_id=args.categoria_id):
        raise SystemExit(f"Item #{args.id} não encontrado.")
    print(f"Item #{args.id} movido para categoria #{args.categoria_id}.")
    return 0


def cmd_item_arquivar(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    if not item_frequente_repo.atualizar(conn, args.id, ativo=False):
        raise SystemExit(f"Item #{args.id} não encontrado.")
    print(f"Item #{args.id} arquivado.")
    return 0


def cmd_item_reativar(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    if not item_frequente_repo.atualizar(conn, args.id, ativo=True):
        raise SystemExit(f"Item #{args.id} não encontrado.")
    print(f"Item #{args.id} reativado.")
    return 0


# ---------------------------------------------------------------------------
# Comandos — CONFIG
# ---------------------------------------------------------------------------


def cmd_config_meta_get(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    valor = configuracao_service.meta_mensal_centavos(conn)
    if valor <= 0:
        print("Meta mensal: não definida.")
    else:
        print(f"Meta mensal: {formatar_moeda(valor)} ({valor} centavos).")
    return 0


def cmd_config_meta_set(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    valor = _parse_reais(args.valor)
    configuracao_service.definir_meta_mensal(conn, valor)
    print(f"Meta mensal definida: {formatar_moeda(valor)}.")
    return 0


# ---------------------------------------------------------------------------
# Comandos — EXPORT
# ---------------------------------------------------------------------------


def cmd_export_xlsx(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    de = _parse_data(args.de)
    ate = _parse_data(args.ate)

    if args.saida:
        saida = Path(args.saida).expanduser().resolve()
    else:
        saida = Path.cwd() / f"fluxo_barber_{de.isoformat()}_a_{ate.isoformat()}.xlsx"

    try:
        arquivo = export_service.exportar_periodo_xlsx(conn, de, ate, saida)
    except ValidacaoError as e:
        raise SystemExit(f"Erro: {e}")
    print(f"Export OK → {arquivo}")
    return 0


# ---------------------------------------------------------------------------
# Comandos — INFO
# ---------------------------------------------------------------------------


def cmd_info(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    tabelas = [
        "servico", "categoria_despesa", "item_despesa_frequente",
        "receita", "despesa", "cliente", "assinatura",
        "pagamento_assinatura", "auditoria", "config",
    ]
    caminho = db_module.default_db_path() if not args.db else Path(args.db)
    print(f"DB: {caminho}")
    for t in tabelas:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:<28} {n:>6}")
    return 0


# ---------------------------------------------------------------------------
# Wiring argparse
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.admin_cli",
        description="Governança via CLI — Fluxo Barber (serviços, categorias, itens, config, export).",
    )
    parser.add_argument("--db", help="Caminho para o .db (usa o padrão se omitido).")

    sub = parser.add_subparsers(dest="comando", required=True)

    # --- servico ------------------------------------------------------------
    p_srv = sub.add_parser("servico", help="Gerenciar serviços do catálogo.")
    sub_srv = p_srv.add_subparsers(dest="sub", required=True)

    p = sub_srv.add_parser("listar", help="Listar serviços.")
    p.add_argument("--todos", action="store_true", help="Incluir arquivados.")
    p.set_defaults(func=cmd_servico_listar)

    p = sub_srv.add_parser("adicionar", help="Criar serviço novo.")
    p.add_argument("nome", help="Nome do serviço.")
    p.add_argument("preco", help="Preço padrão (ex: 35, 35,50, 'R$ 35,50').")
    p.add_argument("--categoria", help="Categoria (Corte, Barba, Combo, etc).")
    p.add_argument("--ordem", type=int, default=999, help="Ordem de exibição na tela Lançar.")
    p.set_defaults(func=cmd_servico_adicionar)

    p = sub_srv.add_parser("renomear", help="Renomear um serviço.")
    p.add_argument("id", type=int)
    p.add_argument("nome")
    p.set_defaults(func=cmd_servico_renomear)

    p = sub_srv.add_parser("preco", help="Ajustar preço padrão.")
    p.add_argument("id", type=int)
    p.add_argument("preco")
    p.set_defaults(func=cmd_servico_preco)

    p = sub_srv.add_parser("ordem", help="Alterar ordem de exibição.")
    p.add_argument("id", type=int)
    p.add_argument("ordem", type=int)
    p.set_defaults(func=cmd_servico_ordem)

    p = sub_srv.add_parser("arquivar", help="Desativar serviço (mantém histórico).")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_servico_arquivar)

    p = sub_srv.add_parser("reativar", help="Reativar serviço arquivado.")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_servico_reativar)

    # --- categoria ----------------------------------------------------------
    p_cat = sub.add_parser("categoria", help="Categorias de despesa.")
    sub_cat = p_cat.add_subparsers(dest="sub", required=True)

    p = sub_cat.add_parser("listar")
    p.add_argument("--todas", action="store_true")
    p.set_defaults(func=cmd_categoria_listar)

    p = sub_cat.add_parser("adicionar")
    p.add_argument("nome")
    p.add_argument("--icone", help="Emoji/ícone opcional (ex: 📦).")
    p.set_defaults(func=cmd_categoria_adicionar)

    p = sub_cat.add_parser("renomear")
    p.add_argument("id", type=int)
    p.add_argument("nome")
    p.set_defaults(func=cmd_categoria_renomear)

    p = sub_cat.add_parser("arquivar")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_categoria_arquivar)

    p = sub_cat.add_parser("reativar")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_categoria_reativar)

    # --- item frequente -----------------------------------------------------
    p_item = sub.add_parser("item", help="Itens frequentes de despesa.")
    sub_item = p_item.add_subparsers(dest="sub", required=True)

    p = sub_item.add_parser("listar")
    p.add_argument("--todos", action="store_true")
    p.set_defaults(func=cmd_item_listar)

    p = sub_item.add_parser("adicionar")
    p.add_argument("descricao")
    p.add_argument("categoria_id", type=int,
                   help="ID da categoria (ver 'categoria listar').")
    p.add_argument("--valor", help="Valor sugerido (opcional).")
    p.set_defaults(func=cmd_item_adicionar)

    p = sub_item.add_parser("renomear")
    p.add_argument("id", type=int)
    p.add_argument("descricao")
    p.set_defaults(func=cmd_item_renomear)

    p = sub_item.add_parser("preco")
    p.add_argument("id", type=int)
    p.add_argument("valor")
    p.set_defaults(func=cmd_item_preco)

    p = sub_item.add_parser("recategorizar")
    p.add_argument("id", type=int)
    p.add_argument("categoria_id", type=int)
    p.set_defaults(func=cmd_item_recategorizar)

    p = sub_item.add_parser("arquivar")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_item_arquivar)

    p = sub_item.add_parser("reativar")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_item_reativar)

    # --- config -------------------------------------------------------------
    p_cfg = sub.add_parser("config", help="Configurações globais do app.")
    sub_cfg = p_cfg.add_subparsers(dest="sub", required=True)

    p_meta = sub_cfg.add_parser("meta-mensal", help="Meta de faturamento mensal.")
    sub_meta = p_meta.add_subparsers(dest="op", required=True)
    sub_meta.add_parser("get").set_defaults(func=cmd_config_meta_get)
    p = sub_meta.add_parser("set")
    p.add_argument("valor", help="Valor em reais (ex: 15000 ou 'R$ 15.000,00').")
    p.set_defaults(func=cmd_config_meta_set)

    # --- export -------------------------------------------------------------
    p_exp = sub.add_parser("export", help="Exportar dados em XLSX.")
    sub_exp = p_exp.add_subparsers(dest="sub", required=True)
    p = sub_exp.add_parser("xlsx")
    p.add_argument("--de", required=True, help="Data inicial YYYY-MM-DD.")
    p.add_argument("--ate", required=True, help="Data final YYYY-MM-DD.")
    p.add_argument("--saida", help="Caminho do .xlsx (default: pasta atual).")
    p.set_defaults(func=cmd_export_xlsx)

    # --- info ---------------------------------------------------------------
    p_info = sub.add_parser("info", help="Contagem das tabelas principais.")
    p_info.set_defaults(func=cmd_info)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    conn = _conn(args)
    try:
        return args.func(conn, args)
    except ValidacaoError as e:
        print(f"Erro de validação: {e}", file=sys.stderr)
        return 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
