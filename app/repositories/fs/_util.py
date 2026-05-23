"""Utilitários compartilhados pelos repositórios Firestore."""

from __future__ import annotations

import uuid
from typing import Optional


def new_id() -> int:
    """Gera um ID inteiro positivo de 63 bits globalmente único."""
    return uuid.uuid4().int >> 65


def doc_to_dict(doc) -> Optional[dict]:
    """Converte um DocumentSnapshot em dict com campo 'id' (int)."""
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    data["id"] = int(doc.id) if doc.id.isdigit() else doc.id
    return data


def stream_to_list(query) -> list[dict]:
    """Converte o stream de um Query em lista de dicts."""
    result = []
    for doc in query.stream():
        d = doc_to_dict(doc)
        if d is not None:
            result.append(d)
    return result
