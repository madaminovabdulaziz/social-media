import logging
from email.message import EmailMessage

import aiosmtplib

from src.core.config import settings

logger = logging.getLogger(__name__)


async def send_verification_email(to_email: str, code: str) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        logger.warning(
            "SMTP not configured — skipping verification email to %s (code: %s)",
            to_email,
            code,
        )
        return

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message["Subject"] = "Your verification code"
    message.set_content(
        f"Your email verification code is: {code}\n\n"
        "This code expires in 10 minutes.\n"
    )

    send_kwargs: dict = {
        "hostname": settings.SMTP_HOST,
        "port": settings.SMTP_PORT,
        "start_tls": settings.SMTP_USE_TLS,
    }
    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        send_kwargs["username"] = settings.SMTP_USER
        send_kwargs["password"] = settings.SMTP_PASSWORD

    await aiosmtplib.send(message, **send_kwargs)
    logger.info("Verification email sent to %s", to_email)
