from email.utils import parseaddr

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.notifications.services import send_email


class Command(BaseCommand):
    help = (
        "Send a test email using Django’s configured backend "
        "(set EMAIL_* for Gmail SMTP — see apps/notifications/NOTIFICATIONS.md)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "to",
            nargs="?",
            default=None,
            help="Recipient address (default: DEFAULT_FROM_EMAIL — self-test)",
        )

    def handle(self, *args, **options):
        raw = (options["to"] or getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip()
        if not raw:
            self.stderr.write(
                "Set DEFAULT_FROM_EMAIL or pass a recipient: "
                "python manage.py send_test_email you@example.com"
            )
            return

        _, to_addr = parseaddr(raw)
        to = to_addr or raw

        ok = send_email(
            subject="Tremly / Klikk — test email",
            body=(
                "If you received this message, outbound email (e.g. Gmail SMTP) "
                "is configured correctly.\n\n"
                f"Backend: {getattr(settings, 'EMAIL_BACKEND', '')}\n"
            ),
            to_emails=to,
        )
        if ok:
            self.stdout.write(self.style.SUCCESS(f"Sent to {to!r}."))
        else:
            self.stdout.write(
                self.style.ERROR(
                    "Send failed — check server logs and NotificationLog in Django admin."
                )
            )
