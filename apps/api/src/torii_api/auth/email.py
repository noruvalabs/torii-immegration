"""Email sending utility — SMTP delivery for verification and password-reset links."""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

from torii_api.config import Settings

log = structlog.get_logger()


def send_email(
    *,
    to_email: str,
    subject: str,
    html_body: str,
    settings: Settings,
) -> bool:
    """Send an HTML email via SMTP. Returns True on success, False on failure.

    When ``smtp_host`` is not configured the send is skipped with a warning log (so
    local dev / CI never blocks on missing SMTP). The verification / reset token is
    always returned to the API response in dev mode so the flow can be tested without
    an email server.
    """
    if not settings.smtp_host:
        log.warning("email.smtp_not_configured", to=to_email, subject=subject)
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    try:
        if settings.smtp_tls:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)

        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)

        server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())
        server.quit()
        log.info("email.sent", to=to_email, subject=subject)
        return True
    except Exception as exc:
        log.error("email.send_failed", to=to_email, error=str(exc))
        return False


def build_verification_email_body(
    *,
    username: str | None,
    verification_url: str,
    base_url: str,
) -> str:
    """Build the HTML body for the email-verification message."""
    display_name = username or "there"
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 500px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #1a1a2e;">Verify your email address</h2>
        <p>Hi {display_name},</p>
        <p>Welcome to Torii! Please verify your email address by clicking the button below:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{verification_url}" style="background-color: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 500;">Verify Email</a>
        </p>
        <p style="color: #666; font-size: 14px;">Or copy this link: <br><a href="{verification_url}">{verification_url}</a></p>
        <p style="color: #666; font-size: 14px;">If you didn't create an account, you can safely ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="color: #999; font-size: 12px;">Torii — Guided immigration form preparation</p>
    </body>
    </html>
    """


def build_password_reset_email_body(
    *,
    username: str | None,
    reset_url: str,
    base_url: str,
) -> str:
    """Build the HTML body for the password-reset message."""
    display_name = username or "there"
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 500px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #1a1a2e;">Reset your password</h2>
        <p>Hi {display_name},</p>
        <p>We received a request to reset your password. Click the button below to choose a new one:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="background-color: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 500;">Reset Password</a>
        </p>
        <p style="color: #666; font-size: 14px;">Or copy this link: <br><a href="{reset_url}">{reset_url}</a></p>
        <p style="color: #666; font-size: 14px;">This link expires in 1 hour. If you didn't request a password reset, you can safely ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="color: #999; font-size: 12px;">Torii — Guided immigration form preparation</p>
    </body>
    </html>
    """
