"""Testes da CLI de governança (tools.admin_cli).

Foco: garantir que os fluxos principais funcionam — adicionar serviço,
ajustar preço, criar categoria e item, configurar meta, exportar XLSX —
sem passar pela UI. Se um dos comandos quebrar, o dono da barbearia
não consegue governar o sistema, então tem que ficar coberto.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from tools import admin_cli


def _run(tmp_db: Path, *args: str) -> int:
    return admin_cli.main(["--db", str(tmp_db), *args])


# ---------------------------------------------------------------------------
# Serviço
# ---------------------------------------------------------------------------


def test_cli_servico_adicionar_e_listar(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    tmp_db = tmp_path / "cli.db"
    # Nome fora do seed para não colidir com UNIQUE.
    assert _run(tmp_db, "servico", "adicionar", "Corte infantil premium", "45", "--categoria", "Corte") == 0
    out = capsys.readouterr().out
    assert "Corte infantil premium" in out

    assert _run(tmp_db, "servico", "listar") == 0
    out = capsys.readouterr().out
    assert "Corte infantil premium" in out
    assert "R$ 45,00" in out


def test_cli_servico_preco_altera_valor(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    tmp_db = tmp_path / "cli.db"
    _run(tmp_db, "servico", "adicionar", "Novo serviço", "50")
    capsys.readouterr()

    # Pega o ID criado
    from app.repositories import db as db_mod, servico_repo
    conn = db_mod.ensure_db(tmp_db, seed=True)
    sid = conn.execute("SELECT id FROM servico WHERE nome = 'Novo serviço'").fetchone()["id"]
    conn.close()

    assert _run(tmp_db, "servico", "preco", str(sid), "75,50") == 0
    out = capsys.readouterr().out
    assert "R$ 75,50" in out


def test_cli_servico_arquivar_soft_delete(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    tmp_db = tmp_path / "cli.db"
    _run(tmp_db, "servico", "adicionar", "Temporário", "20")
    capsys.readouterr()

    from app.repositories import db as db_mod
    conn = db_mod.ensure_db(tmp_db, seed=True)
    sid = conn.execute("SELECT id FROM servico WHERE nome = 'Temporário'").fetchone()["id"]
    conn.close()

    assert _run(tmp_db, "servico", "arquivar", str(sid)) == 0
    assert _run(tmp_db, "servico", "listar") == 0
    out = capsys.readouterr().out
    assert "Temporário" not in out  # não aparece na lista default (só ativos)

    assert _run(tmp_db, "servico", "listar", "--todos") == 0
    out = capsys.readouterr().out
    assert "Temporário" in out


# ---------------------------------------------------------------------------
# Categoria e item
# ---------------------------------------------------------------------------


def test_cli_categoria_e_item_fluxo_completo(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    tmp_db = tmp_path / "cli.db"

    # Cria categoria
    assert _run(tmp_db, "categoria", "adicionar", "Marketing") == 0
    out = capsys.readouterr().out
    assert "Marketing" in out

    from app.repositories import db as db_mod
    conn = db_mod.ensure_db(tmp_db, seed=True)
    cat_id = conn.execute("SELECT id FROM categoria_despesa WHERE nome = 'Marketing'").fetchone()["id"]
    conn.close()

    # Cria item usando a categoria recém-criada
    assert _run(
        tmp_db, "item", "adicionar", "Tráfego pago", str(cat_id), "--valor", "200,00"
    ) == 0
    out = capsys.readouterr().out
    assert "Tráfego pago" in out
    assert "R$ 200,00" in out


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def test_cli_config_meta_mensal(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    tmp_db = tmp_path / "cli.db"
    assert _run(tmp_db, "config", "meta-mensal", "get") == 0
    out = capsys.readouterr().out
    assert "não definida" in out

    assert _run(tmp_db, "config", "meta-mensal", "set", "15000") == 0
    assert _run(tmp_db, "config", "meta-mensal", "get") == 0
    out = capsys.readouterr().out
    assert "R$ 15.000,00" in out


# ---------------------------------------------------------------------------
# Export XLSX
# ---------------------------------------------------------------------------


def test_cli_export_xlsx_gera_arquivo(tmp_path: Path) -> None:
    tmp_db = tmp_path / "cli.db"
    saida = tmp_path / "out.xlsx"

    hoje = date.today()
    rc = admin_cli.main([
        "--db", str(tmp_db),
        "export", "xlsx",
        "--de", hoje.isoformat(),
        "--ate", hoje.isoformat(),
        "--saida", str(saida),
    ])
    assert rc == 0
    assert saida.exists()
    assert saida.stat().st_size > 0


def test_cli_export_xlsx_rejeita_periodo_invertido(tmp_path: Path) -> None:
    tmp_db = tmp_path / "cli.db"
    # A CLI traduz ValidacaoError em SystemExit com mensagem amigável.
    with pytest.raises(SystemExit) as exc_info:
        admin_cli.main([
            "--db", str(tmp_db),
            "export", "xlsx",
            "--de", "2026-05-01",
            "--ate", "2026-04-01",
            "--saida", str(tmp_path / "x.xlsx"),
        ])
    assert "anterior" in str(exc_info.value).lower()
