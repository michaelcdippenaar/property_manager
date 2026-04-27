"""
Lease expiry job.

Runtime helper that flips ``Lease.status`` from ``active`` to ``expired`` once
``end_date`` is in the past.

Background
----------
Unit occupancy is derived from active leases (see
``apps/leases/signals.py::_resync_unit_status``).  Without this job, a lease
whose term has ended retains ``status="active"`` forever, leaving the unit
flagged as ``occupied`` on the dashboard even though no tenant is in residence.

Scheduling
----------
No Celery in this project — invoked via a Django management command from cron.
See ``apps/leases/management/commands/expire_leases.py``.
"""
from __future__ import annotations

import logging

from django.db import transaction

logger = logging.getLogger(__name__)


def expire_overdue_leases(today=None) -> int:
    """
    Mark every ``active`` lease whose ``end_date`` is before *today* as
    ``expired`` and return the number of rows updated.

    Each lease is saved individually with ``update_fields=["status"]`` so the
    existing ``post_save`` signals fire and the linked Unit's status is
    re-synced from "occupied" to "available" (when no other active+future
    lease exists on the same unit).

    DO NOT replace this with ``QuerySet.update()`` — that bypasses signals
    and would leave Unit.status stale, which is exactly the bug this job
    exists to fix.

    Parameters
    ----------
    today : datetime.date | None
        Override the cut-off date for tests / back-fill.  Defaults to
        ``timezone.localdate()``.

    Returns
    -------
    int
        Number of leases transitioned from active → expired.
    """
    from django.utils import timezone

    from apps.leases.models import Lease

    if today is None:
        today = timezone.localdate()

    count = 0
    with transaction.atomic():
        stale = (
            Lease.objects
            .select_related("unit")
            .filter(status=Lease.Status.ACTIVE, end_date__lt=today)
        )
        for lease in stale:
            lease.status = Lease.Status.EXPIRED
            lease.save(update_fields=["status"])
            logger.info(
                "Lease %s expired (unit=%s, end_date=%s)",
                lease.pk,
                lease.unit_id,
                lease.end_date,
            )
            count += 1

    if count:
        logger.info("expire_overdue_leases: expired %d lease(s)", count)
    return count
