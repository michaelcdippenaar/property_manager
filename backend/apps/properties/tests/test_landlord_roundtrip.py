"""Regression: company-landlord create → retrieve roundtrip.

Guards against the bug class where the create endpoint silently drops the
company-entity fields (registration_number, vat_number, representative_*)
or the retrieve endpoint fails to surface them on the detail page.
"""
import pytest

from apps.accounts.models import Agency
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration]


class LandlordCreateRetrieveRoundtripTest(TremlyAPITestCase):
    def setUp(self):
        self.agency = Agency.objects.create(name="Klikk Properties")
        self.admin = self.create_admin()
        # Admin needs an agency to create via the AgencyStampedCreateMixin
        # (the mixin requires admins to have either an own agency_id or pass
        # `agency` in the payload — see apps/accounts/scoping.py).
        self.admin.agency = self.agency
        self.admin.save(update_fields=["agency"])
        self.authenticate(self.admin)

    def test_create_company_then_retrieve_returns_all_fields(self):
        payload = {
            "name": "Klikk Pty Ltd",
            "landlord_type": "company",
            "registration_number": "2018/123456/07",
            "vat_number": "4501234567",
            "email": "owner@klikk.co.za",
            "phone": "0823068144",
            "representative_name": "MC Dippenaar",
            "representative_email": "mc@klikk.co.za",
            "representative_phone": "0823068144",
        }

        # Create
        resp = self.client.post("/api/v1/properties/landlords/", payload, format="json")
        assert resp.status_code == 201, resp.content
        ll_id = resp.data["id"]

        # Retrieve
        resp = self.client.get(f"/api/v1/properties/landlords/{ll_id}/")
        assert resp.status_code == 200, resp.content

        # Every company field MC entered must round-trip back to the detail view.
        for k, v in payload.items():
            assert resp.data.get(k) == v, f"Field {k}: expected {v!r}, got {resp.data.get(k)!r}"

        # Detail-view extras: empty defaults rather than KeyError.
        assert resp.data.get("bank_accounts") == []
        assert resp.data.get("properties") == []
        assert resp.data.get("address") in ({}, None)
        assert resp.data.get("classification_data") is None


class LandlordOrphanRetrieveAsAgencyAdminTest(TremlyAPITestCase):
    """Regression: a freshly-registered agency_admin must be able to fetch
    the detail view of a landlord they just created — BEFORE any property
    has been linked to it.

    Bug class: LandlordViewSet.get_queryset() restricted non-admin users to
    landlords that had `ownerships__property_id__in=accessible_property_ids`.
    Newly-created landlords have zero ownerships, so the filter returned
    nothing → DRF's get_object() raised Http404 with the message
    "No Landlord matches the given query." MC hit this on the first run
    through a fresh agency during the multi-tenant E2E walkthrough.

    Admin users never tripped on this because the admin branch already
    included Q(ownerships__isnull=True). The fix unifies the two branches.
    """

    def setUp(self):
        self.agency = Agency.objects.create(name="Fresh Agency")
        self.user = self.create_user(
            email="boss@fresh.test",
            role="agency_admin",
            agency=self.agency,
        )
        self.authenticate(self.user)

    def test_orphan_landlord_is_retrievable_immediately_after_create(self):
        # Create — no properties exist, no ownership will be linked.
        resp = self.client.post(
            "/api/v1/properties/landlords/",
            {
                "name": "Brand-new Owner (Pty) Ltd",
                "landlord_type": "company",
                "email": "brand@new.test",
            },
            format="json",
        )
        assert resp.status_code == 201, resp.content
        ll_id = resp.data["id"]

        # Retrieve — must succeed despite zero ownerships.
        resp = self.client.get(f"/api/v1/properties/landlords/{ll_id}/")
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}. "
            f"Body: {resp.content!r}. This regression means an agency_admin "
            f"can't see a landlord they just created before attaching a property."
        )
        assert resp.data["name"] == "Brand-new Owner (Pty) Ltd"
        assert resp.data.get("properties") == []
        assert resp.data.get("property_count") == 0
