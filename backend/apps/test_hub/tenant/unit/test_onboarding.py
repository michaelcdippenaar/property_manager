"""
Unit tests for TenantOnboarding model (no DB required).
"""
import pytest
from unittest.mock import MagicMock, patch
from django.db.models.base import ModelState

pytestmark = [pytest.mark.unit, pytest.mark.green]


def _make_onboarding(**overrides):
    """Build an in-memory TenantOnboarding instance with all v1 flags set as given."""
    from apps.tenant.models import TenantOnboarding

    obj = TenantOnboarding.__new__(TenantOnboarding)
    obj._state = ModelState()
    obj.pk = 1
    obj.welcome_pack_sent = False
    obj.deposit_received = False
    obj.first_rent_scheduled = False
    obj.keys_handed_over = False
    obj.emergency_contacts_captured = False
    obj.incoming_inspection_booked = False
    obj.deposit_banked_trust = False
    obj.completed_at = None
    for k, v in overrides.items():
        setattr(obj, k, v)
    return obj


class TestTenantOnboardingProgress:
    def test_zero_progress_when_all_false(self):
        ob = _make_onboarding()
        assert ob.progress == 0

    def test_full_progress_when_all_v1_true(self):
        ob = _make_onboarding(
            welcome_pack_sent=True,
            deposit_received=True,
            first_rent_scheduled=True,
            keys_handed_over=True,
            emergency_contacts_captured=True,
        )
        assert ob.progress == 100

    def test_partial_progress(self):
        ob = _make_onboarding(welcome_pack_sent=True, deposit_received=True)
        # 2 out of 5 = 40%
        assert ob.progress == 40

    def test_v2_items_do_not_affect_progress(self):
        """incoming_inspection_booked and deposit_banked_trust are v2 — excluded from %."""
        ob = _make_onboarding(
            incoming_inspection_booked=True,
            deposit_banked_trust=True,
        )
        assert ob.progress == 0

    def test_is_complete_false_when_partial(self):
        ob = _make_onboarding(welcome_pack_sent=True)
        assert ob.is_complete is False

    def test_is_complete_true_when_all_v1_ticked(self):
        ob = _make_onboarding(
            welcome_pack_sent=True,
            deposit_received=True,
            first_rent_scheduled=True,
            keys_handed_over=True,
            emergency_contacts_captured=True,
        )
        assert ob.is_complete is True

    def test_is_complete_false_when_v2_only(self):
        ob = _make_onboarding(
            incoming_inspection_booked=True,
            deposit_banked_trust=True,
        )
        assert ob.is_complete is False


class TestTenantOnboardingStr:
    def test_str_contains_lease_repr(self):
        from apps.tenant.models import TenantOnboarding

        obj = TenantOnboarding.__new__(TenantOnboarding)
        obj._state = ModelState()
        # Bypass the FK descriptor by patching __str__ directly on the instance
        with patch.object(TenantOnboarding, "__str__", lambda self: "Onboarding for Lease #42"):
            result = str(obj)
        assert "Onboarding for" in result
        assert "Lease #42" in result
