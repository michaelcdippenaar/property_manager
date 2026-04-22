"""
expire_mandates management command
===================================
Transitions mandates whose `end_date` has passed from `active` → `expired`
and sends reminder notifications to agents at 30, 14, and 7 days before expiry.

Usage (run daily via cron / systemd timer):
    python manage.py expire_mandates
    python manage.py expire_mandates --dry-run

Because this project has no Celery, the command is invoked by the OS scheduler
(cron entry: `0 6 * * * .../manage.py expire_mandates`).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)

# Days before expiry on which to fire reminder emails.
REMINDER_DAYS = [30, 14, 7]


def _send_expiry_reminder(mandate, days_remaining: int) -> None:
    """
    Send a reminder notification to the agent assigned to the mandate's property.

    In production this should send an email via Django's email backend or a
    notification service.  This implementation uses logging so there is no hard
    dependency on the email stack in tests.
    """
    agent = mandate.property.agent
    if not agent:
        logger.warning(
            "expire_mandates: mandate %d has no agent — skipping reminder", mandate.pk
        )
        return

    agent_email = getattr(agent, "email", "") or ""
    property_name = mandate.property.name or f"property #{mandate.property_id}"
    end_date_str = mandate.end_date.strftime("%-d %B %Y") if mandate.end_date else "—"

    logger.info(
        "expire_mandates: sending %d-day expiry reminder for mandate %d "
        "(property=%s, end=%s, agent=%s)",
        days_remaining, mandate.pk, property_name, end_date_str, agent_email,
    )

    # Attempt a real email if Django email is configured.
    try:
        from django.core.mail import send_mail
        from django.conf import settings

        subject = (
            f"Mandate expiring in {days_remaining} day{'s' if days_remaining != 1 else ''} "
            f"— {property_name}"
        )
        body = (
            f"Hi,\n\n"
            f"The rental mandate for {property_name} expires on {end_date_str} "
            f"({days_remaining} day{'s' if days_remaining != 1 else ''} from today).\n\n"
            f"Please contact the owner to discuss renewal or termination.\n\n"
            f"Klikk Properties"
        )
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [agent_email],
            fail_silently=True,
        )
    except Exception:
        # Non-fatal — the state transitions proceed regardless.
        logger.exception(
            "expire_mandates: failed to email agent for mandate %d", mandate.pk
        )


class Command(BaseCommand):
    help = (
        "Expire mandates past their end_date and send 30/14/7-day expiry reminders."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would change without writing to the database.",
        )

    def handle(self, *args, **options):
        from apps.properties.models import RentalMandate

        dry_run: bool = options["dry_run"]
        today: date = timezone.localdate()

        # ── 1. Expire mandates whose end_date has passed ─────────────────────

        expirable = RentalMandate.objects.filter(
            status=RentalMandate.Status.ACTIVE,
            end_date__lt=today,
        )

        expired_count = 0
        for mandate in expirable:
            if dry_run:
                self.stdout.write(
                    f"[dry-run] Would expire mandate {mandate.pk} "
                    f"({mandate.property.name}, end={mandate.end_date})"
                )
            else:
                mandate.status = RentalMandate.Status.EXPIRED
                mandate.save(update_fields=["status", "updated_at"])
                logger.info(
                    "expire_mandates: expired mandate %d (property=%s, end=%s)",
                    mandate.pk, mandate.property.name, mandate.end_date,
                )
            expired_count += 1

        # ── 2. Send expiry reminders for mandates approaching end_date ───────

        reminder_count = 0
        for days in REMINDER_DAYS:
            target_date = today + timedelta(days=days)
            approaching = RentalMandate.objects.filter(
                status=RentalMandate.Status.ACTIVE,
                end_date=target_date,
            ).select_related("property__agent")

            for mandate in approaching:
                if dry_run:
                    self.stdout.write(
                        f"[dry-run] Would send {days}-day reminder for mandate "
                        f"{mandate.pk} ({mandate.property.name})"
                    )
                else:
                    _send_expiry_reminder(mandate, days_remaining=days)
                reminder_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"expire_mandates: expired={expired_count}, reminders_queued={reminder_count}"
                + (" (dry-run)" if dry_run else "")
            )
        )
