"""Regression: company-landlord create → retrieve roundtrip.

Guards against the bug class where the create endpoint silently drops the
company-entity fields (registration_number, vat_number, representative_*)
or the retrieve endpoint fails to surface them on the detail page.
"""
import pytest

from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.integration]


class LandlordCreateRetrieveRoundtripTest(TremlyAPITestCase):
    def setUp(self):
        self.admin = self.create_admin()
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
