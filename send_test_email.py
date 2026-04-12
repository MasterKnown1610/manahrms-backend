"""
Send the real welcome_registration HTML/text templates with sample data (SMTP from .env).

Usage (from project root):
  python send_test_email.py
  python send_test_email.py other@example.com
"""
import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

from app.api.v1.services.mail_service import MailService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send welcome email template with test data via configured SMTP."
    )
    parser.add_argument(
        "to",
        nargs="?",
        default="raviteja73189@gmail.com",
        help="Recipient email (default: raviteja73189@gmail.com)",
    )
    args = parser.parse_args()
    to = args.to.strip()

    if not MailService.is_configured():
        logging.error("SMTP not configured. Set EMAIL_HOST, EMAIL_USER, EMAIL_PASS in .env")
        return 1

    ok = MailService.send_registration_welcome(
        to_email=to,
        admin_name="Karthik Demo",
        company_name="Acme HR Demo Pvt Ltd",
        company_code="CMP00000099",
        company_email="hr@acme-demo.example",
        admin_email=to,
        username="karthik_admin",
    )
    if ok:
        logging.info("Welcome template sent OK to %s (same HTML as after register-company)", to)
        return 0
    logging.error("Send failed; check logs above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
