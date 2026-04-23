"""
RHA compliance gate tests — RNT-SEC-007.

Tests for rha_check.py logic, Lease model methods, and the
send-for-signing (esigning) gate.

Run with:
    pytest backend/apps/leases/tests/test_rha_gate.py -v
"""
from __future__ import annotations

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock


# ── rha_check module ──────────────────────────────────────────────────────
# Unit tests (no DB) have pytestmark=unit applied per-class below.
# Integration tests use pytest.mark.django_db directly.
# ──────────────────────────────────────────────────────────────────────── #

@pytest.mark.unit
class TestRhaCheckModule:
    """Unit tests for rha_check.run_rha_checks() — no DB required."""

    def _make_lease(self, **overrides):
        """
        Build a minimal Lease-like mock that passes all RHA checks by default,
        then apply *overrides* to trigger specific flags.
        """
        from apps.leases.models import LeaseEvent

        lease = MagicMock()
        lease.pk = 1
        lease.primary_tenant_id = 1
        lease.unit_id = 1
        lease.monthly_rent = Decimal("10000.00")
        lease.deposit = Decimal("10000.00")
        lease.start_date = date(2026, 1, 1)
        lease.end_date = date(2026, 12, 31)
        lease.notice_period_days = 30
        lease.rha_flags = []
        lease.rha_override = None

        # events queryset mock: return both inspection types
        events_qs = MagicMock()
        events_qs.values_list.return_value = [
            LeaseEvent.EventType.INSPECTION_IN,
            LeaseEvent.EventType.INSPECTION_OUT,
        ]
        lease.events = events_qs

        for key, value in overrides.items():
            setattr(lease, key, value)

        return lease

    def test_clean_lease_has_no_blocking_flags(self):
        """A fully-populated lease should have zero blocking flags."""
        from apps.leases.rha_check import run_rha_checks, blocking_flags
        lease = self._make_lease()
        flags = run_rha_checks(lease)
        assert len(blocking_flags(flags)) == 0

    def test_missing_primary_tenant_is_blocking(self):
        """Missing primary tenant → MISSING_PRIMARY_TENANT blocking flag."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease(primary_tenant_id=None)
        flags = run_rha_checks(lease)
        codes = [f["code"] for f in flags if f["severity"] == "blocking"]
        assert "MISSING_PRIMARY_TENANT" in codes

    def test_missing_unit_is_blocking(self):
        """Missing unit → MISSING_PREMISES blocking flag."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease(unit_id=None)
        flags = run_rha_checks(lease)
        codes = [f["code"] for f in flags if f["severity"] == "blocking"]
        assert "MISSING_PREMISES" in codes

    def test_zero_rent_is_blocking(self):
        """Zero monthly rent → MISSING_RENT blocking flag."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease(monthly_rent=Decimal("0.00"))
        flags = run_rha_checks(lease)
        codes = [f["code"] for f in flags if f["severity"] == "blocking"]
        assert "MISSING_RENT" in codes

    def test_missing_start_date_is_blocking(self):
        """Missing start date → MISSING_START_DATE blocking flag."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease(start_date=None)
        flags = run_rha_checks(lease)
        codes = [f["code"] for f in flags if f["severity"] == "blocking"]
        assert "MISSING_START_DATE" in codes

    def test_missing_end_date_is_blocking(self):
        """Missing end date → MISSING_END_DATE blocking flag."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease(end_date=None)
        flags = run_rha_checks(lease)
        codes = [f["code"] for f in flags if f["severity"] == "blocking"]
        assert "MISSING_END_DATE" in codes

    def test_end_before_start_is_blocking(self):
        """end_date <= start_date → END_BEFORE_START blocking flag."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease(
            start_date=date(2026, 6, 1),
            end_date=date(2026, 5, 1),
        )
        flags = run_rha_checks(lease)
        codes = [f["code"] for f in flags if f["severity"] == "blocking"]
        assert "END_BEFORE_START" in codes

    def test_deposit_exceeds_2x_rent_is_blocking(self):
        """Deposit > 2× rent → DEPOSIT_EXCEEDS_2X_RENT blocking flag (RHA s5(3)(g))."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease(
            monthly_rent=Decimal("5000.00"),
            deposit=Decimal("15000.00"),  # 3× rent
        )
        flags = run_rha_checks(lease)
        codes = [f["code"] for f in flags if f["severity"] == "blocking"]
        assert "DEPOSIT_EXCEEDS_2X_RENT" in codes

    def test_deposit_exactly_2x_rent_is_not_blocking(self):
        """Deposit == 2× rent → no DEPOSIT_EXCEEDS_2X_RENT flag."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease(
            monthly_rent=Decimal("5000.00"),
            deposit=Decimal("10000.00"),  # exactly 2×
        )
        flags = run_rha_checks(lease)
        codes = [f["code"] for f in flags if f["severity"] == "blocking"]
        assert "DEPOSIT_EXCEEDS_2X_RENT" not in codes

    def test_short_notice_period_is_blocking(self):
        """Notice period < 20 days → NOTICE_PERIOD_TOO_SHORT blocking flag."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease(notice_period_days=7)
        flags = run_rha_checks(lease)
        codes = [f["code"] for f in flags if f["severity"] == "blocking"]
        assert "NOTICE_PERIOD_TOO_SHORT" in codes

    def test_interest_bearing_reminder_is_advisory(self):
        """Deposit interest-bearing account check is always advisory."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease()
        flags = run_rha_checks(lease)
        advisory_codes = [f["code"] for f in flags if f["severity"] == "advisory"]
        assert "DEPOSIT_INTEREST_BEARING_REMINDER" in advisory_codes

    def test_pro_rata_advisory_when_start_not_first(self):
        """Start date not on 1st → PRO_RATA_FIRST_MONTH advisory flag."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease(start_date=date(2026, 1, 15))
        flags = run_rha_checks(lease)
        advisory_codes = [f["code"] for f in flags if f["severity"] == "advisory"]
        assert "PRO_RATA_FIRST_MONTH" in advisory_codes

    def test_missing_inspection_events_are_advisory(self):
        """No inspection events → advisory flags (not blocking)."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease()
        # Override events queryset to return nothing
        events_qs = MagicMock()
        events_qs.values_list.return_value = []
        lease.events = events_qs

        flags = run_rha_checks(lease)
        advisory_codes = [f["code"] for f in flags if f["severity"] == "advisory"]
        assert "MISSING_INSPECTION_IN_EVENT" in advisory_codes
        assert "MISSING_INSPECTION_OUT_EVENT" in advisory_codes

    def test_each_flag_has_required_keys(self):
        """Every flag must have code, section, severity, message, field."""
        from apps.leases.rha_check import run_rha_checks
        # Lease with several issues to generate multiple flags
        lease = self._make_lease(
            primary_tenant_id=None,
            deposit=Decimal("25000.00"),
        )
        flags = run_rha_checks(lease)
        assert len(flags) > 0
        for flag in flags:
            assert "code" in flag
            assert "section" in flag
            assert "severity" in flag
            assert "message" in flag
            assert "field" in flag
            assert flag["severity"] in ("blocking", "advisory")


# ── Lease model methods ───────────────────────────────────────────────── #

@pytest.mark.unit
class TestLeaseModelMethods:
    """Unit tests for Lease.assert_rha_ready() and record_rha_override()."""

    def _make_lease_instance(self, flags=None, override=None):
        """Minimal Lease instance without DB."""
        from apps.leases.models import Lease
        from django.db.models.base import ModelState
        lease = Lease.__new__(Lease)
        lease._state = ModelState()
        lease.rha_flags = flags if flags is not None else []
        lease.rha_override = override
        return lease

    def test_assert_rha_ready_passes_with_no_flags(self):
        """No flags → assert_rha_ready() raises nothing."""
        lease = self._make_lease_instance(flags=[])
        lease.assert_rha_ready()  # should not raise

    def test_assert_rha_ready_passes_with_only_advisory_flags(self):
        """Only advisory flags → assert_rha_ready() raises nothing."""
        lease = self._make_lease_instance(flags=[
            {"code": "ADVISORY_X", "severity": "advisory", "section": "RHA s5", "message": "reminder", "field": "deposit"},
        ])
        lease.assert_rha_ready()  # should not raise

    def test_assert_rha_ready_raises_when_blocking_flags_present(self):
        """Blocking flags → assert_rha_ready() raises ValueError."""
        lease = self._make_lease_instance(flags=[
            {"code": "MISSING_RENT", "severity": "blocking", "section": "RHA s5(3)(c)", "message": "No rent", "field": "monthly_rent"},
        ])
        with pytest.raises(ValueError, match="blocking"):
            lease.assert_rha_ready()

    def test_assert_rha_ready_passes_with_override_even_when_blocking(self):
        """If rha_override is recorded, assert_rha_ready() must not raise."""
        lease = self._make_lease_instance(
            flags=[{"code": "MISSING_RENT", "severity": "blocking", "section": "RHA s5(3)(c)", "message": "No rent", "field": "monthly_rent"}],
            override={"user_id": 1, "reason": "test override", "overridden_at": "2026-04-22T10:00:00Z", "flags_at_override": []},
        )
        lease.assert_rha_ready()  # should not raise

    def test_record_rha_override_requires_staff_or_agency_admin(self):
        """Non-staff non-agency_admin → record_rha_override raises PermissionError."""
        lease = self._make_lease_instance(flags=[
            {"code": "MISSING_RENT", "severity": "blocking", "section": "X", "message": "x", "field": "y"},
        ])
        user = MagicMock()
        user.role = "agent"
        user.is_staff = False
        user.is_superuser = False
        with pytest.raises(PermissionError):
            lease.record_rha_override(user, "test reason")

    def test_record_rha_override_requires_non_empty_reason(self):
        """Empty reason → record_rha_override raises ValueError."""
        lease = self._make_lease_instance(flags=[
            {"code": "MISSING_RENT", "severity": "blocking", "section": "X", "message": "x", "field": "y"},
        ])
        user = MagicMock()
        user.role = "agency_admin"
        user.is_staff = False
        user.is_superuser = False
        with pytest.raises(ValueError, match="reason"):
            lease.record_rha_override(user, "")

    def test_record_rha_override_requires_blocking_flags_to_be_present(self):
        """No blocking flags → record_rha_override raises ValueError (nothing to override)."""
        lease = self._make_lease_instance(flags=[])
        user = MagicMock()
        user.role = "admin"
        user.is_staff = True
        user.is_superuser = False
        with pytest.raises(ValueError, match="No blocking"):
            lease.record_rha_override(user, "I have a reason")

    def test_record_rha_override_persists_for_agency_admin(self):
        """agency_admin with blocking flags and reason → override is recorded."""
        from apps.leases.models import Lease
        from django.db.models.base import ModelState

        blocking = [{"code": "MISSING_RENT", "severity": "blocking", "section": "X", "message": "x", "field": "y"}]
        lease = self._make_lease_instance(flags=blocking)

        user = MagicMock()
        user.pk = 99
        user.email = "admin@klikk.co.za"
        user.role = "agency_admin"
        user.is_staff = False
        user.is_superuser = False

        # Patch save() so no DB call is made
        with patch.object(Lease, "save"):
            lease.record_rha_override(user, "Landlord confirmed verbal waiver")

        assert lease.rha_override is not None
        assert lease.rha_override["user_id"] == 99
        assert lease.rha_override["reason"] == "Landlord confirmed verbal waiver"
        assert "flags_at_override" in lease.rha_override
        assert len(lease.rha_override["flags_at_override"]) == 1

    def test_record_rha_override_persists_for_is_staff(self):
        """Django is_staff → may also override RHA flags."""
        from apps.leases.models import Lease

        blocking = [{"code": "MISSING_RENT", "severity": "blocking", "section": "X", "message": "x", "field": "y"}]
        lease = self._make_lease_instance(flags=blocking)

        user = MagicMock()
        user.pk = 1
        user.email = "superuser@klikk.co.za"
        user.role = "tenant"  # low role but is_staff=True
        user.is_staff = True
        user.is_superuser = False

        with patch.object(Lease, "save"):
            lease.record_rha_override(user, "Emergency bypass approved by MC")

        assert lease.rha_override is not None
        assert lease.rha_override["user_email"] == "superuser@klikk.co.za"


# ── RNT-015: escalation_clause / renewal_clause / domicilium_address ──── #

@pytest.mark.unit
class TestRhaMandatoryClauseFields:
    """
    Tests for RNT-015 — the three new RHA s5(3) mandatory clause fields.
    All tests are unit-level (no DB required).
    """

    def _make_lease(self, **overrides):
        """
        Build a fully-populated Lease mock that passes all RHA checks by default.
        All three new clause fields are pre-populated; pass empty string to trigger flags.
        """
        from apps.leases.models import LeaseEvent

        lease = MagicMock()
        lease.pk = 1
        lease.primary_tenant_id = 1
        lease.unit_id = 1
        lease.monthly_rent = Decimal("10000.00")
        lease.deposit = Decimal("10000.00")
        lease.start_date = date(2026, 1, 1)
        lease.end_date = date(2026, 12, 31)
        lease.notice_period_days = 30
        lease.rha_flags = []
        lease.rha_override = None

        # Populate the three new clause fields
        lease.escalation_clause = "Rent shall escalate annually at CPI + 2%."
        lease.renewal_clause = "Tenant may renew for a further 12-month period with 60 days written notice."
        lease.domicilium_address = "123 Test Street, Stellenbosch, 7600"

        # events queryset mock: return both inspection types
        events_qs = MagicMock()
        events_qs.values_list.return_value = [
            LeaseEvent.EventType.INSPECTION_IN,
            LeaseEvent.EventType.INSPECTION_OUT,
        ]
        lease.events = events_qs

        for key, value in overrides.items():
            setattr(lease, key, value)

        return lease

    # (a) All three blocking codes fire when the fields are empty ----------

    def test_missing_escalation_clause_is_blocking(self):
        """Empty escalation_clause → MISSING_ESCALATION_CLAUSE blocking flag."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease(escalation_clause="")
        flags = run_rha_checks(lease)
        codes = [f["code"] for f in flags if f["severity"] == "blocking"]
        assert "MISSING_ESCALATION_CLAUSE" in codes

    def test_missing_renewal_clause_is_blocking(self):
        """Empty renewal_clause → MISSING_RENEWAL_CLAUSE blocking flag."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease(renewal_clause="")
        flags = run_rha_checks(lease)
        codes = [f["code"] for f in flags if f["severity"] == "blocking"]
        assert "MISSING_RENEWAL_CLAUSE" in codes

    def test_missing_domicilium_is_blocking(self):
        """Empty domicilium_address → MISSING_DOMICILIUM blocking flag."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease(domicilium_address="")
        flags = run_rha_checks(lease)
        codes = [f["code"] for f in flags if f["severity"] == "blocking"]
        assert "MISSING_DOMICILIUM" in codes

    def test_all_three_blocking_codes_fire_on_empty_lease(self):
        """All three fields empty → all three blocking codes present."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease(
            escalation_clause="",
            renewal_clause="",
            domicilium_address="",
        )
        flags = run_rha_checks(lease)
        blocking_codes = {f["code"] for f in flags if f["severity"] == "blocking"}
        assert "MISSING_ESCALATION_CLAUSE" in blocking_codes
        assert "MISSING_RENEWAL_CLAUSE" in blocking_codes
        assert "MISSING_DOMICILIUM" in blocking_codes

    # (b) No new flags fire when all three are populated -------------------

    def test_no_new_clause_flags_when_all_three_populated(self):
        """All three fields populated → none of the three new blocking codes fire."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease()
        flags = run_rha_checks(lease)
        blocking_codes = {f["code"] for f in flags if f["severity"] == "blocking"}
        assert "MISSING_ESCALATION_CLAUSE" not in blocking_codes
        assert "MISSING_RENEWAL_CLAUSE" not in blocking_codes
        assert "MISSING_DOMICILIUM" not in blocking_codes

    def test_fully_populated_lease_has_zero_blocking_flags(self):
        """Fully-populated lease (including three new fields) → zero blocking flags."""
        from apps.leases.rha_check import run_rha_checks, blocking_flags
        lease = self._make_lease()
        flags = run_rha_checks(lease)
        assert len(blocking_flags(flags)) == 0

    # (c) Migration smoke-test: new fields default to empty string ---------

    def test_new_fields_default_to_empty_string(self):
        """
        Smoke-test that the three new model fields carry a default of "" (empty string).
        This ensures existing lease records are not broken by the migration.
        """
        from apps.leases.models import Lease
        from django.db.models.base import ModelState

        # Construct a bare Lease instance without saving to DB
        lease = Lease.__new__(Lease)
        lease._state = ModelState()

        # Simulate what the DB would return for pre-existing rows:
        # fields with default="" should produce empty strings, not raise AttributeError
        for field_name in ("escalation_clause", "renewal_clause", "domicilium_address"):
            field = Lease._meta.get_field(field_name)
            # The field's default must be empty string (falsy), not None
            default_value = field.default() if callable(field.default) else field.default
            assert default_value == "", (
                f"{field_name}.default should be '' (empty string), got {default_value!r}"
            )
            assert field.blank is True, f"{field_name}.blank should be True"

    def test_flag_structure_for_new_codes(self):
        """Each new blocking flag must carry the required keys and correct section."""
        from apps.leases.rha_check import run_rha_checks
        lease = self._make_lease(
            escalation_clause="",
            renewal_clause="",
            domicilium_address="",
        )
        flags = run_rha_checks(lease)
        new_codes = {
            "MISSING_ESCALATION_CLAUSE",
            "MISSING_RENEWAL_CLAUSE",
            "MISSING_DOMICILIUM",
        }
        new_flags = [f for f in flags if f["code"] in new_codes]
        assert len(new_flags) == 3, "Expected exactly 3 new blocking flags"
        for flag in new_flags:
            for key in ("code", "section", "severity", "message", "field"):
                assert key in flag, f"Flag missing key '{key}': {flag}"
            assert flag["severity"] == "blocking"
            assert "RHA" in flag["section"]


# ── View endpoint integration tests ──────────────────────────────────────
# RNT-SEC-024: verify that the rha-check and rha-override API endpoints
# return the correct response shape and enforce role-based access control.
# ──────────────────────────────────────────────────────────────────────── #

@pytest.mark.integration
@pytest.mark.django_db
class TestRhaCheckEndpoints:
    """
    Integration tests for:
      GET  /api/v1/leases/{id}/rha-check/
      POST /api/v1/leases/{id}/rha-override/

    Verifies:
    1. rha-check response keys are ``flags``, ``blocking``, ``advisory``,
       ``override`` (NOT ``rha_flags`` / ``rha_override`` — the mis-named keys
       that caused the frontend to silently see no flags in eed71cb).
    2. rha-override requires agency_admin or staff; tenant → 403.
    3. rha-override requires a non-empty reason; blank → 400.
    4. agency_admin can record a valid override.
    """

    def _make_db_lease(self, tc, *, with_blocking_flag=False, admin=None, tenant=None, agent_to_assign=None):
        """Create a minimal DB lease suitable for endpoint testing.

        If admin is provided, it will be assigned to the same agency as the lease's agent
        so it can access the lease (agency_admin scopes to properties managed by
        agents in their agency).

        If tenant is provided, it will be set as the primary_tenant so they can
        access the lease (tenants see leases where they're linked as primary/co/occupant).

        If agent_to_assign is provided, they will be assigned to the same property as
        the lease so they can see it (agents see properties where they're assigned).
        """
        from datetime import date, timedelta
        from decimal import Decimal
        from apps.accounts.models import Agency, Person
        from apps.properties.models import PropertyAgentAssignment

        # Create an agency for the lease's agent and admin
        agency = Agency.objects.create(
            name="Test RHA Agency",
            account_type=Agency.AccountType.AGENCY,
        )

        lease_agent = tc.create_agent(email="rha-agent@test.com", agency=agency)
        if admin:
            admin.agency = agency
            admin.save()

        # Create property with the lease's agent assigned
        prop = tc.create_property(agent=lease_agent)

        # If a test agent is provided, also assign them to the property
        if agent_to_assign:
            PropertyAgentAssignment.objects.create(
                property=prop,
                agent=agent_to_assign,
                status="active",
                assignment_type="managing",
            )

        unit = tc.create_unit(property_obj=prop)

        # If a tenant was provided, create a Person linked to them and set as primary_tenant
        primary_tenant_person = None
        if tenant:
            primary_tenant_person = Person.objects.create(
                full_name=f"Test Tenant {tenant.email}",
                linked_user=tenant,
            )

        kwargs = {
            "start_date": date.today(),
            "end_date": date.today() + timedelta(days=365),
            "monthly_rent": Decimal("8000.00"),
            "deposit": Decimal("16000.00"),
            "status": "pending",
            "notice_period_days": 30,
            "escalation_clause": "CPI-linked annual escalation.",
            "renewal_clause": "Renewable on mutual written agreement.",
            "domicilium_address": "1 Test Road, Stellenbosch, 7600",
        }
        if with_blocking_flag:
            # Introduce a blocking flag: rent = 0
            kwargs["monthly_rent"] = Decimal("0.00")
        return tc.create_lease(unit=unit, primary_tenant=primary_tenant_person, **kwargs)

    def test_rha_check_response_keys(self, tremly, api_client):
        """GET rha-check must return flags/blocking/advisory/override keys."""
        admin = tremly.create_user(
            email="admin-rha@test.com", role="agency_admin"
        )
        lease = self._make_db_lease(tremly, admin=admin)
        api_client.force_authenticate(user=admin)
        resp = api_client.get(f"/api/v1/leases/{lease.pk}/rha-check/")
        assert resp.status_code == 200
        data = resp.json()
        # These are the keys the frontend reads — they must exist
        assert "flags" in data, "Response must contain 'flags' key"
        assert "blocking" in data, "Response must contain 'blocking' key"
        assert "advisory" in data, "Response must contain 'advisory' key"
        assert "override" in data, "Response must contain 'override' key"
        # Must NOT contain the old mis-named keys
        assert "rha_flags" not in data, (
            "Response must NOT contain deprecated 'rha_flags' key — "
            "frontend reads 'flags' (RNT-SEC-024 fix)"
        )
        assert "rha_override" not in data, (
            "Response must NOT contain deprecated 'rha_override' key — "
            "frontend reads 'override' (RNT-SEC-024 fix)"
        )

    def test_rha_check_returns_blocking_for_incomplete_lease(self, tremly, api_client):
        """rha-check on a lease with zero rent returns at least one blocking flag."""
        admin = tremly.create_user(
            email="admin-blocking@test.com", role="agency_admin"
        )
        lease = self._make_db_lease(tremly, with_blocking_flag=True, admin=admin)
        api_client.force_authenticate(user=admin)
        resp = api_client.get(f"/api/v1/leases/{lease.pk}/rha-check/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["blocking"]) > 0, "Expected at least one blocking flag for zero-rent lease"

    def test_rha_override_tenant_is_rejected(self, tremly, api_client):
        """Tenant-role user → POST rha-override must return 403."""
        tenant = tremly.create_tenant(email="tenant-override@test.com")
        lease = self._make_db_lease(tremly, with_blocking_flag=True, tenant=tenant)
        api_client.force_authenticate(user=tenant)
        resp = api_client.post(
            f"/api/v1/leases/{lease.pk}/rha-override/",
            {"reason": "should be blocked"},
            format="json",
        )
        assert resp.status_code == 403, (
            f"Tenant must be rejected with 403 (got {resp.status_code})"
        )

    def test_rha_override_agent_is_rejected(self, tremly, api_client):
        """Agent (non-admin) role → POST rha-override must return 403."""
        agent = tremly.create_agent(email="agent-override@test.com")
        lease = self._make_db_lease(tremly, with_blocking_flag=True, agent_to_assign=agent)
        api_client.force_authenticate(user=agent)
        resp = api_client.post(
            f"/api/v1/leases/{lease.pk}/rha-override/",
            {"reason": "should be blocked"},
            format="json",
        )
        assert resp.status_code == 403, (
            f"Agent must be rejected with 403 (got {resp.status_code})"
        )

    def test_rha_override_empty_reason_rejected(self, tremly, api_client):
        """agency_admin with empty reason → 400."""
        admin = tremly.create_user(
            email="admin-empty-reason@test.com", role="agency_admin"
        )
        lease = self._make_db_lease(tremly, with_blocking_flag=True, admin=admin)
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            f"/api/v1/leases/{lease.pk}/rha-override/",
            {"reason": ""},
            format="json",
        )
        assert resp.status_code == 400

    def test_rha_override_agency_admin_succeeds(self, tremly, api_client):
        """agency_admin with blocking flags and a valid reason → 200, override recorded."""
        from decimal import Decimal

        admin = tremly.create_user(
            email="admin-override-ok@test.com", role="agency_admin"
        )
        lease = self._make_db_lease(tremly, with_blocking_flag=True, admin=admin)
        # Run a check first so rha_flags is populated
        lease.refresh_rha_flags()
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            f"/api/v1/leases/{lease.pk}/rha-override/",
            {"reason": "Landlord confirmed verbal waiver — proceeds at own risk"},
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        # Backend returns { detail, override } — verify correct key
        assert "override" in data, "rha-override response must contain 'override' key"
        assert data["override"]["reason"] == "Landlord confirmed verbal waiver — proceeds at own risk"
        assert "user_email" in data["override"]
        assert "overridden_at" in data["override"]

    def test_rha_override_response_key_is_override_not_rha_override(self, tremly, api_client):
        """
        POST rha-override must return 'override' key (not 'rha_override').
        This test pins the contract that the Vue submitOverride() function relies on
        (fixed in RNT-SEC-024 — eed71cb shipped with the wrong key name).
        """
        admin = tremly.create_user(
            email="admin-key-check@test.com", role="agency_admin"
        )
        lease = self._make_db_lease(tremly, with_blocking_flag=True, admin=admin)
        lease.refresh_rha_flags()
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            f"/api/v1/leases/{lease.pk}/rha-override/",
            {"reason": "Contract key shape test"},
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "override" in data, "Key must be 'override', not 'rha_override'"
        assert "rha_override" not in data, "Deprecated key 'rha_override' must not appear"
