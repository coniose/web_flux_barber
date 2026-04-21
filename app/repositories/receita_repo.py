"""Repositório de receitas (atendimentos)."""

from __future__ import annotations

import sqlite3
import uuid as uuid_lib
from datetime import date
from typing import Optional

from app.repositories.audit import log_audit, row_to_dict


def inserir(
    conn: sqlite3.Connection,
    *,
    data_atendimento: date | str,
    servico_id: int,
    valor: int,
    forma_pagamento: Optional[str],
    cliente_id: Optional[int] = None,
    assinatura_id: Optional[int] = None,
    observacao: Optional[str] = None,
) -> int:
    data_str = data_atendimento.isoformat() if isinstance(data_atendimento, date) else data_atendimento
    # uuid populado aqui (e não via DEFAULT) para cobrir DBs migrados cuja
    # coluna foi adicionada sem default. ``updated_at`` segue a mesma lógica.
    novo_uuid = uuid_lib.uuid4().hex
    cur = conn.execute(
        """INSERT INTO receita
             (uuid, data, servico_id, cliente_id, assinatura_id, valor,
              forma_pagamento, observacao, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (novo_uuid, data_str, servico_id, cliente_id, assinatura_id,
         valor, forma_pagamento, observacao),
    )
    new_id = cur.lastrowid
    log_audit(conn, "receita", new_id, "INSERT", {
        "uuid": novo_uuid, "data": data_str, "servico_id": servico_id,
        "cliente_id": cliente_id, "assinatura_id": assinatura_id,
        "valor": valor, "forma_pagamento": forma_pagamento,
        "observacao": observacao,
    })
    return new_id


def obter(conn: sqlite3.Connection, receita_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM receita WHERE id = ?", (receita_id,)).fetchone()


def listar_periodo(
    conn: sqlite3.Connection,
    de: date | str,
    ate: date | str,
) -> list[sqlite3.Row]:
    """Receitas no período inclusive (``de`` e ``ate``), com JOINs úteis para a UI."""
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    return conn.execute(
        """SELECT r.*,
                  s.nome AS servico_nome,
                  c.nome AS cliente_nome,
                  p.nome AS plano_nome
             FROM receita r
             JOIN servico s ON s.id = r.servico_id
             LEFT JOIN cliente c ON c.id = r.cliente_id
             LEFT JOIN assinatura a ON a.id = r.assinatura_id
             LEFT JOIN plano_assinatura p ON p.id = a.plano_id
            WHERE r.data BETWEEN ? AND ?
            ORDER BY r.data DESC, r.id DESC""",
        (de_s, ate_s),
    ).fetchall()


def total_periodo(
    conn: sqlite3.Connection,
    de: date | str,
    ate: date | str,
) -> tuple[int, int]:
    """Retorna (total_centavos, qtd_atendimentos) no período."""
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    row = conn.execute(
        """SELECT COALESCE(SUM(valor), 0) AS total,
                  COUNT(*) AS qtd
             FROM receita
            WHERE data BETWEEN ? AND ?""",
        (de_s, ate_s),
    ).fetchone()
    return int(row["total"]), int(row["qtd"])


def atualizar(
    conn: sqlite3.Connection,
    receita_id: int,
    *,
    data_atendimento: Optional[date | str] = None,
    servico_id: Optional[int] = None,
    valor: Optional[int] = None,
    forma_pagamento: Optional[str] = None,
    observacao: Optional[str] = None,
) -> bool:
    antes = obter(conn, receita_id)
    if antes is None:
        return False

    campos = []
    valores: list = []
    if data_atendimento is not None:
        s = data_atendimento.isoformat() if isinstance(data_atendimento, date) else data_atendimento
        campos.append("data = ?"); valores.append(s)
    if servico_id is not None:
        campos.append("servico_id = ?"); valores.append(servico_id)
    if valor is not None:
        campos.append("valor = ?"); valores.append(valor)
    if forma_pagamento is not None:
        campos.append("forma_pagamento = ?"); valores.append(forma_pagamento)
    if observacao is not None:
        campos.append("observacao = ?"); valores.append(observacao)

    if not campos:
        return False

    campos.append("editado_em = datetime('now')")
    valores.append(receita_id)
    conn.execute(f"UPDATE receita SET {', '.join(campos)} WHERE id = ?", valores)
    log_audit(conn, "receita", receita_id, "UPDATE", row_to_dict(antes))
    return True


def excluir(conn: sqlite3.Connection, receita_id: int) -> bool:
    antes = obter(conn, receita_id)
    if antes is None:
        return False
    log_audit(conn, "receita", receita_id, "DELETE", row_to_dict(antes))
    conn.execute("DELETE FROM receita WHERE id = ?", (receita_id,))
    return True


# ---------------------------------------------------------------------------
# Agregações para o Dashboard
# ---------------------------------------------------------------------------


def serie_diaria(
    conn: sqlite3.Connection,
    de: date | str,
    ate: date | str,
) -> list[sqlite3.Row]:
    """Soma de receita e contagem de atendimentos por dia no período.

    Retorna linhas com (data, total, qtd) — apenas dias com atendimento.
    O dashboard preenche dias faltantes com zero ao plotar.
    """
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    return conn.execute(
        """SELECT data,
                  COALESCE(SUM(valor), 0) AS total,
                  COUNT(*) AS qtd
             FROM receita
            WHERE data BETWEEN ? AND ?
            GROUP BY data
            ORDER BY data""",
        (de_s, ate_s),
    ).fetchall()


def ranking_servicos(
    conn: sqlite3.Connection,
    de: date | str,
    ate: date | str,
    limite: int = 10,
) -> list[sqlite3.Row]:
    """Top serviços por faturamento no período."""
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    return conn.execute(
        """SELECT s.id AS servico_id,
                  s.nome AS servico_nome,
                  COALESCE(SUM(r.valor), 0) AS total,
                  COUNT(*) AS qtd
             FROM receita r
             JOIN servico s ON s.id = r.servico_id
            WHERE r.data BETWEEN ? AND ?
            GROUP BY s.id, s.nome
            ORDER BY total DESC, qtd DESC
            LIMIT ?""",
        (de_s, ate_s, limite),
    ).fetchall()


def mix_forma_pagamento(
    conn: sqlite3.Connection,
    de: date | str,
    ate: date | str,
) -> list[sqlite3.Row]:
    """Total e quantidade por forma de pagamento no período.

    Atendimentos com ``forma_pagamento IS NULL`` (cobertos por assinatura
    com valor zero) aparecem agrupados como 'ASSINATURA'.
    """
    de_s = de.isoformat() if isinstance(de, date) else de
    ate_s = ate.isoformat() if isinstance(ate, date) else ate
    return conn.execute(
        """SELECT COALESCE(forma_pagamento, 'ASSINATURA') AS forma,
                  COALESCE(SUM(valor), 0) AS total,
                  COUNT(*) AS qtd
             FROM receita
            WHERE data BETWEEN ? AND ?
            GROUP BY COALESCE(forma_pagamento, 'ASSINATURA')
            ORDER BY total DESC""",
        (de_s, ate_s),
    ).fetchall()
