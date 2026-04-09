"""
Unit tests for apps/maintenance/supplier_serializers.py.

Source file under test: apps/maintenance/supplier_serializers.py

Covers the six serializers used by the supplier portal:
  - SupplierTradeSerializer          — label comes from get_trade_display()
  - SupplierDocumentSerializer       — type_label, read-only id/uploaded_at
  - SupplierProfileSerializer        — trade_codes write-only, excludes ai_profile
                                        and linked_user, update() replaces trades
  - SupplierJobQuoteSerializer       — straight passthrough
  - SupplierJobSerializer            — property_city/name fall back to "" when
                                        the relation chain is broken
  - SupplierCalendarItemSerializer   — plain Serializer (no model)

All tests hit the DB via TremlyAPITestCase factories but do not touch the HTTP layer.
"""
from datetime import date
from decimal import Decimal

import pytest

from apps.maintenance.models import (
    JobDispatch, JobQuote, JobQuoteRequest, Supplier, SupplierDocument,
    SupplierTrade,
)
from apps.maintenance.supplier_serializers import (
    SupplierCalendarItemSerializer,
    SupplierDocumentSerializer,
    SupplierJobQuoteSerializer,
    SupplierJobSerializer,
    SupplierProfileSerializer,
    SupplierTradeSerializer,
)
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.unit, pytest.mark.green]


# ─────────────────────────────────────────────────────────────────────────────
# SupplierTradeSerializer
# ─────────────────────────────────────────────────────────────────────────────
class SupplierTradeSerializerTests(TremlyAPITestCase):
    def test_label_uses_display_name(self):
        supplier = self.create_supplier(name="Acme")
        trade = SupplierTrade.objects.create(supplier=supplier, trade="plumbing")

        data = SupplierTradeSerializer(trade).data
        self.assertEqual(data["trade"], "plumbing")
        self.assertEqual(data["label"], "Plumbing")
        self.assertIn("id", data)

    def test_label_is_read_only(self):
        """``label`` comes from get_trade_display and can never be written."""
        supplier = self.create_supplier(name="ReadOnly Co")
        ser = SupplierTradeSerializer(
            data={"trade": "electrical", "label": "HACKED", "supplier": supplier.pk},
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        # label is not a model field — it cannot end up in validated_data
        self.assertNotIn("label", ser.validated_data)


# ─────────────────────────────────────────────────────────────────────────────
# SupplierDocumentSerializer
# ─────────────────────────────────────────────────────────────────────────────
class SupplierDocumentSerializerTests(TremlyAPITestCase):
    def test_type_label_resolved_from_choices(self):
        supplier = self.create_supplier(name="DocCo")
        doc = SupplierDocument.objects.create(
            supplier=supplier,
            document_type="bee_certificate",
            file="supplier_documents/bee.pdf",
            description="2026 certificate",
        )
        data = SupplierDocumentSerializer(doc).data
        self.assertEqual(data["document_type"], "bee_certificate")
        self.assertEqual(data["type_label"], "BEE Certificate")
        self.assertEqual(data["description"], "2026 certificate")

    def test_id_and_uploaded_at_are_read_only(self):
        fields = SupplierDocumentSerializer.Meta.read_only_fields
        self.assertIn("id", fields)
        self.assertIn("uploaded_at", fields)


# ─────────────────────────────────────────────────────────────────────────────
# SupplierProfileSerializer
# ─────────────────────────────────────────────────────────────────────────────
class SupplierProfileSerializerTests(TremlyAPITestCase):
    def test_excluded_fields_never_appear(self):
        supplier = self.create_supplier(name="Secret Co", ai_profile={"hot": "data"})
        data = SupplierProfileSerializer(supplier).data
        self.assertNotIn("ai_profile", data)
        self.assertNotIn("linked_user", data)

    def test_trades_serialized_nested(self):
        supplier = self.create_supplier(name="Multi Trade")
        SupplierTrade.objects.create(supplier=supplier, trade="plumbing")
        SupplierTrade.objects.create(supplier=supplier, trade="electrical")

        data = SupplierProfileSerializer(supplier).data
        trade_codes = sorted(t["trade"] for t in data["trades"])
        self.assertEqual(trade_codes, ["electrical", "plumbing"])

    def test_update_replaces_trade_set(self):
        supplier = self.create_supplier(name="Swap Trades")
        SupplierTrade.objects.create(supplier=supplier, trade="plumbing")
        SupplierTrade.objects.create(supplier=supplier, trade="hvac")

        ser = SupplierProfileSerializer(
            supplier,
            data={"trade_codes": ["electrical", "roofing"]},
            partial=True,
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        ser.save()

        codes = sorted(supplier.trades.values_list("trade", flat=True))
        self.assertEqual(codes, ["electrical", "roofing"])

    def test_update_without_trade_codes_leaves_trades_alone(self):
        """If trade_codes is omitted, existing trades are NOT wiped."""
        supplier = self.create_supplier(name="Keeper")
        SupplierTrade.objects.create(supplier=supplier, trade="plumbing")

        ser = SupplierProfileSerializer(
            supplier, data={"notes": "updated"}, partial=True,
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        ser.save()

        codes = list(supplier.trades.values_list("trade", flat=True))
        self.assertEqual(codes, ["plumbing"])

    def test_trade_codes_is_write_only(self):
        supplier = self.create_supplier(name="WriteOnlyProbe")
        data = SupplierProfileSerializer(supplier).data
        # trade_codes is write_only — never in serialized output
        self.assertNotIn("trade_codes", data)

    def test_invalid_trade_code_rejected(self):
        supplier = self.create_supplier(name="Validator")
        ser = SupplierProfileSerializer(
            supplier, data={"trade_codes": ["not-a-trade"]}, partial=True,
        )
        self.assertFalse(ser.is_valid())
        self.assertIn("trade_codes", ser.errors)

    def test_rating_is_read_only(self):
        supplier = self.create_supplier(name="Rated")
        supplier.rating = Decimal("4.5")
        supplier.save()
        ser = SupplierProfileSerializer(
            supplier, data={"rating": "1.0"}, partial=True,
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        ser.save()
        supplier.refresh_from_db()
        # Rating must stay at 4.5 — write attempt ignored
        self.assertEqual(supplier.rating, Decimal("4.5"))


# ─────────────────────────────────────────────────────────────────────────────
# SupplierJobQuoteSerializer
# ─────────────────────────────────────────────────────────────────────────────
class SupplierJobQuoteSerializerTests(TremlyAPITestCase):
    def _make_quote_request(self):
        unit = self.create_unit()
        tenant = self.create_tenant(email=f"q-tenant-{JobQuoteRequest.objects.count()}@jq.test")
        mr = self.create_maintenance_request(unit=unit, tenant=tenant)
        dispatch = JobDispatch.objects.create(maintenance_request=mr)
        supplier = self.create_supplier(name="Quoter")
        return JobQuoteRequest.objects.create(dispatch=dispatch, supplier=supplier)

    def test_basic_round_trip(self):
        qr = self._make_quote_request()
        quote = JobQuote.objects.create(
            quote_request=qr,
            amount=Decimal("2500.00"),
            description="Replace tap washer",
            estimated_days=1,
            available_from=date(2026, 5, 1),
        )
        data = SupplierJobQuoteSerializer(quote).data
        self.assertEqual(data["amount"], "2500.00")
        self.assertEqual(data["description"], "Replace tap washer")
        self.assertEqual(data["estimated_days"], 1)
        self.assertEqual(data["available_from"], "2026-05-01")
        self.assertIn("submitted_at", data)

    def test_id_and_submitted_at_are_read_only(self):
        fields = SupplierJobQuoteSerializer.Meta.read_only_fields
        self.assertIn("id", fields)
        self.assertIn("submitted_at", fields)


# ─────────────────────────────────────────────────────────────────────────────
# SupplierJobSerializer
# ─────────────────────────────────────────────────────────────────────────────
class SupplierJobSerializerTests(TremlyAPITestCase):
    def _setup(self, property_name="Oak Grove", property_city="Cape Town"):
        prop = self.create_property(name=property_name, city=property_city)
        unit = self.create_unit(property_obj=prop, unit_number="U1")
        tenant = self.create_tenant(
            email=f"sj-tenant-{JobQuoteRequest.objects.count()}@sj.test"
        )
        mr = self.create_maintenance_request(
            unit=unit,
            tenant=tenant,
            title="Leaky tap",
            description="Kitchen tap drips",
            priority="high",
        )
        dispatch = JobDispatch.objects.create(
            maintenance_request=mr, notes="Bring spare washers",
        )
        supplier = self.create_supplier(name="Looker")
        return JobQuoteRequest.objects.create(
            dispatch=dispatch, supplier=supplier, match_score=Decimal("82.50"),
        )

    def test_flattens_job_fields(self):
        qr = self._setup()
        data = SupplierJobSerializer(qr).data
        self.assertEqual(data["job_title"], "Leaky tap")
        self.assertEqual(data["job_description"], "Kitchen tap drips")
        self.assertEqual(data["job_priority"], "high")
        self.assertEqual(data["dispatch_notes"], "Bring spare washers")
        self.assertEqual(data["property_name"], "Oak Grove")
        self.assertEqual(data["property_city"], "Cape Town")
        self.assertEqual(data["match_score"], "82.50")

    def test_property_accessors_default_to_empty_string_on_error(self):
        """When the unit/property chain raises AttributeError, both getters return ''."""
        class BrokenMR:
            @property
            def unit(self):
                raise AttributeError("missing unit")

        class BrokenDispatch:
            maintenance_request = BrokenMR()

        class BrokenQR:
            dispatch = BrokenDispatch()

        ser = SupplierJobSerializer()
        self.assertEqual(ser.get_property_city(BrokenQR()), "")
        self.assertEqual(ser.get_property_name(BrokenQR()), "")

    def test_quote_nested_when_present(self):
        qr = self._setup()
        JobQuote.objects.create(
            quote_request=qr,
            amount=Decimal("1800.00"),
            description="Done",
            estimated_days=2,
        )
        data = SupplierJobSerializer(qr).data
        self.assertIsNotNone(data["quote"])
        self.assertEqual(data["quote"]["amount"], "1800.00")

    def test_quote_is_none_when_absent(self):
        qr = self._setup()
        data = SupplierJobSerializer(qr).data
        self.assertIsNone(data["quote"])


# ─────────────────────────────────────────────────────────────────────────────
# SupplierCalendarItemSerializer
# ─────────────────────────────────────────────────────────────────────────────
class SupplierCalendarItemSerializerTests(TremlyAPITestCase):
    def test_serializes_raw_dict(self):
        payload = {
            "quote_request_id": 17,
            "title": "Paint kitchen",
            "property_name": "Oak Grove",
            "start_date": date(2026, 5, 1),
            "end_date": date(2026, 5, 3),
            "amount": Decimal("4500.00"),
            "status": "awarded",
        }
        data = SupplierCalendarItemSerializer(payload).data
        self.assertEqual(data["id"], 17)
        self.assertEqual(data["title"], "Paint kitchen")
        self.assertEqual(data["start_date"], "2026-05-01")
        self.assertEqual(data["end_date"], "2026-05-03")
        self.assertEqual(data["amount"], "4500.00")

    def test_missing_required_fields_fail_validation(self):
        ser = SupplierCalendarItemSerializer(data={"title": "only"})
        self.assertFalse(ser.is_valid())
        # At minimum, start_date / end_date / amount are required
        self.assertIn("start_date", ser.errors)
        self.assertIn("end_date", ser.errors)
        self.assertIn("amount", ser.errors)
