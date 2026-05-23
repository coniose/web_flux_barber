"""User model para Flask-Login."""

from __future__ import annotations

import uuid

from flask_login import UserMixin, current_user
from werkzeug.security import check_password_hash, generate_password_hash

from app.repositories.db import get_connection


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.email = row["email"]
        self.nome = row["nome"]
        self.plano = row["plano"]
        self.device_id = row["device_id"]
        self._senha_hash = row["senha_hash"]

    @property
    def is_pro(self) -> bool:
        return self.plano == "pro"

    # ------------------------------------------------------------------
    # Finders
    # ------------------------------------------------------------------

    @classmethod
    def get_by_id(cls, user_id: int) -> "User | None":
        conn = get_connection()
        row = conn.execute("SELECT * FROM usuario WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return cls(row) if row else None

    @classmethod
    def get_by_email(cls, email: str) -> "User | None":
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM usuario WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
        conn.close()
        return cls(row) if row else None

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    @classmethod
    def criar(cls, nome: str, email: str, senha: str) -> "User":
        hash_ = generate_password_hash(senha)
        device_id = uuid.uuid4().hex  # namespace Firestore exclusivo
        conn = get_connection()
        conn.execute(
            "INSERT INTO usuario (nome, email, senha_hash, device_id) VALUES (?, ?, ?, ?)",
            (nome.strip(), email.lower().strip(), hash_, device_id),
        )
        row = conn.execute(
            "SELECT * FROM usuario WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
        conn.close()
        return cls(row)

    def verificar_senha(self, senha: str) -> bool:
        return check_password_hash(self._senha_hash, senha)

    def registrar_acesso(self) -> None:
        conn = get_connection()
        conn.execute(
            "UPDATE usuario SET ultimo_acesso = datetime('now') WHERE id = ?", (self.id,)
        )
        conn.close()


def get_store():
    """Retorna um BarberStore para o usuário autenticado."""
    from app.repositories.firestore_client import get_firestore_client
    from app.repositories.fs.store import BarberStore
    return BarberStore(db=get_firestore_client(), device_id=current_user.device_id)
