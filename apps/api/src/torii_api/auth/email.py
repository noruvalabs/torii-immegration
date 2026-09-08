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
    text_body: str | None = None,
    settings: Settings,
) -> bool:
    """Send an HTML email (with optional plain text part) via SMTP. Returns True on success, False on failure.

    When ``smtp_host`` is not configured the send is skipped with a warning log (so
    local dev / CI never blocks on missing SMTP). The verification / reset token is
    always returned to the API response in dev mode so the flow can be tested without
    an email server.
    """
    if not settings.smtp_host:
        log.warning("email.smtp_not_configured", to=to_email, subject=subject)
        return False

    # Prevent sending to dummy/test domains (RFC 2606 reserved domains used in unit tests)
    if to_email.lower().endswith(
        ("@example.com", "@example.org", "@example.net", "@test.com", "@localhost")
    ):
        log.info("email.skipped_reserved_test_domain", to=to_email, subject=subject)
        return True

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    # Plain text version first for non-HTML email clients and optimal anti-spam score
    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

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


def build_verification_email_text(
    *,
    username: str | None,
    verification_url: str,
) -> str:
    """Build the plain text body for email verification."""
    display_name = username or "there"
    return (
        f"Hi {display_name},\n\n"
        "Welcome to Torii!\n\n"
        "Please verify your email address by opening the following link in your browser:\n"
        f"{verification_url}\n\n"
        "If you didn't create an account with Torii, you can safely ignore this email.\n\n"
        "— Torii Immigration"
    )


def build_verification_email_body(
    *,
    username: str | None,
    verification_url: str,
    base_url: str,
) -> str:
    """Build the modern responsive HTML body for the email-verification message."""
    display_name = username or "there"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify your email address</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; color: #1e293b;">
    <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background-color: #f8fafc; padding: 40px 16px;">
        <tr>
            <td align="center">
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="max-width: 520px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0; overflow: hidden;">
                    <!-- Brand Header -->
                    <tr>
                        <td style="background-color: #0f172a; padding: 28px 32px; text-align: left;">
                            <span style="font-size: 22px; font-weight: 700; color: #ffffff; letter-spacing: -0.5px;">⛩️ Torii</span>
                            <span style="font-size: 13px; color: #94a3b8; margin-left: 8px; font-weight: 500;">Immigration Platform</span>
                        </td>
                    </tr>
                    <!-- Main Content -->
                    <tr>
                        <td style="padding: 36px 32px 28px 32px;">
                            <h1 style="margin: 0 0 16px 0; font-size: 22px; font-weight: 700; color: #0f172a; letter-spacing: -0.3px;">Verify your email address</h1>
                            <p style="margin: 0 0 16px 0; font-size: 15px; line-height: 24px; color: #334155;">Hi <strong>{display_name}</strong>,</p>
                            <p style="margin: 0 0 24px 0; font-size: 15px; line-height: 24px; color: #334155;">
                                Welcome to Torii! To activate your account and start preparing your official immigration dossier, please verify your email address.
                            </p>
                            <!-- Action Button -->
                            <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin: 30px 0;">
                                <tr>
                                    <td align="center">
                                        <a href="{verification_url}" target="_blank" style="display: inline-block; background-color: #4f46e5; color: #ffffff; font-size: 15px; font-weight: 600; text-decoration: none; padding: 14px 32px; border-radius: 8px; box-shadow: 0 2px 4px rgba(79, 70, 229, 0.3);">Verify Email Address</a>
                                    </td>
                                </tr>
                            </table>
                            <!-- Fallback Link -->
                            <div style="background-color: #f1f5f9; border-radius: 8px; padding: 14px 16px; margin: 24px 0;">
                                <p style="margin: 0 0 6px 0; font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Or copy and paste this link:</p>
                                <a href="{verification_url}" style="font-size: 13px; color: #4f46e5; word-break: break-all; text-decoration: underline; line-height: 18px;">{verification_url}</a>
                            </div>
                            <p style="margin: 24px 0 0 0; font-size: 13px; line-height: 20px; color: #64748b;">
                                If you did not register for an account with Torii, you can safely ignore this email.
                            </p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 32px; background-color: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #94a3b8;">
                                &copy; Torii Immigration — Guided immigration form preparation & dossier management.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


def build_password_reset_email_text(
    *,
    username: str | None,
    reset_url: str,
) -> str:
    """Build the plain text body for password reset."""
    display_name = username or "there"
    return (
        f"Hi {display_name},\n\n"
        "We received a request to reset your Torii account password.\n\n"
        "To choose a new password, open the following link in your browser:\n"
        f"{reset_url}\n\n"
        "This link expires in 1 hour. If you didn't request a password reset, you can safely ignore this email.\n\n"
        "— Torii Immigration"
    )


def build_password_reset_email_body(
    *,
    username: str | None,
    reset_url: str,
    base_url: str,
) -> str:
    """Build the modern responsive HTML body for the password-reset message."""
    display_name = username or "there"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset your password</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; color: #1e293b;">
    <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background-color: #f8fafc; padding: 40px 16px;">
        <tr>
            <td align="center">
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="max-width: 520px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0; overflow: hidden;">
                    <!-- Brand Header -->
                    <tr>
                        <td style="background-color: #0f172a; padding: 28px 32px; text-align: left;">
                            <span style="font-size: 22px; font-weight: 700; color: #ffffff; letter-spacing: -0.5px;">⛩️ Torii</span>
                            <span style="font-size: 13px; color: #94a3b8; margin-left: 8px; font-weight: 500;">Immigration Platform</span>
                        </td>
                    </tr>
                    <!-- Main Content -->
                    <tr>
                        <td style="padding: 36px 32px 28px 32px;">
                            <h1 style="margin: 0 0 16px 0; font-size: 22px; font-weight: 700; color: #0f172a; letter-spacing: -0.3px;">Reset your password</h1>
                            <p style="margin: 0 0 16px 0; font-size: 15px; line-height: 24px; color: #334155;">Hi <strong>{display_name}</strong>,</p>
                            <p style="margin: 0 0 24px 0; font-size: 15px; line-height: 24px; color: #334155;">
                                We received a request to reset your password. Click the button below to choose a new password:
                            </p>
                            <!-- Action Button -->
                            <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin: 30px 0;">
                                <tr>
                                    <td align="center">
                                        <a href="{reset_url}" target="_blank" style="display: inline-block; background-color: #4f46e5; color: #ffffff; font-size: 15px; font-weight: 600; text-decoration: none; padding: 14px 32px; border-radius: 8px; box-shadow: 0 2px 4px rgba(79, 70, 229, 0.3);">Reset Password</a>
                                    </td>
                                </tr>
                            </table>
                            <!-- Fallback Link -->
                            <div style="background-color: #f1f5f9; border-radius: 8px; padding: 14px 16px; margin: 24px 0;">
                                <p style="margin: 0 0 6px 0; font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Or copy and paste this link:</p>
                                <a href="{reset_url}" style="font-size: 13px; color: #4f46e5; word-break: break-all; text-decoration: underline; line-height: 18px;">{reset_url}</a>
                            </div>
                            <p style="margin: 24px 0 0 0; font-size: 13px; line-height: 20px; color: #64748b;">
                                This link expires in 1 hour. If you didn't request a password reset, you can safely ignore this email.
                            </p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 32px; background-color: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #94a3b8;">
                                &copy; Torii Immigration — Guided immigration form preparation & dossier management.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
