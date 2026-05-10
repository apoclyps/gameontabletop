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


def send_group_invite_email(to_email: str, group_name: str, inviter_username: str, invite_url: str) -> None:
    _send(
        to_email,
        f"You're invited to join {group_name} on Game On Tabletop",
        f"""
        <p><strong>{inviter_username}</strong> has invited you to join the board game group
        <strong>{group_name}</strong> on Game On Tabletop.</p>
        <p><a href="{invite_url}">Click here to accept the invitation</a></p>
        <p>This link expires in 7 days.</p>
        """,
    )


def send_occurrence_notification_email(
    to_email: str, series_title: str, occurrence_date: str, group_name: str, occurrence_url: str
) -> None:
    _send(
        to_email,
        f"Next {series_title}: {occurrence_date}",
        f"""
        <p>A new board game night has been scheduled for <strong>{group_name}</strong>.</p>
        <p><strong>{series_title}</strong> — {occurrence_date}</p>
        <p><a href="{occurrence_url}">View details and RSVP</a></p>
        """,
    )


def send_poll_created_email(to_email: str, group_name: str, series_title: str, poll_title: str, poll_url: str) -> None:
    _send(
        to_email,
        f"Help pick a date for {series_title}",
        f"""
        <p>A new availability poll has been created for <strong>{group_name}</strong>.</p>
        <p><strong>{poll_title}</strong> — vote on dates for {series_title}.</p>
        <p><a href="{poll_url}">View poll and respond</a></p>
        """,
    )


def send_poll_resolved_email(to_email: str, series_title: str, chosen_date: str, chosen_time: str, occurrence_url: str) -> None:
    _send(
        to_email,
        f"{series_title} is happening on {chosen_date}",
        f"""
        <p>The availability poll for <strong>{series_title}</strong> has been resolved.</p>
        <p>The session is confirmed for <strong>{chosen_date} at {chosen_time}</strong>.</p>
        <p><a href="{occurrence_url}">View details and RSVP</a></p>
        """,
    )
