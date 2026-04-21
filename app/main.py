"""Entry-point do Fluxo Barber.

Executar com: ``python -m app.main``

Flags:
  --init        inicializa o DB e sai (útil para testes/setup)
  --cli         modo linha de comando (não abre UI)
"""

from __future__ import annotations

import sys

from app.repositories.db import default_db_path, ensure_db


def _modo_cli() -> int:
    db_path = default_db_path()
    print(f"[Fluxo Barber] Inicializando banco em: {db_path}")
    conn = ensure_db(db_path, seed=True)
    try:
        n_servicos = conn.execute("SELECT COUNT(*) FROM servico").fetchone()[0]
        n_planos = conn.execute("SELECT COUNT(*) FROM plano_assinatura").fetchone()[0]
        n_categorias = conn.execute("SELECT COUNT(*) FROM categoria_despesa").fetchone()[0]
        print(
            f"[Fluxo Barber] OK. {n_servicos} serviços, {n_planos} planos, "
            f"{n_categorias} categorias de despesa."
        )
    finally:
        conn.close()
    return 0


def _modo_ui() -> int:
    # Imports tardios para evitar custo se --cli.
    from app.ui import theme
    from app.ui.app_window import AppWindow

    theme.aplicar_tema_global()
    app = AppWindow()
    app.mainloop()
    return 0


def main() -> int:
    if "--init" in sys.argv or "--cli" in sys.argv:
        return _modo_cli()
    try:
        return _modo_ui()
    except ModuleNotFoundError as e:
        print(
            f"[Fluxo Barber] Falha ao carregar a UI: {e}\n"
            f"Verifique se 'customtkinter' está instalado "
            f"(pip install -r requirements.txt).",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
