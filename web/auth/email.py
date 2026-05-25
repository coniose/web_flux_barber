"""Envio de e-mail transacional via SMTP.

Configuração via variáveis de ambiente:
  MAIL_SERVER    (padrão: smtp.gmail.com)
  MAIL_PORT      (padrão: 587)
  MAIL_USERNAME  e-mail remetente
  MAIL_PASSWORD  senha ou app-password
  MAIL_FROM      remetente exibido (padrão: MAIL_USERNAME)
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _cfg(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def send_password_reset(to_email: str, reset_url: str) -> bool:
    """Envia e-mail de redefinição de senha. Retorna True se enviado com sucesso."""
    username = _cfg("MAIL_USERNAME")
    password = _cfg("MAIL_PASSWORD")

    if not username or not password:
        logging.warning("MAIL_USERNAME / MAIL_PASSWORD não configurados — e-mail não enviado.")
        return False

    server   = _cfg("MAIL_SERVER",   "smtp.gmail.com")
    port     = int(_cfg("MAIL_PORT", "587"))
    from_    = _cfg("MAIL_FROM", username)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Redefinição de senha — Flux"
    msg["From"]    = f"Flux <{from_}>"
    msg["To"]      = to_email

    text = f"""\
Você solicitou a redefinição de senha no Flux.

Acesse o link abaixo para criar uma nova senha (válido por 1 hora):
{reset_url}

Se não foi você, ignore este e-mail.
"""
    html = f"""\
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"></head>
<body style="font-family:sans-serif;background:#111827;margin:0;padding:24px;">
  <div style="max-width:480px;margin:0 auto;background:#1f2937;border-radius:12px;
              border:1px solid #374151;padding:32px;">
    <div style="margin-bottom:24px;">
      <span style="display:inline-flex;align-items:center;justify-content:center;
                   width:36px;height:36px;background:#10b981;border-radius:8px;
                   color:#fff;font-weight:700;font-size:14px;">F</span>
    </div>
    <h1 style="color:#fff;font-size:20px;margin:0 0 8px;">Redefinição de senha</h1>
    <p style="color:#9ca3af;font-size:14px;line-height:1.6;margin:0 0 24px;">
      Você solicitou a redefinição de senha. Clique no botão abaixo para criar uma nova senha.
      O link expira em <strong style="color:#e5e7eb;">1 hora</strong>.
    </p>
    <a href="{reset_url}"
       style="display:inline-block;background:#10b981;color:#fff;font-weight:600;
              font-size:14px;padding:12px 24px;border-radius:8px;text-decoration:none;">
      Redefinir senha
    </a>
    <p style="color:#6b7280;font-size:12px;margin:24px 0 0;">
      Se não foi você quem solicitou, ignore este e-mail — sua senha não será alterada.
    </p>
  </div>
</body>
</html>
"""
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(server, port, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(username, password)
            smtp.sendmail(from_, to_email, msg.as_string())
        return True
    except Exception as exc:
        logging.error("Falha ao enviar e-mail de reset para %s: %s", to_email, exc)
        return False
