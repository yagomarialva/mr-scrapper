"""
Mr. Scrapper — Email Service
Sends HTML confirmation emails via SMTP using aiosmtplib.
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


# ── HTML Email Template ─────────────────────────────────────────

CONFIRMATION_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background-color:#0f0f0f; font-family:'Inter',Arial,sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f0f0f; padding:40px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0"
                       style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
                              border-radius:16px; padding:40px; border:1px solid rgba(124,58,237,0.3);">
                    <tr>
                        <td align="center" style="padding-bottom:30px;">
                            <h1 style="color:#fff; font-size:28px; margin:0;">
                                🎬 Mr. Scrapper
                            </h1>
                            <p style="color:#a0a0b0; font-size:14px; margin:8px 0 0;">
                                Automated Video Database Builder
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:20px 0;">
                            <h2 style="color:#e0e0ff; font-size:20px; margin:0 0 16px;">
                                Confirme seu email, {name}!
                            </h2>
                            <p style="color:#c0c0d0; font-size:15px; line-height:1.6; margin:0 0 24px;">
                                Você está a um passo de acessar o Mr. Scrapper.
                                Clique no botão abaixo para verificar seu endereço de email
                                e ativar sua conta.
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td align="center" style="padding:10px 0 30px;">
                            <a href="{confirmation_url}"
                               style="display:inline-block; padding:14px 40px;
                                      background:linear-gradient(135deg,#7c3aed 0%,#2563eb 100%);
                                      color:#fff; text-decoration:none; font-size:16px;
                                      font-weight:600; border-radius:10px;
                                      box-shadow:0 4px 20px rgba(124,58,237,0.4);">
                                ✅ Confirmar Email
                            </a>
                        </td>
                    </tr>
                    <tr>
                        <td style="border-top:1px solid rgba(255,255,255,0.1); padding-top:20px;">
                            <p style="color:#808090; font-size:12px; line-height:1.5; margin:0;">
                                Se você não criou esta conta, ignore este email.<br>
                                Este link expira em 24 horas.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


async def send_confirmation_email(
    to_email: str,
    name: str,
    confirmation_token: str,
) -> bool:
    """
    Send an HTML email with the confirmation link.
    Returns True on success, False on failure (non-blocking).
    """
    confirmation_url = (
        f"{settings.FRONTEND_URL}/confirm?token={confirmation_token}"
    )

    html_body = CONFIRMATION_TEMPLATE.format(
        name=name,
        confirmation_url=confirmation_url,
    )

    message = MIMEMultipart("alternative")
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM}>"
    message["To"] = to_email
    message["Subject"] = "🎬 Mr. Scrapper — Confirme seu email"

    # Plain text fallback
    plain_text = (
        f"Olá {name}!\n\n"
        f"Confirme seu email acessando: {confirmation_url}\n\n"
        f"Este link expira em 24 horas."
    )
    message.attach(MIMEText(plain_text, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info(f"Confirmation email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send confirmation email to {to_email}: {e}")
        return False
