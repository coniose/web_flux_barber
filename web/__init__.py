"""Flask application factory."""

from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response
from flask_login import LoginManager

from app.repositories.db import ensure_db

# Carrega .env tanto quando iniciado via `flask run` quanto via wsgi.py
load_dotenv(Path(__file__).parent.parent / ".env")

login_manager = LoginManager()


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        if os.environ.get("RAILWAY_ENVIRONMENT"):
            raise RuntimeError(
                "SECRET_KEY não configurada. Execute: "
                "railway variables set SECRET_KEY=$(python -c \"import secrets; print(secrets.token_hex(32))\")"
            )
        secret_key = secrets.token_hex(32)
        logging.warning("SECRET_KEY não definida — gerada aleatoriamente (sessões não persistem entre restarts)")

    app.config["SECRET_KEY"] = secret_key
    app.config["STRIPE_SECRET_KEY"] = os.environ.get("STRIPE_SECRET_KEY", "")
    app.config["STRIPE_PUBLISHABLE_KEY"] = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    app.config["STRIPE_WEBHOOK_SECRET"] = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    app.config["STRIPE_PRICE_ID"] = os.environ.get("STRIPE_PRICE_ID", "")

    if test_config:
        app.config.update(test_config)

    # Garante DB SQLite inicializado (só para autenticação)
    conn = ensure_db()
    _ensure_usuario_table(conn)
    _seed_demo_user(conn)
    conn.close()

    from web.extensions import limiter
    limiter.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para continuar."
    login_manager.login_message_category = "info"

    from web.models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.get_by_id(int(user_id))

    @app.after_request
    def set_security_headers(response: Response) -> Response:
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    from web.auth.routes import auth_bp
    from web.routes.billing import billing_bp
    from web.routes.chat import chat_bp
    from web.routes.dashboard import dashboard_bp
    from web.routes.despesas import despesas_bp
    from web.routes.estoque import estoque_bp
    from web.routes.lancamento import lancamento_bp
    from web.routes.receitas import receitas_bp
    from web.routes.config import config_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(lancamento_bp)
    app.register_blueprint(receitas_bp)
    app.register_blueprint(despesas_bp)
    app.register_blueprint(estoque_bp)
    app.register_blueprint(config_bp)

    return app


def _seed_demo_user(conn) -> None:
    """Garante que a conta de demonstração existe com plano Pro."""
    import uuid as _uuid
    from werkzeug.security import generate_password_hash

    DEMO_EMAIL = "dev@email.com"
    DEMO_NOME = "Demo Dev"
    DEMO_SENHA = "90901010"

    row = conn.execute("SELECT id, plano FROM usuario WHERE email = ?", (DEMO_EMAIL,)).fetchone()
    if row:
        if row["plano"] != "pro":
            conn.execute("UPDATE usuario SET plano = 'pro' WHERE email = ?", (DEMO_EMAIL,))
        return

    conn.execute(
        "INSERT INTO usuario (email, nome, senha_hash, device_id, plano) VALUES (?, ?, ?, ?, ?)",
        (DEMO_EMAIL, DEMO_NOME, generate_password_hash(DEMO_SENHA), _uuid.uuid4().hex, "pro"),
    )


def _ensure_usuario_table(conn) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS usuario (
            id                     INTEGER PRIMARY KEY AUTOINCREMENT,
            email                  TEXT    NOT NULL UNIQUE,
            nome                   TEXT    NOT NULL,
            senha_hash             TEXT    NOT NULL,
            plano                  TEXT    NOT NULL DEFAULT 'free'
                                           CHECK (plano IN ('free', 'pro')),
            device_id              TEXT,
            stripe_customer_id     TEXT,
            stripe_subscription_id TEXT,
            criado_em              TEXT    NOT NULL DEFAULT (datetime('now')),
            ultimo_acesso          TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_usuario_email ON usuario(email);
    """)
    # Tabela de idempotência para webhooks Stripe
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS stripe_events (
            event_id      TEXT PRIMARY KEY,
            tipo          TEXT NOT NULL,
            processado_em TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    # Migrações incrementais para bancos existentes
    for migration in [
        "ALTER TABLE usuario ADD COLUMN device_id TEXT",
        "ALTER TABLE usuario ADD COLUMN plano TEXT NOT NULL DEFAULT 'free'",
        "ALTER TABLE usuario ADD COLUMN stripe_customer_id TEXT",
        "ALTER TABLE usuario ADD COLUMN stripe_subscription_id TEXT",
        "ALTER TABLE usuario ADD COLUMN plano_verificado_em TEXT",
    ]:
        try:
            conn.execute(migration)
        except Exception:
            pass  # coluna já existe
