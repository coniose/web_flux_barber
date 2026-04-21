"""Backup automático e manual do banco de dados.

Regras:
- Na abertura do app, se o último backup tiver mais de ``intervalo_horas`` horas,
  cria um novo. Caso contrário, não faz nada.
- Mantém no máximo ``manter`` arquivos (rotação por data de modificação).
- Usa a API oficial ``sqlite3.Connection.backup()`` — atômica e segura mesmo com WAL.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


def pasta_backups_padrao(db_path: Path) -> Path:
    """Pasta de backups irmã ao arquivo do DB."""
    return db_path.parent / "backups"


def _timestamp() -> str:
    # Inclui milissegundos para garantir unicidade mesmo em chamadas rápidas.
    now = datetime.now()
    return now.strftime("%Y%m%d_%H%M%S") + f"_{now.microsecond // 1000:03d}"


def _listar_backups(pasta: Path, prefixo: str) -> list[Path]:
    if not pasta.exists():
        return []
    arquivos = [p for p in pasta.iterdir() if p.is_file() and p.name.startswith(prefixo) and p.suffix == ".db"]
    arquivos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return arquivos


def backup_agora(
    db_path: Path,
    pasta_destino: Optional[Path] = None,
    prefixo: str = "fluxo_barber_",
) -> Path:
    """Cria um backup imediatamente. Retorna o caminho do arquivo criado."""
    if not db_path.exists():
        raise FileNotFoundError(f"DB não existe: {db_path}")

    pasta_destino = pasta_destino or pasta_backups_padrao(db_path)
    pasta_destino.mkdir(parents=True, exist_ok=True)
    destino = pasta_destino / f"{prefixo}{_timestamp()}.db"

    # Usa sqlite3.backup() — atômico, inclui qualquer WAL pendente.
    src = sqlite3.connect(str(db_path))
    try:
        dst = sqlite3.connect(str(destino))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    return destino


def rotacionar(
    pasta: Path,
    manter: int = 30,
    prefixo: str = "fluxo_barber_",
) -> list[Path]:
    """Remove backups antigos mantendo apenas os ``manter`` mais recentes.
    Retorna a lista de arquivos removidos.
    """
    backups = _listar_backups(pasta, prefixo)
    excedentes = backups[manter:]
    for p in excedentes:
        try:
            p.unlink()
        except OSError:
            pass
    return excedentes


def ultimo_backup(
    pasta: Path,
    prefixo: str = "fluxo_barber_",
) -> Optional[Path]:
    backups = _listar_backups(pasta, prefixo)
    return backups[0] if backups else None


def backup_auto_se_necessario(
    db_path: Path,
    pasta_destino: Optional[Path] = None,
    intervalo_horas: int = 24,
    manter: int = 30,
    prefixo: str = "fluxo_barber_",
) -> Optional[Path]:
    """Cria backup se o último tiver mais de ``intervalo_horas`` horas.

    Retorna o caminho do backup criado, ou ``None`` se não foi necessário.
    Também executa a rotação.
    """
    pasta_destino = pasta_destino or pasta_backups_padrao(db_path)
    pasta_destino.mkdir(parents=True, exist_ok=True)

    ultimo = ultimo_backup(pasta_destino, prefixo)
    if ultimo is not None:
        idade = datetime.now() - datetime.fromtimestamp(ultimo.stat().st_mtime)
        if idade < timedelta(hours=intervalo_horas):
            return None

    novo = backup_agora(db_path, pasta_destino, prefixo)
    rotacionar(pasta_destino, manter=manter, prefixo=prefixo)
    return novo


def restaurar(
    db_path: Path,
    arquivo_backup: Path,
    *,
    manter_pre_restore: bool = True,
) -> Optional[Path]:
    """Restaura o DB a partir de um arquivo de backup.

    Se ``manter_pre_restore=True``, faz um backup do DB atual antes de sobrescrever
    (retorna o caminho desse snapshot pré-restore).
    """
    if not arquivo_backup.exists():
        raise FileNotFoundError(f"Backup não existe: {arquivo_backup}")

    pre_restore: Optional[Path] = None
    if manter_pre_restore and db_path.exists():
        pre_restore = backup_agora(
            db_path, pasta_backups_padrao(db_path), prefixo="pre_restore_"
        )

    # Remove arquivos WAL/SHM antes de sobrescrever para evitar inconsistência.
    for sufixo in ("-wal", "-shm", "-journal"):
        lateral = db_path.with_suffix(db_path.suffix + sufixo)
        if lateral.exists():
            lateral.unlink()

    shutil.copy2(arquivo_backup, db_path)
    return pre_restore
