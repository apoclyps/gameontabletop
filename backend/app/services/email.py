import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.config import settings

logger = logging.getLogger(__name__)


def _send(to_email: str, subject: str, html_content: str) -> None:
    if not settings.sendgrid_api_key:
        logger.warning("SENDGRID_API_KEY not set — skipping email to %s", to_email)
        return
    message = Mail(
        from_email=(settings.sendgrid_from_email, settings.sendgrid_from_name),
        to_emails=to_email,
        subject=subject,
        html_content=html_content,
    )
    try:
        SendGridAPIClient(settings.sendgrid_api_key).send(message)
    except Exception:
        logger.exception("Failed to send email to %s", to_email)


def send_verification_email(to_email: str, token: str) -> None:
    link = f"{settings.frontend_url}/verify-email?token={token}"
    _send(
        to_email,
        "Verify your Game On Tabletop email",
        f"""
        <p>Welcome to Game On Tabletop!</p>
        <p>Please verify your email address by clicking the link below.
        This link expires in {settings.verification_token_expire_hours} hours.</p>
        <p><a href="{link}">{link}</a></p>
        """,
    )


def send_password_reset_email(to_email: str, token: str) -> None:
    link = f"{settings.frontend_url}/reset-password?token={token}"
    _send(
        to_email,
        "Reset your Game On Tabletop password",
        f"""
        <p>You requested a password reset.</p>
        <p>Click the link below to set a new password.
        This link expires in {settings.password_reset_expire_hours} hours.</p>
        <p><a href="{link}">{link}</a></p>
        <p>If you did not request this, you can ignore this email.</p>
        """,
    )
