"""Testes do utilitário de backup."""

from __future__ import annotations

import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.repositories.db import ensure_db
from app.utils import backup


def test_backup_agora_cria_arquivo(tmp_path: Path) -> None:
    db = tmp_path / "src.db"
    ensure_db(db, seed=True).close()

    destino = backup.backup_agora(db)
    assert destino.exists()
    assert destino.stat().st_size > 0
    # É um DB SQLite válido
    conn = sqlite3.connect(str(destino))
    try:
        n = conn.execute("SELECT COUNT(*) FROM servico").fetchone()[0]
        assert n == 37
    finally:
        conn.close()


def test_backup_auto_cria_na_primeira_vez(tmp_path: Path) -> None:
    db = tmp_path / "src.db"
    ensure_db(db, seed=True).close()

    r = backup.backup_auto_se_necessario(db)
    assert r is not None
    assert r.exists()


def test_backup_auto_nao_cria_dentro_do_intervalo(tmp_path: Path) -> None:
    db = tmp_path / "src.db"
    ensure_db(db, seed=True).close()

    primeiro = backup.backup_auto_se_necessario(db)
    assert primeiro is not None

    # Chamada seguida — não deve criar novo dentro de 24h.
    segundo = backup.backup_auto_se_necessario(db)
    assert segundo is None


def test_backup_auto_cria_depois_do_intervalo(tmp_path: Path) -> None:
    db = tmp_path / "src.db"
    ensure_db(db, seed=True).close()

    primeiro = backup.backup_auto_se_necessario(db, intervalo_horas=24)
    assert primeiro is not None

    # Envelhece artificialmente o arquivo.
    antigo = (datetime.now() - timedelta(hours=25)).timestamp()
    os.utime(primeiro, (antigo, antigo))

    segundo = backup.backup_auto_se_necessario(db, intervalo_horas=24)
    assert segundo is not None
    assert segundo != primeiro


def test_rotacao_mantem_apenas_N(tmp_path: Path) -> None:
    db = tmp_path / "src.db"
    ensure_db(db, seed=True).close()
    pasta = backup.pasta_backups_padrao(db)

    # Cria 5 backups com timestamps distintos.
    paths = []
    for _ in range(5):
        paths.append(backup.backup_agora(db))
        time.sleep(1.01)  # garante mtimes diferentes

    removidos = backup.rotacionar(pasta, manter=2)
    assert len(removidos) == 3
    # Restaram exatamente 2.
    restantes = [p for p in pasta.iterdir() if p.is_file() and p.suffix == ".db"]
    assert len(restantes) == 2


def test_restaurar_sobrescreve_db(tmp_path: Path) -> None:
    db = tmp_path / "src.db"
    conn = ensure_db(db, seed=True)
    sid = conn.execute("SELECT id FROM servico WHERE nome='Corte de cabelo'").fetchone()[0]
    conn.close()

    snapshot = backup.backup_agora(db)

    # Modifica o DB: apaga todos os serviços.
    conn = sqlite3.connect(str(db))
    conn.execute("DELETE FROM receita")
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("DELETE FROM plano_servico")
    conn.execute("DELETE FROM servico")
    conn.commit()
    conn.close()

    # Restaura a partir do snapshot.
    pre = backup.restaurar(db, snapshot, manter_pre_restore=True)
    assert pre is not None and pre.exists()

    conn = sqlite3.connect(str(db))
    try:
        n = conn.execute("SELECT COUNT(*) FROM servico").fetchone()[0]
        assert n == 37
    finally:
        conn.close()


def test_backup_arquivo_inexistente_falha(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        backup.backup_agora(tmp_path / "nao_existe.db")
