#!/usr/bin/env python3
"""Test script for email service configuration.

Usage:
    # Set environment variables first:
    export EBOOK_SMTP_HOST=smtp.antik.sk
    export EBOOK_SMTP_PORT=587
    export EBOOK_SMTP_USERNAME=fejo.marek3@atk.sk
    export EBOOK_SMTP_PASSWORD=your_password
    export EBOOK_SMTP_FROM=fejo.marek3@atk.sk

    # Then run:
    python scripts/test_email.py your-test-email@example.com
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.user_management.email_service import (
    get_email_config_from_env,
    get_email_service,
    generate_initial_password,
)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_email.py <recipient_email>")
        print("\nRequired environment variables:")
        print("  EBOOK_SMTP_HOST     - SMTP server (e.g., smtp.antik.sk)")
        print("  EBOOK_SMTP_PORT     - SMTP port (e.g., 587)")
        print("  EBOOK_SMTP_USERNAME - SMTP username")
        print("  EBOOK_SMTP_PASSWORD - SMTP password")
        print("  EBOOK_SMTP_FROM     - From address")
        print("\nOptional:")
        print("  EBOOK_SMTP_USE_TLS  - Use STARTTLS (default: true)")
        print("  EBOOK_SMTP_USE_SSL  - Use SSL connection (default: false)")
        sys.exit(1)

    recipient = sys.argv[1]

    # Check configuration
    print("Checking email configuration...")
    config = get_email_config_from_env()

    if config is None:
        print("\nError: Email configuration incomplete!")
        print("\nCurrent environment:")
        for var in ["EBOOK_SMTP_HOST", "EBOOK_SMTP_PORT", "EBOOK_SMTP_USERNAME",
                    "EBOOK_SMTP_PASSWORD", "EBOOK_SMTP_FROM"]:
            value = os.environ.get(var)
            if var == "EBOOK_SMTP_PASSWORD" and value:
                value = "***" + value[-3:] if len(value) > 3 else "***"
            print(f"  {var}: {value or '(not set)'}")
        sys.exit(1)

    print(f"\nConfiguration found:")
    print(f"  Host: {config.smtp_host}")
    print(f"  Port: {config.smtp_port}")
    print(f"  Username: {config.username}")
    print(f"  From: {config.from_address}")
    print(f"  Use TLS: {config.use_tls}")
    print(f"  Use SSL: {config.use_ssl}")

    # Get service
    service = get_email_service()
    if service is None:
        print("\nError: Could not create email service!")
        sys.exit(1)

    # Generate test password
    test_password = generate_initial_password()
    print(f"\nGenerated test password: {test_password}")

    # Send test registration email
    print(f"\nSending test registration email to: {recipient}")

    success = service.send_registration_email(
        to_address=recipient,
        username=recipient,
        initial_password=test_password,
        app_name="Language Tools (TEST)",
        login_url="https://langtools.fifosk.synology.me",
    )

    if success:
        print("\nSuccess! Test email sent.")
        print(f"Check {recipient} for the registration email.")
    else:
        print("\nFailed to send email. Check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
