"""Conexão SQLite, inicialização de schema e utilitários de DB.

Este é o único módulo que conhece o caminho do banco físico.
A camada de services recebe uma conexão e não se preocupa com setup.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

# -------------------------------------------------------------------- paths --

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def default_db_path() -> Path:
    """Retorna o caminho padrão do DB.

    - Windows: %APPDATA%/FluxoBarber/fluxo_barber.db
    - Outros:  ~/.fluxo_barber/fluxo_barber.db

    Pode ser sobrescrito via variável de ambiente FLUXO_BARBER_DB.
    """
    override = os.environ.get("FLUXO_BARBER_DB")
    if override:
        return Path(override).expanduser().resolve()

    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "FluxoBarber" / "fluxo_barber.db"

    return Path.home() / ".fluxo_barber" / "fluxo_barber.db"


# --------------------------------------------------------------- conexão ---


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Abre conexão SQLite com PRAGMAs de segurança/performance ligados.

    - foreign_keys ON  → FKs são enforçadas.
    - journal_mode WAL → melhor concorrência e resiliência a quedas.
    - row_factory Row  → acesso por nome de coluna.
    """
    db_path = db_path or default_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), isolation_level=None)  # autocommit; abrimos transações explícitas
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Context manager para transação manual (BEGIN/COMMIT/ROLLBACK)."""
    conn.execute("BEGIN")
    try:
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


# --------------------------------------------------------------- schema ----


def load_schema_sql() -> str:
    """Lê o schema.sql do disco."""
    return _SCHEMA_PATH.read_text(encoding="utf-8")


def init_schema(conn: sqlite3.Connection) -> None:
    """Executa o schema.sql (idempotente, usa CREATE TABLE IF NOT EXISTS)."""
    conn.executescript(load_schema_sql())


def ensure_db(db_path: Optional[Path] = None, seed: bool = True) -> sqlite3.Connection:
    """Garante que o DB existe, tem schema aplicado e (opcionalmente) seed.

    Usado no 1º run do app. Idempotente.

    Ordem:
      1. get_connection (abre conexão e liga PRAGMAs)
      2. init_schema (CREATE TABLE IF NOT EXISTS)
      3. apply_migrations (ALTER TABLE em DBs antigos)
      4. apply_seed (só se bancos-semente estiverem vazios)
    """
    db_path = db_path or default_db_path()
    conn = get_connection(db_path)
    init_schema(conn)

    # Imports locais — evitam ciclo, já que ambos importam deste módulo.
    from app.repositories.migrations import apply_migrations
    apply_migrations(conn)

    if seed:
        from app.repositories.seed import apply_seed

        apply_seed(conn)
    return conn


# --------------------------------------------------------------- CLI -------


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Utilitário de DB do Fluxo Barber")
    parser.add_argument("--init", metavar="PATH", help="Inicializa DB no caminho dado (aplica schema + seed).")
    parser.add_argument("--no-seed", action="store_true", help="Não aplica o seed ao inicializar.")
    parser.add_argument("--info", metavar="PATH", help="Imprime contagens básicas do DB.")
    args = parser.parse_args(argv)

    if args.init:
        path = Path(args.init).expanduser().resolve()
        conn = ensure_db(path, seed=not args.no_seed)
        print(f"DB pronto em {path}")
        conn.close()
        return 0

    if args.info:
        path = Path(args.info).expanduser().resolve()
        if not path.exists():
            print(f"DB não existe: {path}", file=sys.stderr)
            return 1
        conn = get_connection(path)
        tabelas = ["servico", "plano_assinatura", "plano_servico", "cliente",
                   "assinatura", "pagamento_assinatura", "receita",
                   "categoria_despesa", "item_despesa_frequente", "despesa",
                   "auditoria", "config"]
        print(f"DB: {path}")
        for t in tabelas:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t:<26} {n:>6}")
        conn.close()
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(_main())
