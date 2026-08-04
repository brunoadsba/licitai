"""
Envio de e-mail via SMTP (RF04 — Fase 3.3).

Versão 1: texto simples (sem HTML), envio síncrono executado em thread
(`asyncio.to_thread`) para não bloquear o loop de eventos.

Falhas de envio nunca propagam para a comparação — o chamador decide como
tratar (resposta parcial com `enviados`/`falhas`).
"""

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


class EmailConfigError(RuntimeError):
    """SMTP não configurado (host ou remetente ausentes)."""


def smtp_configurado() -> bool:
    """Indica se há configuração mínima de SMTP (host e remetente)."""
    return bool(settings.smtp_host and settings.smtp_from)


def _enviar(
    to: str,
    subject: str,
    body: str,
) -> None:
    """Envia um e-mail de texto simples (executado em thread)."""
    if not smtp_configurado():
        raise EmailConfigError(
            "SMTP não configurado. Defina SMTP_HOST e SMTP_FROM (e, se "
            "houver autenticação, SMTP_USER/SMTP_PASSWORD) no .env."
        )

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.ehlo()
        if settings.smtp_user:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)

    logger.info("E-mail enviado para %s (assunto: %s)", to, subject)


async def enviar_email(to: str, subject: str, body: str) -> None:
    """Envia um e-mail de forma assíncrona (executa SMTP em thread)."""
    await asyncio.to_thread(_enviar, to, subject, body)
