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
    from web.routes.setup import setup_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(lancamento_bp)
    app.register_blueprint(receitas_bp)
    app.register_blueprint(despesas_bp)
    app.register_blueprint(estoque_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(setup_bp)

    _register_onboarding_gate(app)
    _register_context_processors(app)

    return app


def _register_context_processors(app) -> None:
    from flask_login import current_user

    @app.context_processor
    def inject_negocio():
        if not current_user.is_authenticated:
            return {"nome_negocio": "Flux"}
        try:
            from app.repositories.sql import config_repo
            from web.models import get_user_conn
            conn = get_user_conn()
            nome = config_repo.get_config(conn, "nome_negocio") or "Flux"
            conn.close()
        except Exception:
            nome = "Flux"
        return {"nome_negocio": nome}


def _register_onboarding_gate(app) -> None:
    """Redireciona usuários autenticados sem onboarding para /setup."""
    from flask import redirect, request, url_for
    from flask_login import current_user

    @app.before_request
    def gate_onboarding():
        # Só se aplica a usuários logados
        if not current_user.is_authenticated:
            return None

        # Rotas que não precisam do onboarding completo
        endpoint = request.endpoint or ""
        if (
            endpoint.startswith("auth.")
            or endpoint.startswith("setup.")
            or endpoint.startswith("static")
            or endpoint.startswith("billing.")
        ):
            return None

        from app.repositories.sql import config_repo
        from web.models import get_user_conn
        conn = get_user_conn()
        completo = config_repo.get_config(conn, "onboarding_completo")
        conn.close()
        if not completo:
            return redirect(url_for("setup.index"))


def _seed_demo_user(conn) -> None:
    """Garante que a conta de demonstração existe com plano Pro."""
    import uuid as _uuid
    from werkzeug.security import generate_password_hash

    DEMO_EMAIL = "dev@email.com"
    DEMO_NOME = "Demo Dev"
    DEMO_SENHA = "90901010"

    row = conn.execute("SELECT id, plano, device_id FROM usuario WHERE email = ?", (DEMO_EMAIL,)).fetchone()
    if row:
        if row["plano"] != "pro":
            conn.execute("UPDATE usuario SET plano = 'pro' WHERE email = ?", (DEMO_EMAIL,))
        if not row["device_id"]:
            device_id = _uuid.uuid4().hex
            conn.execute("UPDATE usuario SET device_id = ? WHERE email = ?", (device_id, DEMO_EMAIL))
        else:
            device_id = row["device_id"]
    else:
        device_id = _uuid.uuid4().hex
        conn.execute(
            "INSERT INTO usuario (email, nome, senha_hash, device_id, plano) VALUES (?, ?, ?, ?, ?)",
            (DEMO_EMAIL, DEMO_NOME, generate_password_hash(DEMO_SENHA), device_id, "pro"),
        )

    _seed_demo_onboarding(device_id)


def _seed_demo_onboarding(device_id: str) -> None:
    """Garante que o onboarding do demo user esteja completo."""
    from app.repositories.sql import config_repo
    from app.repositories.user_db import get_user_connection
    try:
        user_conn = get_user_connection(device_id)
        if not config_repo.get_config(user_conn, "onboarding_completo"):
            config_repo.set_config(user_conn, "nome_negocio", "Demo Dev")
            config_repo.set_config(user_conn, "descricao_negocio", "Conta de demonstração do sistema.")
            config_repo.set_config(user_conn, "tipo_trabalho", "ambos")
            config_repo.set_config(user_conn, "formas_pagamento", "PIX,DINHEIRO,MAQUININHA")
            config_repo.set_config(user_conn, "onboarding_completo", "1")
        user_conn.close()
    except Exception:
        pass  # não bloqueia o boot se o DB de usuário falhar


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
    # Rastreamento de consumo de tokens por usuário
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS consumo_chat (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,
            data           TEXT    NOT NULL,
            tokens_entrada INTEGER NOT NULL DEFAULT 0,
            tokens_saida   INTEGER NOT NULL DEFAULT 0,
            criado_em      TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_consumo_user_data ON consumo_chat(user_id, data);
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
