"""Envio de e-mail transacional via Resend (HTTP API — sem SMTP).

Configuração via variáveis de ambiente:
  RESEND_API_KEY   chave da API do Resend
  MAIL_FROM        remetente exibido (padrão: Flux Barber <onboarding@resend.dev>)
"""

from __future__ import annotations

import logging
import os


def _cfg(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def send_password_reset(to_email: str, reset_url: str) -> bool:
    """Envia e-mail de redefinição de senha via Resend. Retorna True se enviado com sucesso."""
    api_key = _cfg("RESEND_API_KEY")
    if not api_key:
        logging.warning("RESEND_API_KEY não configurado — e-mail não enviado.")
        return False

    from_addr = _cfg("MAIL_FROM", "Flux Barber <onboarding@resend.dev>")

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

    text = f"""\
Você solicitou a redefinição de senha no Flux.

Acesse o link abaixo para criar uma nova senha (válido por 1 hora):
{reset_url}

Se não foi você, ignore este e-mail.
"""

    try:
        import resend
        resend.api_key = api_key
        resend.Emails.send({
            "from": from_addr,
            "to": [to_email],
            "subject": "Redefinição de senha — Flux",
            "text": text,
            "html": html,
        })
        return True
    except Exception as exc:
        logging.error("Falha ao enviar e-mail de reset para %s: %s", to_email, exc)
        return False
