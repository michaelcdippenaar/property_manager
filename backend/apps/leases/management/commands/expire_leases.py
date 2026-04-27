"""
Expire leases whose ``end_date`` has passed.

Flips ``Lease.status`` from ``active`` to ``expired`` for every lease whose
term has ended.  The post_save signal on Lease re-syncs the linked Unit so
it goes from ``occupied`` back to ``available`` (when no other active+future
lease covers the unit).

Usage:
    python manage.py expire_leases
    python manage.py expire_leases --dry-run

Cron (run daily, just after midnight SAST):
    5 0 * * * /path/to/venv/bin/python /path/to/manage.py expire_leases >> /var/log/klikk/lease_expiry.log 2>&1

When Celery Beat is added to the project, the underlying function
``apps.leases.expiry.expire_overdue_leases`` can be decorated with
``@shared_task`` and registered in ``CELERY_BEAT_SCHEDULE``; this management
command can then be retired or kept as a manual fallback.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Expire leases whose end_date is in the past (active → expired)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show which leases would be expired without updating the DB",
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            from django.utils import timezone
            from apps.leases.models import Lease

            today = timezone.localdate()
            stale = (
                Lease.objects
                .select_related("unit__property")
                .filter(status=Lease.Status.ACTIVE, end_date__lt=today)
            )

            if not stale:
                self.stdout.write("No overdue active leases to expire.")
                return

            for lease in stale:
                days_overdue = (today - lease.end_date).days
                self.stdout.write(
                    f"  Would expire lease #{lease.pk}: unit={lease.unit} "
                    f"end_date={lease.end_date} ({days_overdue}d overdue)"
                )
            self.stdout.write(f"Dry-run complete. {stale.count()} lease(s) would be expired.")
            return

        from apps.leases.expiry import expire_overdue_leases

        count = expire_overdue_leases()
        self.stdout.write(
            self.style.SUCCESS(f"Expired {count} overdue lease(s).")
        )
