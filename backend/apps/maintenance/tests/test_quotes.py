"""Tests for token-based supplier quote views (AllowAny — no auth required)."""
import uuid
from decimal import Decimal

from django.urls import reverse

from apps.maintenance.models import JobDispatch, JobQuote, JobQuoteRequest
from tests.base import TremlyAPITestCase


class TokenBasedQuoteTests(TremlyAPITestCase):

    def setUp(self):
        self.agent = self.create_agent()
        self.supplier = self.create_supplier()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.mr = self.create_maintenance_request(unit=self.unit)
        self.dispatch = JobDispatch.objects.create(
            maintenance_request=self.mr, dispatched_by=self.agent, status="sent",
        )
        self.qr = JobQuoteRequest.objects.create(
            dispatch=self.dispatch, supplier=self.supplier, status="pending",
        )

    def test_get_quote_page(self):
        """Token-based GET — no auth required."""
        resp = self.client.get(reverse("supplier-quote", args=[self.qr.token]))
        self.assertEqual(resp.status_code, 200)
        self.qr.refresh_from_db()
        self.assertEqual(self.qr.status, "viewed")

    def test_get_quote_page_invalid_token(self):
        resp = self.client.get(reverse("supplier-quote", args=[uuid.uuid4()]))
        self.assertEqual(resp.status_code, 404)

    def test_submit_quote(self):
        resp = self.client.post(
            reverse("supplier-quote", args=[self.qr.token]),
            {"amount": "3500.00", "estimated_days": 5, "notes": "Will fix"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.qr.refresh_from_db()
        self.assertEqual(self.qr.status, "quoted")

    def test_submit_quote_already_submitted(self):
        JobQuote.objects.create(quote_request=self.qr, amount=Decimal("1000.00"))
        resp = self.client.post(
            reverse("supplier-quote", args=[self.qr.token]),
            {"amount": "2000.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_submit_quote_closed(self):
        self.qr.status = "awarded"
        self.qr.save()
        resp = self.client.post(
            reverse("supplier-quote", args=[self.qr.token]),
            {"amount": "1000.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_no_auth_required(self):
        """
        SECURITY AUDIT: Token-based quote views use AllowAny.
        This is by design for external suppliers, but means anyone with a
        token link can view job details and submit quotes.
        """
        # No authentication set — should still work
        resp = self.client.get(reverse("supplier-quote", args=[self.qr.token]))
        self.assertEqual(resp.status_code, 200)

    def test_decline_quote(self):
        resp = self.client.post(reverse("supplier-quote-decline", args=[self.qr.token]))
        self.assertEqual(resp.status_code, 200)
        self.qr.refresh_from_db()
        self.assertEqual(self.qr.status, "declined")

    def test_decline_closed(self):
        self.qr.status = "awarded"
        self.qr.save()
        resp = self.client.post(reverse("supplier-quote-decline", args=[self.qr.token]))
        self.assertEqual(resp.status_code, 400)
