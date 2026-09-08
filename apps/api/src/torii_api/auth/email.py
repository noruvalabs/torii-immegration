"""Email sending utility — SMTP delivery for verification and password-reset links."""

from __future__ import annotations

import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import structlog

from torii_api.config import Settings

log = structlog.get_logger()

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSETS_DIR / "logo-icon.png"


def send_email(
    *,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
    settings: Settings,
) -> bool:
    """Send an HTML email (with optional plain text part and inline logo) via SMTP."""
    if not settings.smtp_host:
        log.warning("email.smtp_not_configured", to=to_email, subject=subject)
        return False

    # Prevent sending to dummy/test domains (RFC 2606 reserved domains used in unit tests)
    if to_email.lower().endswith(
        ("@example.com", "@example.org", "@example.net", "@test.com", "@localhost")
    ):
        log.info("email.skipped_reserved_test_domain", to=to_email, subject=subject)
        return True

    msg = MIMEMultipart("related")
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    alt_part = MIMEMultipart("alternative")
    if text_body:
        alt_part.attach(MIMEText(text_body, "plain", "utf-8"))
    alt_part.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt_part)

    # Attach official Torii logo as inline MIME attachment so it displays across all email clients
    if LOGO_PATH.exists():
        try:
            with open(LOGO_PATH, "rb") as f:
                img = MIMEImage(f.read(), _subtype="png")
            img.add_header("Content-ID", "<torii_logo>")
            img.add_header("Content-Disposition", "inline", filename="logo.png")
            msg.attach(img)
        except Exception as exc:
            log.warning("email.attach_logo_failed", error=str(exc))

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
    """Build the modern responsive HTML body for the email-verification message matching Torii's site theme."""
    display_name = username or "there"
    clean_base = base_url.rstrip("/")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify your email address - Torii</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; color: #1e293b;">
    <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background-color: #f8fafc; padding: 40px 16px;">
        <tr>
            <td align="center">
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="max-width: 520px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0; overflow: hidden;">
                    <!-- Brand Header with Official Logo -->
                    <tr>
                        <td style="background-color: #0f172a; padding: 24px 32px;">
                            <table cellpadding="0" cellspacing="0" border="0" role="presentation">
                                <tr>
                                    <td style="vertical-align: middle; padding-right: 14px;">
                                        <a href="{clean_base}" target="_blank" style="text-decoration: none; display: block;">
                                            <img src="cid:torii_logo" alt="Torii" width="36" height="36" style="display: block; width: 36px; height: 36px; border: 0; outline: none; border-radius: 8px;" />
                                        </a>
                                    </td>
                                    <td style="vertical-align: middle;">
                                        <a href="{clean_base}" target="_blank" style="text-decoration: none; display: block;">
                                            <div style="font-size: 22px; font-weight: 700; color: #ffffff; line-height: 1.1;">Torii</div>
                                            <div style="font-size: 10px; font-weight: 600; color: #94a3b8; letter-spacing: 1.2px; text-transform: uppercase; margin-top: 3px;">Immigration Platform</div>
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Primary Blue Accent Line (Matches Site Landing Theme) -->
                    <tr>
                        <td style="height: 3px; background-color: #2563eb; line-height: 3px; font-size: 0;">&nbsp;</td>
                    </tr>
                    <!-- Main Content -->
                    <tr>
                        <td style="padding: 36px 32px 28px 32px;">
                            <h1 style="margin: 0 0 16px 0; font-size: 22px; font-weight: 700; color: #0f172a; letter-spacing: -0.3px;">Verify your email address</h1>
                            <p style="margin: 0 0 16px 0; font-size: 15px; line-height: 24px; color: #334155;">Hi <strong>{display_name}</strong>,</p>
                            <p style="margin: 0 0 24px 0; font-size: 15px; line-height: 24px; color: #334155;">
                                Welcome to Torii! To activate your account and start preparing your official immigration dossier, please verify your email address:
                            </p>
                            <!-- Action Button (Primary Landing Blue: #2563eb) -->
                            <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin: 30px 0;">
                                <tr>
                                    <td align="center">
                                        <a href="{verification_url}" target="_blank" style="display: inline-block; background-color: #2563eb; color: #ffffff; font-size: 15px; font-weight: 600; text-decoration: none; padding: 14px 34px; border-radius: 8px; box-shadow: 0 2px 4px rgba(37, 99, 235, 0.25);">Verify Email Address</a>
                                    </td>
                                </tr>
                            </table>
                            <!-- Fallback Link Box -->
                            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-left: 3px solid #2563eb; border-radius: 0 8px 8px 0; padding: 14px 16px; margin: 24px 0;">
                                <p style="margin: 0 0 6px 0; font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Or copy and paste this link:</p>
                                <a href="{verification_url}" style="font-size: 13px; color: #2563eb; word-break: break-all; text-decoration: underline; line-height: 18px;">{verification_url}</a>
                            </div>
                            <p style="margin: 24px 0 0 0; font-size: 13px; line-height: 20px; color: #64748b;">
                                If you did not create an account with Torii, you can safely ignore this email.
                            </p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 32px; background-color: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #64748b;">
                                &copy; Torii Immigration — Official immigration application & dossier management.
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
    """Build the modern responsive HTML body for the password-reset message matching Torii's site theme."""
    display_name = username or "there"
    clean_base = base_url.rstrip("/")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset your password - Torii</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; color: #1e293b;">
    <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background-color: #f8fafc; padding: 40px 16px;">
        <tr>
            <td align="center">
                <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="max-width: 520px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0; overflow: hidden;">
                    <!-- Brand Header with Official Logo -->
                    <tr>
                        <td style="background-color: #0f172a; padding: 24px 32px;">
                            <table cellpadding="0" cellspacing="0" border="0" role="presentation">
                                <tr>
                                    <td style="vertical-align: middle; padding-right: 14px;">
                                        <a href="{clean_base}" target="_blank" style="text-decoration: none; display: block;">
                                            <img src="cid:torii_logo" alt="Torii" width="36" height="36" style="display: block; width: 36px; height: 36px; border: 0; outline: none; border-radius: 8px;" />
                                        </a>
                                    </td>
                                    <td style="vertical-align: middle;">
                                        <a href="{clean_base}" target="_blank" style="text-decoration: none; display: block;">
                                            <div style="font-size: 22px; font-weight: 700; color: #ffffff; line-height: 1.1;">Torii</div>
                                            <div style="font-size: 10px; font-weight: 600; color: #94a3b8; letter-spacing: 1.2px; text-transform: uppercase; margin-top: 3px;">Immigration Platform</div>
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Primary Blue Accent Line (Matches Site Landing Theme) -->
                    <tr>
                        <td style="height: 3px; background-color: #2563eb; line-height: 3px; font-size: 0;">&nbsp;</td>
                    </tr>
                    <!-- Main Content -->
                    <tr>
                        <td style="padding: 36px 32px 28px 32px;">
                            <h1 style="margin: 0 0 16px 0; font-size: 22px; font-weight: 700; color: #0f172a; letter-spacing: -0.3px;">Reset your password</h1>
                            <p style="margin: 0 0 16px 0; font-size: 15px; line-height: 24px; color: #334155;">Hi <strong>{display_name}</strong>,</p>
                            <p style="margin: 0 0 24px 0; font-size: 15px; line-height: 24px; color: #334155;">
                                We received a request to reset your Torii account password. Click the button below to choose a new password:
                            </p>
                            <!-- Action Button (Primary Landing Blue: #2563eb) -->
                            <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin: 30px 0;">
                                <tr>
                                    <td align="center">
                                        <a href="{reset_url}" target="_blank" style="display: inline-block; background-color: #2563eb; color: #ffffff; font-size: 15px; font-weight: 600; text-decoration: none; padding: 14px 34px; border-radius: 8px; box-shadow: 0 2px 4px rgba(37, 99, 235, 0.25);">Reset Password</a>
                                    </td>
                                </tr>
                            </table>
                            <!-- Fallback Link Box -->
                            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-left: 3px solid #2563eb; border-radius: 0 8px 8px 0; padding: 14px 16px; margin: 24px 0;">
                                <p style="margin: 0 0 6px 0; font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Or copy and paste this link:</p>
                                <a href="{reset_url}" style="font-size: 13px; color: #2563eb; word-break: break-all; text-decoration: underline; line-height: 18px;">{reset_url}</a>
                            </div>
                            <p style="margin: 24px 0 0 0; font-size: 13px; line-height: 20px; color: #64748b;">
                                This link expires in 1 hour. If you didn't request a password reset, you can safely ignore this email.
                            </p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 32px; background-color: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #64748b;">
                                &copy; Torii Immigration — Official immigration application & dossier management.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
