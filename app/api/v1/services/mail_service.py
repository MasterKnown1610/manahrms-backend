"""
Transactional email via SMTP (e.g. Hostinger: port 465 + SSL).
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)

_APP_ROOT = Path(__file__).resolve().parents[3]
_TEMPLATES_DIR = _APP_ROOT / "templates" / "email"
_WELCOME_LOGO_PATH = _APP_ROOT / "templates" / "tab-logo-2.png"
_jinja = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


class MailService:
    @staticmethod
    def is_configured() -> bool:
        return bool(
            settings.EMAIL_HOST
            and settings.EMAIL_USER
            and settings.EMAIL_PASS
        )

    @staticmethod
    def _smtp_connect():
        host = settings.EMAIL_HOST or ""
        port = settings.EMAIL_PORT
        secure = (settings.EMAIL_SECURE or "SSL").strip().upper()
        timeout = 30
        context = ssl.create_default_context()

        if secure == "TLS":
            server = smtplib.SMTP(host, port, timeout=timeout)
            server.starttls(context=context)
            return server

        if secure == "NONE":
            return smtplib.SMTP(host, port, timeout=timeout)

        return smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)

    @staticmethod
    def send_html_email(
        *,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        inline_cid_images: Optional[list[tuple[str, Path]]] = None,
    ) -> bool:
        if not MailService.is_configured():
            logger.warning(
                "Welcome email skipped: set EMAIL_HOST, EMAIL_USER, and EMAIL_PASS in .env "
                "(restart the API after changes)."
            )
            return False

        from_addr = (settings.EMAIL_USER or "").strip()
        from_name = (settings.EMAIL_FROM_NAME or "ManaHRMS").strip()

        # Use MIMEMultipart (not nested EmailMessage): nested messages serialize as
        # message/rfc822 and Gmail/others show "Forwarded message" + From/To/Subject.
        root = MIMEMultipart("alternative")
        root["Subject"] = subject
        root["From"] = f"{from_name} <{from_addr}>"
        root["To"] = to_email
        root.attach(MIMEText(text_body or "", "plain", "utf-8"))

        if inline_cid_images:
            related = MIMEMultipart("related")
            related.attach(MIMEText(html_body, "html", "utf-8"))
            for cid, img_path in inline_cid_images:
                if not img_path.is_file():
                    logger.warning("Inline email image missing: %s", img_path)
                    continue
                ext = img_path.suffix.lower().lstrip(".") or "png"
                subtype = "jpeg" if ext == "jpg" else ext
                img = MIMEImage(img_path.read_bytes(), _subtype=subtype)
                img.add_header("Content-ID", f"<{cid}>")
                img.add_header("Content-Disposition", "inline", filename=img_path.name)
                related.attach(img)
            root.attach(related)
        else:
            root.attach(MIMEText(html_body, "html", "utf-8"))

        msg = root

        try:
            logger.info(
                "SMTP send: host=%s port=%s secure=%s user=%s -> %s",
                settings.EMAIL_HOST,
                settings.EMAIL_PORT,
                (settings.EMAIL_SECURE or "SSL").strip().upper(),
                from_addr,
                to_email,
            )
            with MailService._smtp_connect() as server:
                server.login(from_addr, settings.EMAIL_PASS or "")
                server.send_message(msg)
            logger.info("Email accepted by SMTP for %s (subject=%s)", to_email, subject)
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(
                "SMTP authentication failed for user %s: %s. "
                "Check EMAIL_USER / EMAIL_PASS; if the password contains @ or spaces, wrap it in quotes in .env.",
                from_addr,
                e,
            )
            return False
        except Exception as e:
            logger.exception("Failed to send email to %s: %s", to_email, e)
            return False

    @staticmethod
    def send_registration_welcome(
        *,
        to_email: str,
        admin_name: str,
        company_name: str,
        company_code: str,
        company_email: str,
        admin_email: str,
        username: str,
    ) -> bool:
        login_url = (settings.APP_PUBLIC_URL or "").strip().rstrip("/")
        if login_url:
            login_url = f"{login_url}/login" if "/login" not in login_url else login_url

        logo_cid: Optional[str] = None
        inline: Optional[list[tuple[str, Path]]] = None
        if _WELCOME_LOGO_PATH.is_file():
            logo_cid = "manahrms_logo"
            inline = [(logo_cid, _WELCOME_LOGO_PATH)]
        else:
            logger.warning("Welcome email: logo not found at %s", _WELCOME_LOGO_PATH)

        ctx = {
            "admin_name": admin_name,
            "company_name": company_name,
            "company_code": company_code,
            "company_email": company_email,
            "admin_email": admin_email,
            "username": username,
            "login_url": login_url or None,
            "logo_cid": logo_cid,
            "primary_light": "#7B3FAE",
            "primary_dark": "#4A1A73",
        }
        html_body = _jinja.get_template("welcome_registration.html").render(**ctx)
        text_body = _jinja.get_template("welcome_registration.txt").render(**ctx)

        subject = f"Welcome to ManaHRMS - {company_name} is ready to grow"
        return MailService.send_html_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            inline_cid_images=inline,
        )

    @staticmethod
    def send_password_reset_email(
        *,
        to_email: str,
        full_name: str,
        reset_url: str,
    ) -> bool:
        logo_cid: Optional[str] = None
        inline: Optional[list[tuple[str, Path]]] = None
        if _WELCOME_LOGO_PATH.is_file():
            logo_cid = "manahrms_logo"
            inline = [(logo_cid, _WELCOME_LOGO_PATH)]

        ctx = {
            "full_name": full_name,
            "reset_url": reset_url,
            "logo_cid": logo_cid,
            "primary_light": "#7B3FAE",
            "primary_dark": "#4A1A73",
        }
        html_body = _jinja.get_template("password_reset.html").render(**ctx)
        text_body = _jinja.get_template("password_reset.txt").render(**ctx)

        return MailService.send_html_email(
            to_email=to_email,
            subject="Reset your ManaHRMS password",
            html_body=html_body,
            text_body=text_body,
            inline_cid_images=inline,
        )
