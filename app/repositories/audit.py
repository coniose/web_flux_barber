"""Helper para gravar trilha de auditoria em UPDATE/DELETE.

Todo repositório que mutar dados chama ``log_audit()`` antes/depois da operação
para registrar o estado anterior em formato JSON.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Mapping


def _json_default(obj: Any) -> str:
    """Fallback de serialização para tipos não triviais (date, datetime, bytes)."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    return str(obj)


def log_audit(
    conn: sqlite3.Connection,
    tabela: str,
    registro_id: int,
    acao: str,
    payload: Mapping[str, Any],
) -> None:
    """Grava uma linha em ``auditoria``.

    :param tabela: nome da tabela afetada.
    :param registro_id: PK do registro afetado.
    :param acao: 'INSERT' | 'UPDATE' | 'DELETE'.
    :param payload: dict com snapshot (estado anterior em DELETE/UPDATE; novo em INSERT).
    """
    conn.execute(
        "INSERT INTO auditoria (tabela, registro_id, acao, payload) VALUES (?, ?, ?, ?)",
        (
            tabela,
            registro_id,
            acao,
            json.dumps(dict(payload), ensure_ascii=False, default=_json_default),
        ),
    )


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Converte sqlite3.Row em dict comum (útil para payload de auditoria)."""
    return {k: row[k] for k in row.keys()}
