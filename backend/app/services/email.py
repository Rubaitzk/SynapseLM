import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict
import httpx

from app.core.config import settings

logger = logging.getLogger("synapselm.email")

# In-memory test store for automated testing assertions
_test_outbox: List[Dict[str, str]] = []

def get_test_outbox() -> List[Dict[str, str]]:
    return _test_outbox

def clear_test_outbox():
    _test_outbox.clear()

def send_password_reset_email(to_email: str, username: str, reset_token: str) -> bool:
    """
    Sends a transactional password reset email with a link pointing to the configured FRONTEND_URL.
    Supports Resend API, standard SMTP, and logs cleanly if no delivery provider is configured.
    """
    frontend_base = settings.FRONTEND_URL.rstrip("/")
    reset_url = f"{frontend_base}/reset-password?token={reset_token}"
    subject = "Reset your SynapseLM password"

    text_content = f"""Hello {username},

We received a request to reset your SynapseLM account password.

To set a new password, open the link below in your browser:
{reset_url}

This link is valid for 30 minutes and can only be used once.

If you did not request a password reset, you can safely ignore this email. Your password will not change.

Best regards,
The SynapseLM Team
"""

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Reset your SynapseLM password</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f9fafb; margin: 0; padding: 40px 20px;">
  <div style="max-width: 540px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #e5e7eb; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
    <div style="background-color: #1e293b; padding: 24px; text-align: center;">
      <h1 style="color: #ffffff; margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px;">SynapseLM</h1>
    </div>
    <div style="padding: 32px 28px;">
      <h2 style="color: #111827; font-size: 18px; margin-top: 0; margin-bottom: 16px;">Password Reset Request</h2>
      <p style="color: #4b5563; font-size: 14px; line-height: 1.6; margin-bottom: 24px;">
        Hello <strong>{username}</strong>,<br><br>
        We received a request to reset your SynapseLM password. Click the button below to choose a new password:
      </p>
      <div style="text-align: center; margin: 32px 0;">
        <a href="{reset_url}" style="background-color: #2563eb; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-size: 14px; font-weight: 600; display: inline-block;">
          Reset Password
        </a>
      </div>
      <p style="color: #6b7280; font-size: 12px; line-height: 1.5; margin-bottom: 8px;">
        Or copy and paste this link into your browser:
      </p>
      <p style="color: #2563eb; font-size: 12px; word-break: break-all; margin-bottom: 24px;">
        <a href="{reset_url}" style="color: #2563eb; text-decoration: underline;">{reset_url}</a>
      </p>
      <p style="color: #9ca3af; font-size: 12px; line-height: 1.5; border-top: 1px solid #f3f4f6; padding-top: 20px; margin-bottom: 0;">
        This link expires in 30 minutes. If you did not request this, please disregard this email.
      </p>
    </div>
  </div>
</body>
</html>
"""

    # Record in test outbox for test environments
    _test_outbox.append({
        "to": to_email,
        "username": username,
        "token": reset_token,
        "reset_url": reset_url,
        "subject": subject
    })

    # Option 1: Resend HTTP API
    if settings.RESEND_API_KEY:
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                    json={
                        "from": settings.SMTP_FROM,
                        "to": [to_email],
                        "subject": subject,
                        "html": html_content,
                        "text": text_content,
                    }
                )
                if res.status_code in [200, 201]:
                    logger.info("Password reset email sent via Resend to %s", to_email)
                    return True
                else:
                    logger.error("Resend API error: %s %s", res.status_code, res.text)
        except Exception as e:
            logger.error("Failed sending email via Resend: %s", e)

    # Option 2: Standard SMTP
    if settings.SMTP_HOST:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_FROM
            msg["To"] = to_email
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.ehlo()
                if settings.SMTP_PORT != 25:
                    server.starttls()
                    server.ehlo()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM, [to_email], msg.as_string())
            logger.info("Password reset email sent via SMTP to %s", to_email)
            return True
        except Exception as e:
            logger.error("Failed sending email via SMTP: %s", e)

    # Fallback when no email provider is configured
    if settings.ENVIRONMENT.lower() != "production":
        logger.warning(
            "No email provider configured. [DEV/TEST] Password reset link for %s: %s",
            to_email, reset_url
        )
    else:
        logger.warning(
            "Transactional email provider is not configured in production. Password reset token created for %s.",
            to_email
        )
    return False
