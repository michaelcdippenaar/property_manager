"""
Tests for push notification signal transition guards -- RNT-QUAL-061.

Verifies that push signals only fire when the status field genuinely
transitions (old != new), not on every save of an already-triggered record.

Run with:
    cd backend && pytest apps/notifications/tests/test_push_signals.py -v
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_user(email, role="agent"):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(email=email, password="x", role=role)


def _make_property(agent=None):
    from apps.properties.models import Property

    return Property.objects.create(
        name="Test Prop",
        address="1 Test St",
        city="Cape Town",
        province="WC",
        postal_code="8001",
        property_type="apartment",
        agent=agent,
    )


def _make_unit(prop):
    from apps.properties.models import Unit

    return Unit.objects.create(
        property=prop,
        unit_number="101",
        bedrooms=2,
        bathrooms=1,
        rent_amount=Decimal("8000.00"),
    )


def _make_lease(unit, status="active"):
    from apps.leases.models import Lease

    return Lease.objects.create(
        unit=unit,
        status=status,
        start_date="2024-01-01",
        end_date="2024-12-31",
        monthly_rent=Decimal("8000.00"),
    )


def _make_invoice(lease, status="paid"):
    from apps.payments.models import RentInvoice

    return RentInvoice.objects.create(
        lease=lease,
        amount_due=Decimal("8000.00"),
        period_start="2024-01-01",
        period_end="2024-01-31",
        due_date="2024-01-01",
        status=status,
    )


def _make_mandate(prop, status="active"):
    from apps.properties.models import RentalMandate

    return RentalMandate.objects.create(
        property=prop,
        mandate_type="full_management",
        commission_rate=Decimal("10.00"),
        start_date="2024-01-01",
        status=status,
    )


# ---------------------------------------------------------------------------
# RentInvoice: no push on non-transitional save
# ---------------------------------------------------------------------------


class TestRentInvoicePaidGuard:
    def test_no_push_when_already_paid_and_resaved(self):
        """Saving an already-paid invoice without changing status must NOT dispatch."""
        agent = _make_user("agent_inv@ex.com", role="agent")
        prop = _make_property(agent=agent)
        unit = _make_unit(prop)
        lease = _make_lease(unit, status="active")
        invoice = _make_invoice(lease, status="paid")

        push_path = "apps.notifications.services.push.send_push_to_user"
        with patch(push_path) as mock_push:
            invoice.save()
            assert mock_push.call_count == 0, (
                f"Expected 0 push calls on non-transitional save, got {mock_push.call_count}"
            )

    def test_push_fires_on_transition_to_paid(self):
        """Saving an invoice transitioning pending->paid MUST dispatch."""
        agent = _make_user("agent_inv2@ex.com", role="agent")
        prop = _make_property(agent=agent)
        unit = _make_unit(prop)
        lease = _make_lease(unit, status="active")
        invoice = _make_invoice(lease, status="pending")

        push_path = "apps.notifications.services.push.send_push_to_user"
        with patch(push_path) as mock_push:
            invoice.status = "paid"
            invoice.save()
            assert mock_push.call_count >= 1, (
                f"Expected at least 1 push call on paid transition, got {mock_push.call_count}"
            )


# ---------------------------------------------------------------------------
# Lease: no push on non-transitional save
# ---------------------------------------------------------------------------


class TestLeaseStatusGuard:
    def test_no_push_when_already_active_and_resaved(self):
        """Re-saving an active lease without status change must NOT dispatch."""
        agent = _make_user("agent_lease@ex.com", role="agent")
        prop = _make_property(agent=agent)
        unit = _make_unit(prop)
        lease = _make_lease(unit, status="active")

        push_path = "apps.notifications.services.push.send_push_to_user"
        with patch(push_path) as mock_push:
            lease.save()
            assert mock_push.call_count == 0, (
                f"Expected 0 push calls on non-transitional lease save, got {mock_push.call_count}"
            )

    def test_push_fires_on_transition_to_active(self):
        """Transitioning lease pending->active MUST dispatch."""
        agent = _make_user("agent_lease2@ex.com", role="agent")
        prop = _make_property(agent=agent)
        unit = _make_unit(prop)
        lease = _make_lease(unit, status="pending")

        push_path = "apps.notifications.services.push.send_push_to_user"
        with patch(push_path) as mock_push:
            lease.status = "active"
            lease.save()
            assert mock_push.call_count >= 1, (
                f"Expected at least 1 push call on active transition, got {mock_push.call_count}"
            )


# ---------------------------------------------------------------------------
# Mandate: no push on non-transitional save
# ---------------------------------------------------------------------------


class TestMandateStatusGuard:
    def test_no_push_when_already_active_and_resaved(self):
        """Re-saving an active mandate without status change must NOT dispatch."""
        agent = _make_user("agent_mand@ex.com", role="agent")
        prop = _make_property(agent=agent)
        mandate = _make_mandate(prop, status="active")

        push_path = "apps.notifications.services.push.send_push_to_user"
        with patch(push_path) as mock_push:
            mandate.save()
            assert mock_push.call_count == 0, (
                f"Expected 0 push calls on non-transitional mandate save, got {mock_push.call_count}"
            )

    def test_push_fires_on_transition_to_active(self):
        """Transitioning mandate draft->active MUST dispatch."""
        agent = _make_user("agent_mand2@ex.com", role="agent")
        prop = _make_property(agent=agent)
        mandate = _make_mandate(prop, status="draft")

        push_path = "apps.notifications.services.push.send_push_to_user"
        with patch(push_path) as mock_push:
            mandate.status = "active"
            mandate.save()
            assert mock_push.call_count >= 1, (
                f"Expected at least 1 push call on active mandate transition, got {mock_push.call_count}"
            )


# ---------------------------------------------------------------------------
# Maintenance: no push on non-transitional save
# ---------------------------------------------------------------------------


class TestMaintenanceStatusGuard:
    def test_no_push_when_already_resolved_and_resaved(self):
        """Re-saving an already-resolved maintenance request must NOT dispatch."""
        agent = _make_user("agent_maint@ex.com", role="agent")
        tenant_user = _make_user("tenant_maint@ex.com", role="tenant")
        prop = _make_property(agent=agent)
        unit = _make_unit(prop)

        from apps.maintenance.models import MaintenanceRequest

        req = MaintenanceRequest.objects.create(
            unit=unit,
            title="Leaking tap",
            status="resolved",
            priority="low",
            tenant=tenant_user,
        )

        push_path = "apps.notifications.services.push.send_push_to_user"
        with patch(push_path) as mock_push:
            req.save()
            assert mock_push.call_count == 0, (
                f"Expected 0 push calls on non-transitional maintenance save, got {mock_push.call_count}"
            )

    def test_push_fires_on_status_transition(self):
        """Transitioning maintenance request open->resolved MUST dispatch."""
        agent = _make_user("agent_maint2@ex.com", role="agent")
        tenant_user = _make_user("tenant_maint2@ex.com", role="tenant")
        prop = _make_property(agent=agent)
        unit = _make_unit(prop)

        from apps.maintenance.models import MaintenanceRequest

        req = MaintenanceRequest.objects.create(
            unit=unit,
            title="Leaking tap",
            status="open",
            priority="low",
            tenant=tenant_user,
        )

        push_path = "apps.notifications.services.push.send_push_to_user"
        with patch(push_path) as mock_push:
            req.status = "resolved"
            req.save()
            assert mock_push.call_count >= 1, (
                f"Expected at least 1 push call on resolved transition, got {mock_push.call_count}"
            )
