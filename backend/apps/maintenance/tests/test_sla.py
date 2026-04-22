"""
SLA tests for MaintenanceRequest.

Tests:
  - sla_ack_deadline / sla_resolve_deadline computed correctly per priority
  - DEFAULT_SLA_HOURS fallback when no AgencySLAConfig exists
  - AgencySLAConfig overrides default hours
  - sla_ack_pct / sla_resolve_pct return expected range values
  - is_sla_overdue is True when deadline passed and ticket open
  - is_sla_overdue is False for resolved/closed tickets
  - escalate_overdue_maintenance marks sla_escalated=True
  - set_sla_deadlines signal fires on ticket creation
"""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone


@pytest.mark.django_db
class TestDefaultSLAHours:
    def test_urgent_defaults(self):
        from apps.maintenance.models import AgencySLAConfig, DEFAULT_SLA_HOURS
        ack_h, res_h = AgencySLAConfig.get_hours(None, "urgent")
        assert ack_h == DEFAULT_SLA_HOURS["urgent"][0]
        assert res_h == DEFAULT_SLA_HOURS["urgent"][1]

    def test_high_defaults(self):
        from apps.maintenance.models import AgencySLAConfig, DEFAULT_SLA_HOURS
        ack_h, res_h = AgencySLAConfig.get_hours(None, "high")
        assert ack_h == DEFAULT_SLA_HOURS["high"][0]
        assert res_h == DEFAULT_SLA_HOURS["high"][1]

    def test_medium_defaults(self):
        from apps.maintenance.models import AgencySLAConfig, DEFAULT_SLA_HOURS
        ack_h, res_h = AgencySLAConfig.get_hours(None, "medium")
        assert ack_h == DEFAULT_SLA_HOURS["medium"][0]
        assert res_h == DEFAULT_SLA_HOURS["medium"][1]

    def test_unknown_priority_fallback(self):
        from apps.maintenance.models import AgencySLAConfig
        ack_h, res_h = AgencySLAConfig.get_hours(None, "nonexistent")
        # Should fall back to (72, 336)
        assert ack_h == 72
        assert res_h == 336


@pytest.mark.django_db
class TestAgencySLAConfigOverride:
    def _make_agency(self):
        from apps.accounts.models import Agency
        return Agency.objects.create(name="Test Agency")

    def test_agency_override_used(self):
        from apps.maintenance.models import AgencySLAConfig
        agency = self._make_agency()
        AgencySLAConfig.objects.create(agency=agency, priority="urgent", ack_hours=2, resolve_hours=12)
        ack_h, res_h = AgencySLAConfig.get_hours(agency, "urgent")
        assert ack_h == 2
        assert res_h == 12

    def test_fallback_when_no_override(self):
        from apps.maintenance.models import AgencySLAConfig, DEFAULT_SLA_HOURS
        agency = self._make_agency()
        # No config for 'high'
        ack_h, res_h = AgencySLAConfig.get_hours(agency, "high")
        assert (ack_h, res_h) == DEFAULT_SLA_HOURS["high"]


@pytest.mark.django_db
class TestComputeSLADeadlines:
    def _make_request(self, priority="urgent"):
        from apps.accounts.models import User
        from apps.properties.models import Property, Unit
        from apps.maintenance.models import MaintenanceRequest

        user = User.objects.create_user(email=f"tenant_{priority}@test.com", password="x", role="tenant")
        prop = Property.objects.create(name="Test Prop", property_type="house")
        unit = Unit.objects.create(property=prop, unit_number="1", rent_amount=5000)
        return MaintenanceRequest.objects.create(
            unit=unit,
            tenant=user,
            title="Test issue",
            description="desc",
            priority=priority,
        )

    def test_deadlines_set_on_creation(self):
        from apps.maintenance.models import DEFAULT_SLA_HOURS
        ticket = self._make_request("urgent")
        ticket.refresh_from_db()
        assert ticket.sla_ack_deadline is not None
        assert ticket.sla_resolve_deadline is not None
        ack_h, res_h = DEFAULT_SLA_HOURS["urgent"]
        # Allow 5-second tolerance for test execution time
        expected_ack = ticket.created_at + timedelta(hours=ack_h)
        expected_res = ticket.created_at + timedelta(hours=res_h)
        assert abs((ticket.sla_ack_deadline - expected_ack).total_seconds()) < 5
        assert abs((ticket.sla_resolve_deadline - expected_res).total_seconds()) < 5

    def test_medium_priority_deadlines(self):
        from apps.maintenance.models import DEFAULT_SLA_HOURS
        ticket = self._make_request("medium")
        ticket.refresh_from_db()
        ack_h, res_h = DEFAULT_SLA_HOURS["medium"]
        expected_res = ticket.created_at + timedelta(hours=res_h)
        assert abs((ticket.sla_resolve_deadline - expected_res).total_seconds()) < 5


@pytest.mark.django_db
class TestSLAPercentage:
    def _make_request_with_deadline(self, resolve_deadline):
        from apps.accounts.models import User
        from apps.properties.models import Property, Unit
        from apps.maintenance.models import MaintenanceRequest

        user = User.objects.create_user(email=f"u_{resolve_deadline}@test.com", password="x", role="tenant")
        prop = Property.objects.create(name="Prop", property_type="house")
        unit = Unit.objects.create(property=prop, unit_number="1", rent_amount=5000)
        req = MaintenanceRequest.objects.create(
            unit=unit,
            tenant=user,
            title="Test",
            description="desc",
            priority="urgent",
        )
        # Manually set deadline for predictable pct
        MaintenanceRequest.objects.filter(pk=req.pk).update(
            sla_ack_deadline=resolve_deadline,
            sla_resolve_deadline=resolve_deadline,
        )
        req.refresh_from_db()
        return req

    def test_pct_is_none_for_resolved_ticket(self):
        from apps.maintenance.models import MaintenanceRequest
        future = timezone.now() + timedelta(hours=10)
        req = self._make_request_with_deadline(future)
        MaintenanceRequest.objects.filter(pk=req.pk).update(status="resolved")
        req.refresh_from_db()
        assert req.sla_resolve_pct is None

    def test_pct_positive_when_deadline_in_future(self):
        future = timezone.now() + timedelta(hours=10)
        req = self._make_request_with_deadline(future)
        pct = req.sla_resolve_pct
        assert pct is not None
        assert pct > 0

    def test_is_sla_overdue_true_when_past_deadline(self):
        past = timezone.now() - timedelta(hours=50)
        req = self._make_request_with_deadline(past)
        assert req.is_sla_overdue is True

    def test_is_sla_overdue_false_when_resolved(self):
        from apps.maintenance.models import MaintenanceRequest
        past = timezone.now() - timedelta(hours=50)
        req = self._make_request_with_deadline(past)
        MaintenanceRequest.objects.filter(pk=req.pk).update(status="resolved")
        req.refresh_from_db()
        assert req.is_sla_overdue is False

    def test_is_sla_overdue_false_when_future_deadline(self):
        future = timezone.now() + timedelta(hours=10)
        req = self._make_request_with_deadline(future)
        assert req.is_sla_overdue is False


@pytest.mark.django_db
class TestSLADeadlineRecomputeOnPriorityChange:
    """Ensure set_sla_deadlines recalculates when priority is changed on an existing ticket."""

    def test_priority_change_recalculates_deadlines(self):
        from apps.accounts.models import User
        from apps.properties.models import Property, Unit
        from apps.maintenance.models import MaintenanceRequest, DEFAULT_SLA_HOURS

        user = User.objects.create_user(email="prio_change@test.com", password="x", role="tenant")
        prop = Property.objects.create(name="Prio Prop", property_type="house")
        unit = Unit.objects.create(property=prop, unit_number="P1", rent_amount=5000)

        # Create urgent ticket — short deadlines
        ticket = MaintenanceRequest.objects.create(
            unit=unit,
            tenant=user,
            title="Priority change test",
            description="desc",
            priority="urgent",
        )
        ticket.refresh_from_db()
        urgent_resolve_deadline = ticket.sla_resolve_deadline
        assert urgent_resolve_deadline is not None

        # Change to medium — deadline should now be much later (336h vs 24h)
        ticket.priority = "medium"
        ticket.save()
        ticket.refresh_from_db()

        medium_resolve_h = DEFAULT_SLA_HOURS["medium"][1]
        assert ticket.sla_resolve_deadline > urgent_resolve_deadline, (
            "Deadline should extend when priority is downgraded from urgent to medium"
        )
        # Rough sanity: medium resolve should be ~336h from created_at
        expected_medium_res = ticket.created_at + timedelta(hours=medium_resolve_h)
        assert abs((ticket.sla_resolve_deadline - expected_medium_res).total_seconds()) < 5


@pytest.mark.django_db
class TestEscalateTask:
    def test_escalates_overdue_tickets(self):
        from apps.accounts.models import User
        from apps.properties.models import Property, Unit
        from apps.maintenance.models import MaintenanceRequest
        from apps.maintenance.tasks import escalate_overdue_maintenance

        admin = User.objects.create_user(email="admin@test.com", password="x", role="agency_admin")
        user = User.objects.create_user(email="tenant_esc@test.com", password="x", role="tenant")
        prop = Property.objects.create(name="Esc Prop", property_type="house")
        unit = Unit.objects.create(property=prop, unit_number="E1", rent_amount=5000)
        req = MaintenanceRequest.objects.create(
            unit=unit,
            tenant=user,
            title="Overdue ticket",
            description="desc",
            priority="urgent",
        )
        # Set deadline >48h in the past
        past = timezone.now() - timedelta(hours=60)
        MaintenanceRequest.objects.filter(pk=req.pk).update(
            sla_resolve_deadline=past,
            sla_escalated=False,
        )

        with patch("django.core.mail.send_mail") as mock_mail:
            count = escalate_overdue_maintenance()

        req.refresh_from_db()
        assert req.sla_escalated is True
        assert count >= 1
        mock_mail.assert_called_once()

    def test_does_not_re_escalate(self):
        from apps.accounts.models import User
        from apps.properties.models import Property, Unit
        from apps.maintenance.models import MaintenanceRequest
        from apps.maintenance.tasks import escalate_overdue_maintenance

        user = User.objects.create_user(email="tenant_re@test.com", password="x", role="tenant")
        prop = Property.objects.create(name="Re-esc Prop", property_type="house")
        unit = Unit.objects.create(property=prop, unit_number="R1", rent_amount=5000)
        req = MaintenanceRequest.objects.create(
            unit=unit, tenant=user, title="Already escalated", description="desc", priority="urgent",
        )
        past = timezone.now() - timedelta(hours=60)
        MaintenanceRequest.objects.filter(pk=req.pk).update(
            sla_resolve_deadline=past,
            sla_escalated=True,  # already done
        )

        with patch("django.core.mail.send_mail") as mock_mail:
            count = escalate_overdue_maintenance()

        mock_mail.assert_not_called()
