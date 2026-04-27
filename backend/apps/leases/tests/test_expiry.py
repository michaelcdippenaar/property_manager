"""
RNT-026 — Lease expiry job + Unit-status defence-in-depth.

Covers:
    1. expire_overdue_leases flips active+past-end_date → expired
    2. It does NOT touch active leases with future end_date
    3. It does NOT touch already-expired or terminated leases
    4. After expiry, the Unit's status flips to "available" via post_save signal
    5. If the unit has another active+future lease, Unit stays "occupied"
    6. Returns the correct count
    7. Idempotent — second call yields 0
    8. Hardened _resync_unit_status: saving an active lease with past end_date
       does NOT mark the unit occupied
    9. Management command --dry-run makes no DB changes

Run:
    cd backend && python manage.py test apps.leases.tests.test_expiry -v 2
"""
from __future__ import annotations

from datetime import date, timedelta
from io import StringIO

import pytest
from django.core.management import call_command

from apps.leases.expiry import expire_overdue_leases
from apps.leases.models import Lease
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration, pytest.mark.green]


class ExpireOverdueLeasesTests(TremlyAPITestCase):
    def setUp(self):
        self.agent = self.create_agent(email="agent-expiry@test.com")
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.today = date.today()

    # ── Core behaviour ─────────────────────────────────────────────────── #

    def test_expires_active_lease_with_past_end_date(self):
        lease = self.create_lease(
            unit=self.unit,
            status="active",
            start_date=self.today - timedelta(days=400),
            end_date=self.today - timedelta(days=10),
        )
        n = expire_overdue_leases()
        lease.refresh_from_db()
        self.assertEqual(n, 1)
        self.assertEqual(lease.status, Lease.Status.EXPIRED)

    def test_does_not_touch_active_lease_with_future_end_date(self):
        lease = self.create_lease(
            unit=self.unit,
            status="active",
            start_date=self.today - timedelta(days=10),
            end_date=self.today + timedelta(days=300),
        )
        n = expire_overdue_leases()
        lease.refresh_from_db()
        self.assertEqual(n, 0)
        self.assertEqual(lease.status, "active")

    def test_does_not_touch_already_expired_or_terminated(self):
        l_expired = self.create_lease(
            unit=self.unit, status="expired",
            start_date=self.today - timedelta(days=400),
            end_date=self.today - timedelta(days=30),
        )
        unit2 = self.create_unit(property_obj=self.prop, unit_number="102")
        l_term = self.create_lease(
            unit=unit2, status="terminated",
            start_date=self.today - timedelta(days=400),
            end_date=self.today - timedelta(days=20),
        )
        n = expire_overdue_leases()
        l_expired.refresh_from_db()
        l_term.refresh_from_db()
        self.assertEqual(n, 0)
        self.assertEqual(l_expired.status, "expired")
        self.assertEqual(l_term.status, "terminated")

    # ── Unit re-sync via signal ────────────────────────────────────────── #

    def test_unit_flips_to_available_after_expiry(self):
        self.create_lease(
            unit=self.unit, status="active",
            start_date=self.today - timedelta(days=400),
            end_date=self.today - timedelta(days=5),
        )
        # Sanity: signal on lease save forced it to "occupied" *before* the
        # hardening, but with hardening the signal already filters by
        # end_date. Force the unit to "occupied" to simulate legacy state.
        self.unit.status = "occupied"
        self.unit.save(update_fields=["status"])

        expire_overdue_leases()
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.status, "available")

    def test_unit_stays_occupied_when_another_active_future_lease_exists(self):
        # Stale lease on the unit
        self.create_lease(
            unit=self.unit, status="active",
            start_date=self.today - timedelta(days=400),
            end_date=self.today - timedelta(days=5),
        )
        # In-term lease on the same unit
        self.create_lease(
            unit=self.unit, status="active",
            start_date=self.today - timedelta(days=2),
            end_date=self.today + timedelta(days=300),
        )
        # Force unit occupied (the second create_lease save already does this
        # via the signal, but be explicit).
        self.unit.status = "occupied"
        self.unit.save(update_fields=["status"])

        expire_overdue_leases()
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.status, "occupied")

    # ── Idempotency ────────────────────────────────────────────────────── #

    def test_idempotent_second_call_yields_zero(self):
        self.create_lease(
            unit=self.unit, status="active",
            start_date=self.today - timedelta(days=400),
            end_date=self.today - timedelta(days=1),
        )
        first = expire_overdue_leases()
        second = expire_overdue_leases()
        self.assertEqual(first, 1)
        self.assertEqual(second, 0)

    # ── Hardened signal ────────────────────────────────────────────────── #

    def test_hardened_signal_does_not_mark_unit_occupied_for_stale_active(self):
        """
        Saving an ``active`` lease whose end_date is in the past should NOT
        cause the unit to be flagged ``occupied`` — the signal filters by
        end_date.
        """
        # Start with available unit
        self.unit.status = "available"
        self.unit.save(update_fields=["status"])

        # Create a stale-active lease (simulates the bug rows pre-fix)
        self.create_lease(
            unit=self.unit, status="active",
            start_date=self.today - timedelta(days=400),
            end_date=self.today - timedelta(days=1),
        )
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.status, "available")

    # ── Management command ─────────────────────────────────────────────── #

    def test_dry_run_makes_no_db_changes(self):
        lease = self.create_lease(
            unit=self.unit, status="active",
            start_date=self.today - timedelta(days=400),
            end_date=self.today - timedelta(days=2),
        )
        out = StringIO()
        call_command("expire_leases", "--dry-run", stdout=out)
        lease.refresh_from_db()
        self.assertEqual(lease.status, "active")
        self.assertIn("Would expire", out.getvalue())

    def test_command_real_run_expires_and_reports_count(self):
        self.create_lease(
            unit=self.unit, status="active",
            start_date=self.today - timedelta(days=400),
            end_date=self.today - timedelta(days=2),
        )
        out = StringIO()
        call_command("expire_leases", stdout=out)
        self.assertIn("Expired 1", out.getvalue())
