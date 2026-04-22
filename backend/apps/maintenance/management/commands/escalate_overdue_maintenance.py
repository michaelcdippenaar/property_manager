"""
Escalate maintenance tickets that are overdue by more than 48 hours.

Sends an email to every agency admin for the affected agency and sets
``sla_escalated=True`` so the notification is not repeated.

Usage:
    python manage.py escalate_overdue_maintenance
    python manage.py escalate_overdue_maintenance --dry-run

Cron (run hourly, adjust path/user as needed):
    0 * * * * /path/to/venv/bin/python /path/to/manage.py escalate_overdue_maintenance >> /var/log/klikk/sla_escalation.log 2>&1

When Celery Beat is added to the project, the underlying function
``apps.maintenance.tasks.escalate_overdue_maintenance`` can be decorated
with ``@shared_task`` and registered in ``CELERY_BEAT_SCHEDULE``; this
management command can then be retired or kept as a manual fallback.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Escalate maintenance tickets overdue by >48 h to agency admins"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show which tickets would be escalated without sending emails or updating the DB",
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            from datetime import timedelta
            from django.utils import timezone
            from apps.maintenance.models import MaintenanceRequest

            threshold = timezone.now() - timedelta(hours=48)
            tickets = MaintenanceRequest.objects.filter(
                sla_resolve_deadline__lt=threshold,
                status__in=[MaintenanceRequest.Status.OPEN, MaintenanceRequest.Status.IN_PROGRESS],
                sla_escalated=False,
            ).select_related("unit__property", "tenant")

            if not tickets:
                self.stdout.write("No overdue tickets to escalate.")
                return

            for ticket in tickets:
                hours_overdue = (timezone.now() - ticket.sla_resolve_deadline).total_seconds() / 3600
                self.stdout.write(
                    f"  Would escalate #{ticket.pk}: {ticket.title} "
                    f"[{ticket.priority}] — {hours_overdue:.1f}h overdue"
                )
            self.stdout.write(f"Dry-run complete. {tickets.count()} ticket(s) would be escalated.")
            return

        from apps.maintenance.tasks import escalate_overdue_maintenance

        count = escalate_overdue_maintenance()
        self.stdout.write(
            self.style.SUCCESS(f"Escalated {count} overdue maintenance ticket(s).")
        )
