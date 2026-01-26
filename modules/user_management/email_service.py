"""Email service for sending registration and notification emails via SMTP."""

from __future__ import annotations

import logging
import os
import secrets
import smtplib
import ssl
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import NamedTuple

logger = logging.getLogger(__name__)


def _create_legacy_ssl_context() -> ssl.SSLContext:
    """Create an SSL context compatible with older SMTP servers.

    Some providers (like Antik) use older TLS configurations that
    require a more permissive SSL context.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    # Allow older cipher suites for compatibility
    context.set_ciphers("DEFAULT:@SECLEVEL=1")
    return context


class EmailConfig(NamedTuple):
    """SMTP configuration for email sending."""

    smtp_host: str
    smtp_port: int
    username: str
    password: str
    from_address: str
    use_tls: bool = True
    use_ssl: bool = False


def get_email_config_from_env() -> EmailConfig | None:
    """Load email configuration from environment variables.

    Required environment variables:
        EBOOK_SMTP_HOST: SMTP server hostname (e.g., smtp.antik.sk)
        EBOOK_SMTP_PORT: SMTP port (typically 587 for TLS, 465 for SSL)
        EBOOK_SMTP_USERNAME: SMTP authentication username
        EBOOK_SMTP_PASSWORD: SMTP authentication password
        EBOOK_SMTP_FROM: From address for outgoing emails

    Optional:
        EBOOK_SMTP_USE_TLS: Use STARTTLS (default: true)
        EBOOK_SMTP_USE_SSL: Use SSL/TLS connection (default: false)
    """
    host = os.environ.get("EBOOK_SMTP_HOST")
    port_str = os.environ.get("EBOOK_SMTP_PORT")
    username = os.environ.get("EBOOK_SMTP_USERNAME")
    password = os.environ.get("EBOOK_SMTP_PASSWORD")
    from_address = os.environ.get("EBOOK_SMTP_FROM")

    if not all([host, port_str, username, password, from_address]):
        return None

    try:
        port = int(port_str)  # type: ignore[arg-type]
    except ValueError:
        logger.warning("Invalid EBOOK_SMTP_PORT value: %s", port_str)
        return None

    use_tls = os.environ.get("EBOOK_SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    use_ssl = os.environ.get("EBOOK_SMTP_USE_SSL", "false").lower() in ("true", "1", "yes")

    return EmailConfig(
        smtp_host=host,  # type: ignore[arg-type]
        smtp_port=port,
        username=username,  # type: ignore[arg-type]
        password=password,  # type: ignore[arg-type]
        from_address=from_address,  # type: ignore[arg-type]
        use_tls=use_tls,
        use_ssl=use_ssl,
    )


def generate_initial_password(length: int = 12) -> str:
    """Generate a secure random password for new user registration.

    Args:
        length: Password length (default 12 characters)

    Returns:
        Random password string with letters and digits
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class EmailService:
    """Service for sending emails via SMTP."""

    def __init__(self, config: EmailConfig) -> None:
        self.config = config

    def send_email(
        self,
        *,
        to_address: str,
        subject: str,
        body_text: str,
        body_html: str | None = None,
    ) -> bool:
        """Send an email message.

        Args:
            to_address: Recipient email address
            subject: Email subject line
            body_text: Plain text body
            body_html: Optional HTML body

        Returns:
            True if email was sent successfully, False otherwise
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.config.from_address
        msg["To"] = to_address

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        # Try openssl-based method first (more compatible with legacy servers like Antik)
        if self.config.use_ssl:
            result = self._send_via_openssl(to_address, msg)
            if result:
                return True
            # If openssl method tried and succeeded or we should skip smtplib fallback
            # for servers that work via openssl only
            logger.debug("openssl method did not confirm success, trying smtplib fallback")

        # Fallback to smtplib
        try:
            ssl_context = _create_legacy_ssl_context()

            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(
                    self.config.smtp_host,
                    self.config.smtp_port,
                    context=ssl_context,
                )
            else:
                server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
                if self.config.use_tls:
                    server.starttls(context=ssl_context)

            server.ehlo()
            server.login(self.config.username, self.config.password)
            server.sendmail(self.config.from_address, [to_address], msg.as_string())
            server.quit()
            logger.info("Email sent successfully to %s", to_address)
            return True
        except smtplib.SMTPException as exc:
            logger.error("Failed to send email to %s: %s", to_address, exc)
            return False
        except OSError as exc:
            logger.error("Network error sending email to %s: %s", to_address, exc)
            return False

    def _send_via_openssl(self, to_address: str, msg: MIMEMultipart) -> bool:
        """Send email using openssl s_client for legacy server compatibility.

        Some SMTP servers (like Antik) work better with openssl s_client
        than Python's smtplib due to SSL/TLS compatibility issues.
        """
        import base64
        import subprocess

        try:
            # Build AUTH PLAIN token
            auth_plain = base64.b64encode(
                f"\0{self.config.username}\0{self.config.password}".encode()
            ).decode()

            # Convert message to SMTP-compatible format with CRLF line endings
            msg_str = msg.as_string().replace("\n", "\r\n")

            # Build SMTP dialog
            smtp_dialog = (
                "EHLO localhost\r\n"
                f"AUTH PLAIN {auth_plain}\r\n"
                f"MAIL FROM:<{self.config.from_address}>\r\n"
                f"RCPT TO:<{to_address}>\r\n"
                "DATA\r\n"
                f"{msg_str}\r\n"
                ".\r\n"
                "QUIT\r\n"
            )

            # Use openssl s_client
            proc = subprocess.Popen(
                [
                    "openssl", "s_client",
                    "-connect", f"{self.config.smtp_host}:{self.config.smtp_port}",
                    "-quiet",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            stdout, stderr = proc.communicate(smtp_dialog, timeout=30)

            # Check for successful message acceptance (250 ok with queue ID)
            if "250 ok" in stdout and "qp" in stdout:
                logger.info("Email sent successfully to %s via openssl", to_address)
                return True

            logger.debug("openssl send output: %s", stdout)
            return False

        except FileNotFoundError:
            logger.debug("openssl not available, falling back to smtplib")
            return False
        except subprocess.TimeoutExpired:
            logger.warning("openssl send timed out")
            return False
        except Exception as exc:
            logger.debug("openssl send failed: %s", exc)
            return False

    def send_registration_email(
        self,
        *,
        to_address: str,
        username: str,
        initial_password: str,
        app_name: str = "Language Tools",
        login_url: str | None = None,
    ) -> bool:
        """Send registration confirmation email with initial password.

        Args:
            to_address: New user's email address
            username: Username for login
            initial_password: Generated initial password
            app_name: Application name for email content
            login_url: Optional URL to the login page

        Returns:
            True if email was sent successfully
        """
        subject = f"Welcome to {app_name} - Your Account"

        login_info = ""
        if login_url:
            login_info = f"\nLogin URL: {login_url}\n"

        body_text = f"""Welcome to {app_name}!

Your account has been created. Please use the following credentials to log in:

Username: {username}
Initial Password: {initial_password}
{login_info}
IMPORTANT: Your account is currently suspended and awaiting administrator approval.
You will receive a notification once your account has been activated.

For security, please change your password after your first login.

If you did not request this account, please ignore this email.

Best regards,
{app_name} Team
"""

        body_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #f8fafc; background: #0f172a; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #1e293b; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3); }}
        .header {{ background: linear-gradient(135deg, #38bdf8, #818cf8); color: white; padding: 30px 20px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 1.75em; font-weight: 600; }}
        .content {{ background: #1e293b; padding: 30px; color: #e2e8f0; }}
        .content p {{ margin: 0 0 16px 0; }}
        .credentials {{ background: #0f172a; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #38bdf8; }}
        .credentials dl {{ margin: 0; }}
        .credentials dt {{ font-weight: 600; color: #94a3b8; margin-top: 12px; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.05em; }}
        .credentials dt:first-child {{ margin-top: 0; }}
        .credentials dd {{ margin: 6px 0 0 0; font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace; font-size: 1.1em; color: #f8fafc; }}
        .credentials a {{ color: #38bdf8; text-decoration: none; }}
        .credentials a:hover {{ text-decoration: underline; }}
        .warning {{ background: rgba(251, 191, 36, 0.15); border: 1px solid rgba(251, 191, 36, 0.4); padding: 16px; border-radius: 8px; margin: 20px 0; color: #fbbf24; }}
        .warning strong {{ color: #fcd34d; }}
        .footer {{ text-align: center; color: #64748b; font-size: 0.9em; padding: 20px; background: #0f172a; }}
        .footer p {{ margin: 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to {app_name}</h1>
        </div>
        <div class="content">
            <p>Your account has been created. Please use the following credentials to log in:</p>

            <div class="credentials">
                <dl>
                    <dt>Username</dt>
                    <dd>{username}</dd>
                    <dt>Initial Password</dt>
                    <dd>{initial_password}</dd>
                    {"<dt>Login URL</dt><dd><a href='" + login_url + "'>" + login_url + "</a></dd>" if login_url else ""}
                </dl>
            </div>

            <div class="warning">
                <strong>Important:</strong> Your account is currently suspended and awaiting administrator approval.
                You will receive a notification once your account has been activated.
            </div>

            <p>For security, please change your password after your first login.</p>

            <p>If you did not request this account, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>{app_name} Team</p>
        </div>
    </div>
</body>
</html>
"""

        return self.send_email(
            to_address=to_address,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )

    def send_account_activated_email(
        self,
        *,
        to_address: str,
        username: str,
        app_name: str = "Language Tools",
        login_url: str | None = None,
    ) -> bool:
        """Send notification that user account has been activated.

        Args:
            to_address: User's email address
            username: Username for login
            app_name: Application name for email content
            login_url: Optional URL to the login page

        Returns:
            True if email was sent successfully
        """
        subject = f"{app_name} - Your Account Has Been Activated"

        login_info = ""
        if login_url:
            login_info = f"\nYou can log in at: {login_url}\n"

        body_text = f"""Hello {username},

Great news! Your {app_name} account has been activated by an administrator.

You can now log in using the credentials provided in your registration email.
{login_info}
If you've forgotten your password, please contact an administrator.

Best regards,
{app_name} Team
"""

        body_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #f8fafc; background: #0f172a; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #1e293b; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3); }}
        .header {{ background: linear-gradient(135deg, #38bdf8, #818cf8); color: white; padding: 30px 20px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 1.75em; font-weight: 600; }}
        .content {{ background: #1e293b; padding: 30px; color: #e2e8f0; }}
        .content p {{ margin: 0 0 16px 0; }}
        .success {{ background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.4); padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center; color: #22c55e; }}
        .success strong {{ color: #4ade80; font-size: 1.1em; }}
        .btn {{ display: inline-block; background: linear-gradient(135deg, #38bdf8, #818cf8); color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 10px 0; }}
        .footer {{ text-align: center; color: #64748b; font-size: 0.9em; padding: 20px; background: #0f172a; }}
        .footer p {{ margin: 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Account Activated</h1>
        </div>
        <div class="content">
            <p>Hello {username},</p>

            <div class="success">
                <strong>Your {app_name} account has been activated!</strong>
            </div>

            <p>You can now log in using the credentials provided in your registration email.</p>

            {f'<p style="text-align: center;"><a href="{login_url}" class="btn">Log In Now</a></p>' if login_url else ""}

            <p>If you've forgotten your password, please contact an administrator.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>{app_name} Team</p>
        </div>
    </div>
</body>
</html>
"""

        return self.send_email(
            to_address=to_address,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )


def get_email_service() -> EmailService | None:
    """Get an EmailService instance configured from environment variables.

    Returns:
        EmailService if configuration is available, None otherwise
    """
    config = get_email_config_from_env()
    if config is None:
        return None
    return EmailService(config)
