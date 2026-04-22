"""
Tier enforcement tests — OPS-007.

Run with:
    pytest backend/apps/accounts/tests/test_tier_enforcement.py
"""
import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Agency
from apps.accounts.tier_service import SubscriptionTier, sync_tiers, TierService, QuotaStatus


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _make_agency(name="Test Agency", tier_slug=None):
    """Create an Agency, optionally assigning a tier."""
    agency = Agency.objects.create(name=name)
    if tier_slug:
        tier = SubscriptionTier.objects.filter(slug=tier_slug).first()
        if tier:
            agency.subscription_tier = tier
            agency.save(update_fields=["subscription_tier"])
    return agency


def _make_user(email, role=User.Role.AGENCY_ADMIN, agency=None, password="pass"):
    user = User.objects.create_user(email=email, password=password, role=role)
    if agency:
        user.agency = agency
        user.save(update_fields=["agency"])
    return user


# ─────────────────────────────────────────────────────────────────
# SubscriptionTier model + sync
# ─────────────────────────────────────────────────────────────────

class TestSyncTiers(TestCase):
    def test_sync_creates_all_tiers(self):
        """sync_tiers() must create free / pro / enterprise / custom rows."""
        from apps.accounts.tier_service import load_pricing_config
        load_pricing_config.cache_clear()
        sync_tiers()
        slugs = set(SubscriptionTier.objects.values_list("slug", flat=True))
        self.assertIn("free", slugs)
        self.assertIn("pro", slugs)
        self.assertIn("enterprise", slugs)

    def test_sync_is_idempotent(self):
        """Running sync_tiers() twice does not duplicate rows."""
        load_pricing_config = __import__(
            "apps.accounts.tier_service", fromlist=["load_pricing_config"]
        ).load_pricing_config
        load_pricing_config.cache_clear()
        sync_tiers()
        count_first = SubscriptionTier.objects.count()
        sync_tiers()
        count_second = SubscriptionTier.objects.count()
        self.assertEqual(count_first, count_second)

    def test_pro_tier_has_ai_lease_generation(self):
        from apps.accounts.tier_service import load_pricing_config
        load_pricing_config.cache_clear()
        sync_tiers()
        pro = SubscriptionTier.objects.get(slug="pro")
        self.assertTrue(pro.has_feature("ai_lease_generation"))
        self.assertTrue(pro.has_feature("e_signing"))
        self.assertTrue(pro.has_feature("api_access"))

    def test_free_tier_flags(self):
        from apps.accounts.tier_service import load_pricing_config
        load_pricing_config.cache_clear()
        sync_tiers()
        free = SubscriptionTier.objects.get(slug="free")
        # Free has 2 AI contracts/year — feature flag True, quota enforced separately
        self.assertTrue(free.has_feature("ai_lease_generation"))
        # Free does not have e-signing
        self.assertFalse(free.has_feature("e_signing"))
        # Free does not have API access
        self.assertFalse(free.has_feature("api_access"))


# ─────────────────────────────────────────────────────────────────
# Agency.has_feature() helper
# ─────────────────────────────────────────────────────────────────

class TestAgencyHasFeature(TestCase):
    def setUp(self):
        from apps.accounts.tier_service import load_pricing_config
        load_pricing_config.cache_clear()
        sync_tiers()

    def test_agency_without_tier_gets_all_features(self):
        """Backwards compat: no tier → all features accessible."""
        agency = _make_agency("No Tier Agency", tier_slug=None)
        self.assertTrue(agency.has_feature("ai_lease_generation"))
        self.assertTrue(agency.has_feature("e_signing"))

    def test_agency_on_free_tier_no_e_signing(self):
        agency = _make_agency("Free Agency", tier_slug="free")
        self.assertFalse(agency.has_feature("e_signing"))

    def test_agency_on_pro_tier_has_e_signing(self):
        agency = _make_agency("Pro Agency", tier_slug="pro")
        self.assertTrue(agency.has_feature("e_signing"))


# ─────────────────────────────────────────────────────────────────
# TierService
# ─────────────────────────────────────────────────────────────────

class TestTierService(TestCase):
    def setUp(self):
        from apps.accounts.tier_service import load_pricing_config
        load_pricing_config.cache_clear()
        sync_tiers()

    def test_has_feature_no_agency(self):
        """TierService with None agency falls back to True (safe default)."""
        svc = TierService(None)
        self.assertTrue(svc.has_feature("ai_lease_generation"))

    def test_has_feature_pro_tier(self):
        agency = _make_agency("Pro", tier_slug="pro")
        svc = TierService(agency)
        self.assertTrue(svc.has_feature("ai_lease_generation"))
        self.assertTrue(svc.has_feature("api_access"))

    def test_quota_statuses_returns_list(self):
        agency = _make_agency("Quota Agency", tier_slug="pro")
        svc = TierService(agency)
        statuses = svc.quota_statuses()
        self.assertIsInstance(statuses, list)
        keys = {qs.key for qs in statuses}
        self.assertIn("properties", keys)
        self.assertIn("users", keys)

    def test_quota_warning_threshold(self):
        qs = QuotaStatus("properties", used=4, limit=5)
        self.assertTrue(qs.warning)
        self.assertFalse(qs.blocked)

    def test_quota_blocked_threshold(self):
        qs = QuotaStatus("properties", used=5, limit=5)
        self.assertFalse(qs.warning)
        self.assertTrue(qs.blocked)

    def test_quota_unlimited(self):
        qs = QuotaStatus("properties", used=9999, limit=None)
        self.assertTrue(qs.is_unlimited)
        self.assertFalse(qs.warning)
        self.assertFalse(qs.blocked)

    def test_tier_info_shape(self):
        agency = _make_agency("Info", tier_slug="pro")
        svc = TierService(agency)
        info = svc.tier_info()
        self.assertIn("tier", info)
        self.assertIn("quotas", info)
        self.assertIn("upgrade_url", info)
        self.assertIn("all_tiers", info)


# ─────────────────────────────────────────────────────────────────
# @requires_feature decorator via HTTP
# ─────────────────────────────────────────────────────────────────

class TestRequiresFeatureDecorator(TestCase):
    """
    Smoke-test the decorator by calling the lease builder session endpoint.
    Free tier with ai_contracts_yearly=2 still has feature=True, so we test
    with a custom tier that has e_signing=False and then check the decorator
    on a view that requires e_signing.

    Since we don't have a built-in view gated by e_signing yet, we test
    the decorator unit-level.
    """
    def setUp(self):
        from apps.accounts.tier_service import load_pricing_config
        load_pricing_config.cache_clear()
        sync_tiers()
        self.agency = _make_agency("Test", tier_slug="free")
        self.user = _make_user("test@tier.com", role=User.Role.AGENCY_ADMIN, agency=self.agency)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _make_authenticated_request(self, user):
        """Return a DRF Request with a properly force-authenticated user."""
        from rest_framework.test import APIRequestFactory
        from rest_framework.request import Request as DRFRequest
        factory = APIRequestFactory()
        raw = factory.post("/fake/")
        # _force_auth_user must be on the raw request BEFORE DRFRequest wraps it.
        raw._force_auth_user = user
        return DRFRequest(raw)

    def test_feature_blocked_returns_402(self):
        """
        A tier that does NOT have a feature should return HTTP 402.
        Free tier has e_signing=False.
        """
        from apps.accounts.decorators import requires_feature

        drf_request = self._make_authenticated_request(self.user)

        class FakeView:
            @requires_feature("e_signing")
            def post(self, request):
                return "reached"

        view = FakeView()
        result = view.post(drf_request)
        # Free tier has e_signing=False → 402
        self.assertEqual(result.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertIn("upgrade_required", result.data)
        self.assertEqual(result.data["feature"], "e_signing")

    def test_feature_allowed_passes_through(self):
        """A feature the tier has → decorator does not intercept."""
        from apps.accounts.decorators import requires_feature

        drf_request = self._make_authenticated_request(self.user)

        class FakeView:
            @requires_feature("ai_lease_generation")
            def post(self, request):
                return "reached"

        view = FakeView()
        result = view.post(drf_request)
        # Free tier allows ai_lease_generation (quota-limited, but feature is on)
        self.assertEqual(result, "reached")


# ─────────────────────────────────────────────────────────────────
# Billing API endpoint
# ─────────────────────────────────────────────────────────────────

class TestBillingEndpoint(TestCase):
    def setUp(self):
        from apps.accounts.tier_service import load_pricing_config
        load_pricing_config.cache_clear()
        sync_tiers()
        self.agency = _make_agency("API Test Agency", tier_slug="pro")
        self.admin = _make_user("admin@billing.com", role=User.Role.ADMIN, agency=self.agency)
        self.agent = _make_user("agent@billing.com", role=User.Role.AGENT, agency=self.agency)
        self.client = APIClient()

    def test_admin_can_get_billing(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/api/v1/auth/agency/billing/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("tier", resp.data)
        self.assertIn("quotas", resp.data)

    def test_agent_cannot_get_billing(self):
        """Regular agents are not admin/agency_admin — should be 403."""
        self.client.force_authenticate(user=self.agent)
        resp = self.client.get("/api/v1/auth/agency/billing/")
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_patch_tier(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            "/api/v1/auth/agency/billing/",
            {"subscription_tier": "enterprise"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.agency.refresh_from_db()
        self.assertEqual(self.agency.subscription_tier.slug, "enterprise")

    def test_patch_invalid_tier_returns_400(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            "/api/v1/auth/agency/billing/",
            {"subscription_tier": "nonexistent"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
