"""
Unit tests for apps/properties/mandate_services.py.

Covers:
  - build_mandate_context: merges owner/agency/property/mandate fields correctly
  - generate_mandate_html: substitutes merge fields, populates agent_name
  - build_mandate_signers: owner-first/agent-second ordering, fallback names
  - _fmt_date / _fmt_address helpers

These are DB-backed unit tests (the services load real models through FK
traversal); we use the TremlyAPITestCase factories but don't exercise the
HTTP layer.
"""
import pytest
from datetime import date
from decimal import Decimal
from unittest import mock

from apps.accounts.models import Agency
from apps.properties.mandate_services import (
    _fmt_address,
    _fmt_date,
    _mandate_duration_text,
    build_mandate_context,
    build_mandate_signers,
    generate_mandate_html,
)
from apps.properties.models import RentalMandate
from apps.test_hub.base.test_case import TremlyAPITestCase

pytestmark = [pytest.mark.unit, pytest.mark.green]


# ─────────────────────────────────────────────────────────────────────
# Helpers (pure)
# ─────────────────────────────────────────────────────────────────────


class FormatHelperTests(TremlyAPITestCase):
    """Pure formatting helpers — no DB involvement."""

    def test_fmt_date_none_returns_dash(self):
        self.assertEqual(_fmt_date(None), "—")

    def test_fmt_date_formats_date_object(self):
        out = _fmt_date(date(2026, 4, 8))
        self.assertIn("April", out)
        self.assertIn("2026", out)

    def test_fmt_date_falls_back_to_str_for_non_date(self):
        self.assertEqual(_fmt_date("not-a-date"), "not-a-date")

    def test_fmt_address_empty_dict(self):
        self.assertEqual(_fmt_address({}), "—")

    def test_fmt_address_none(self):
        self.assertEqual(_fmt_address(None), "—")

    def test_fmt_address_joins_parts(self):
        out = _fmt_address({
            "street": "10 Main Rd",
            "city": "Cape Town",
            "province": "Western Cape",
            "postal_code": "8001",
        })
        self.assertEqual(out, "10 Main Rd, Cape Town, Western Cape, 8001")

    def test_fmt_address_skips_empty_parts(self):
        out = _fmt_address({"street": "10 Main Rd", "city": "", "province": "WC", "postal_code": ""})
        self.assertEqual(out, "10 Main Rd, WC")

    def test_mandate_duration_indefinite_when_no_end(self):
        out = _mandate_duration_text(date(2026, 1, 1), None)
        self.assertIn("indefinite", out)

    def test_mandate_duration_twelve_months(self):
        out = _mandate_duration_text(date(2026, 1, 1), date(2027, 1, 1))
        self.assertIn("12", out)

    def test_mandate_duration_six_months(self):
        out = _mandate_duration_text(date(2026, 1, 1), date(2026, 7, 1))
        self.assertIn("6 months", out)


# ─────────────────────────────────────────────────────────────────────
# Context builder
# ─────────────────────────────────────────────────────────────────────


class BuildMandateContextTests(TremlyAPITestCase):
    """build_mandate_context merges data from Landlord, Agency, Property, RentalMandate."""

    def setUp(self):
        self.agency = Agency.objects.create(
            name="Klikk Properties (Pty) Ltd",
            trading_name="Klikk",
            registration_number="2020/123456/07",
            vat_number="4123456789",
            eaab_ffc_number="PPRA-FFC-2025-01",
            contact_number="0211234567",
            email="info@klikk.co.za",
            physical_address="Shop 1, Main Rd, Cape Town",
            trust_bank_name="Nedbank",
            trust_account_number="1234567890",
        )
        self.landlord = self.create_landlord(name="Acme Holdings (Pty) Ltd")
        self.prop = self.create_property(name="Sunset Villa", description="Sea view home")
        self.create_property_ownership(property_obj=self.prop, landlord=self.landlord)
        self.mandate = RentalMandate.objects.create(
            property=self.prop,
            landlord=self.landlord,
            mandate_type=RentalMandate.MandateType.FULL_MANAGEMENT,
            exclusivity=RentalMandate.Exclusivity.SOLE,
            commission_rate=Decimal("10.00"),
            commission_period=RentalMandate.CommissionPeriod.MONTHLY,
            start_date=date(2026, 1, 1),
            end_date=date(2027, 1, 1),
            notice_period_days=60,
            maintenance_threshold=Decimal("2500.00"),
        )

    def test_owner_fields_from_landlord_representative(self):
        ctx = build_mandate_context(self.mandate)
        self.assertEqual(ctx["owner_full_name"], "John Landlord")
        self.assertEqual(ctx["owner_email_address"], "john@landlord.co.za")
        self.assertEqual(ctx["owner_contact_number"], "0829998877")

    def test_agency_uses_trading_name_when_set(self):
        ctx = build_mandate_context(self.mandate)
        self.assertEqual(ctx["agency_name"], "Klikk")
        self.assertEqual(ctx["agency_registration_number"], "2020/123456/07")
        self.assertEqual(ctx["agency_ffc_number"], "PPRA-FFC-2025-01")
        self.assertEqual(ctx["agency_vat_number"], "4123456789")

    def test_agency_falls_back_to_registered_name(self):
        self.agency.trading_name = ""
        self.agency.save()
        ctx = build_mandate_context(self.mandate)
        self.assertEqual(ctx["agency_name"], "Klikk Properties (Pty) Ltd")

    def test_property_address_concatenated(self):
        ctx = build_mandate_context(self.mandate)
        self.assertIn("123 Test St", ctx["property_address"])
        self.assertIn("Cape Town", ctx["property_address"])

    def test_mandate_type_checkbox_full_management(self):
        ctx = build_mandate_context(self.mandate)
        self.assertEqual(ctx["mandate_type_full_management_check"], "☑")
        self.assertEqual(ctx["mandate_type_letting_only_check"], "☐")
        self.assertEqual(ctx["mandate_type_rent_collection_check"], "☐")
        self.assertEqual(ctx["mandate_type_finders_fee_check"], "☐")
        self.assertEqual(ctx["mandate_type_full_management_class"], "active-type")
        self.assertEqual(ctx["mandate_type_letting_only_class"], "inactive-type")

    def test_mandate_type_checkbox_letting_only(self):
        self.mandate.mandate_type = RentalMandate.MandateType.LETTING_ONLY
        self.mandate.save()
        ctx = build_mandate_context(self.mandate)
        self.assertEqual(ctx["mandate_type_letting_only_check"], "☑")
        self.assertEqual(ctx["mandate_type_full_management_check"], "☐")

    def test_exclusivity_sole(self):
        ctx = build_mandate_context(self.mandate)
        self.assertEqual(ctx["exclusivity_sole_check"], "☑")
        self.assertEqual(ctx["exclusivity_open_check"], "☐")

    def test_exclusivity_open(self):
        self.mandate.exclusivity = RentalMandate.Exclusivity.OPEN
        self.mandate.save()
        ctx = build_mandate_context(self.mandate)
        self.assertEqual(ctx["exclusivity_open_check"], "☑")
        self.assertEqual(ctx["exclusivity_sole_check"], "☐")

    def test_commission_monthly_display(self):
        ctx = build_mandate_context(self.mandate)
        self.assertIn("10", ctx["commission_rate_display"])
        self.assertIn("%", ctx["commission_rate_display"])

    def test_commission_once_off_display_singular(self):
        self.mandate.commission_period = RentalMandate.CommissionPeriod.ONCE_OFF
        self.mandate.commission_rate = Decimal("1.00")
        self.mandate.save()
        ctx = build_mandate_context(self.mandate)
        # "1 month's gross rental" — singular, no trailing 's'
        self.assertIn("1 month's", ctx["commission_rate_display"])

    def test_commission_once_off_display_plural(self):
        self.mandate.commission_period = RentalMandate.CommissionPeriod.ONCE_OFF
        self.mandate.commission_rate = Decimal("2.00")
        self.mandate.save()
        ctx = build_mandate_context(self.mandate)
        self.assertIn("2 months", ctx["commission_rate_display"])

    def test_trust_account_pulled_from_agency(self):
        ctx = build_mandate_context(self.mandate)
        self.assertEqual(ctx["trust_bank_name"], "Nedbank")
        self.assertEqual(ctx["trust_account_number"], "1234567890")

    def test_maintenance_threshold_formatted_with_thousands_sep(self):
        self.mandate.maintenance_threshold = Decimal("12500.00")
        self.mandate.save()
        ctx = build_mandate_context(self.mandate)
        self.assertEqual(ctx["maintenance_threshold"], "12,500.00")

    def test_agent_name_defaults_to_dash(self):
        ctx = build_mandate_context(self.mandate)
        self.assertEqual(ctx["agent_name"], "—")

    def test_owner_fallback_to_ownership_when_no_landlord(self):
        """If mandate.landlord is None, context falls back to PropertyOwnership."""
        self.mandate.landlord = None
        self.mandate.save()
        # PropertyOwnership has its own representative fields
        ownership = self.prop.ownerships.filter(is_current=True).first()
        ownership.representative_name = "Fallback Rep"
        ownership.representative_email = "fallback@test.com"
        ownership.save()

        ctx = build_mandate_context(self.mandate)
        self.assertEqual(ctx["owner_full_name"], "Fallback Rep")
        self.assertEqual(ctx["owner_email_address"], "fallback@test.com")

    def test_missing_agency_gives_dashes(self):
        Agency.objects.all().delete()
        ctx = build_mandate_context(self.mandate)
        self.assertEqual(ctx["agency_name"], "—")
        self.assertEqual(ctx["agency_ffc_number"], "—")
        self.assertEqual(ctx["trust_bank_name"], "—")


# ─────────────────────────────────────────────────────────────────────
# HTML generator
# ─────────────────────────────────────────────────────────────────────


class GenerateMandateHtmlTests(TremlyAPITestCase):
    """generate_mandate_html reads the template file, substitutes merge fields."""

    def setUp(self):
        Agency.objects.create(name="Klikk", eaab_ffc_number="PPRA-FFC-1", contact_number="0211234567")
        self.landlord = self.create_landlord()
        self.prop = self.create_property()
        self.create_property_ownership(property_obj=self.prop, landlord=self.landlord)
        self.mandate = RentalMandate.objects.create(
            property=self.prop,
            landlord=self.landlord,
            mandate_type=RentalMandate.MandateType.FULL_MANAGEMENT,
            commission_rate=Decimal("10.00"),
            start_date=date(2026, 1, 1),
            notice_period_days=60,
            maintenance_threshold=Decimal("2000.00"),
        )
        self.agent = self.create_agent(first_name="Mary", last_name="Manager")

    def test_reads_template_file_and_returns_html(self):
        """Template file exists and the function returns a non-empty string."""
        html = generate_mandate_html(self.mandate, agent_user=self.agent)
        self.assertIsInstance(html, str)
        self.assertGreater(len(html), 100)

    def test_substitutes_agency_name(self):
        html = generate_mandate_html(self.mandate, agent_user=self.agent)
        self.assertIn("Klikk", html)

    def test_agent_name_substituted_from_user(self):
        """agent_name merge field must be populated from the user."""
        with mock.patch(
            "apps.properties.mandate_services.open",
            mock.mock_open(read_data="Agent: {{agent_name}}"),
            create=True,
        ):
            html = generate_mandate_html(self.mandate, agent_user=self.agent)
            self.assertIn("Mary Manager", html)

    def test_agent_name_falls_back_to_email_when_no_full_name(self):
        agent_no_name = self.create_agent(email="anon@test.com", first_name="", last_name="")
        with mock.patch(
            "apps.properties.mandate_services.open",
            mock.mock_open(read_data="{{agent_name}}"),
            create=True,
        ):
            html = generate_mandate_html(self.mandate, agent_user=agent_no_name)
            self.assertIn("anon@test.com", html)

    def test_unknown_merge_field_passes_through(self):
        """Unknown {{key}} tokens become [key] for debugging visibility."""
        with mock.patch(
            "apps.properties.mandate_services.open",
            mock.mock_open(read_data="{{owner_full_name}} — {{totally_unknown_field}}"),
            create=True,
        ):
            html = generate_mandate_html(self.mandate, agent_user=self.agent)
            self.assertIn("John Landlord", html)
            self.assertIn("[totally_unknown_field]", html)

    def test_no_agent_user_leaves_agent_name_as_dash(self):
        with mock.patch(
            "apps.properties.mandate_services.open",
            mock.mock_open(read_data="Agent: {{agent_name}}"),
            create=True,
        ):
            html = generate_mandate_html(self.mandate, agent_user=None)
            self.assertIn("Agent: —", html)


# ─────────────────────────────────────────────────────────────────────
# Signer builder
# ─────────────────────────────────────────────────────────────────────


class BuildMandateSignersTests(TremlyAPITestCase):
    """build_mandate_signers returns [owner, agent] in signing order."""

    def setUp(self):
        self.landlord = self.create_landlord()
        self.prop = self.create_property()
        self.mandate = RentalMandate.objects.create(
            property=self.prop,
            landlord=self.landlord,
            mandate_type=RentalMandate.MandateType.FULL_MANAGEMENT,
            commission_rate=Decimal("10.00"),
            start_date=date(2026, 1, 1),
            notice_period_days=60,
            maintenance_threshold=Decimal("2000.00"),
        )
        self.agent = self.create_agent(email="mary@klikk.co.za", first_name="Mary", last_name="Manager")

    def test_signers_are_ordered_owner_then_agent(self):
        signers = build_mandate_signers(self.mandate, self.agent)
        self.assertEqual(len(signers), 2)
        self.assertEqual(signers[0]["order"], 0)
        self.assertEqual(signers[0]["role"], "owner")
        self.assertEqual(signers[1]["order"], 1)
        self.assertEqual(signers[1]["role"], "agent")

    def test_owner_populated_from_landlord_representative(self):
        signers = build_mandate_signers(self.mandate, self.agent)
        owner = signers[0]
        self.assertEqual(owner["name"], "John Landlord")
        self.assertEqual(owner["email"], "john@landlord.co.za")
        self.assertEqual(owner["phone"], "0829998877")
        self.assertTrue(owner["send_email"])

    def test_owner_falls_back_to_property_ownership(self):
        self.mandate.landlord = None
        self.mandate.save()
        self.create_property_ownership(
            property_obj=self.prop,
            landlord=None,
            owner_name="Pinned Owner",
            owner_email="pinned@test.com",
            owner_phone="0811111111",
            representative_name="",
            representative_email="",
            representative_phone="",
        )
        signers = build_mandate_signers(self.mandate, self.agent)
        self.assertEqual(signers[0]["name"], "Pinned Owner")
        self.assertEqual(signers[0]["email"], "pinned@test.com")

    def test_owner_defaults_when_nothing_known(self):
        self.mandate.landlord = None
        self.mandate.save()
        # No PropertyOwnership on this property → hardcoded default
        signers = build_mandate_signers(self.mandate, self.agent)
        self.assertEqual(signers[0]["name"], "Property Owner")
        self.assertEqual(signers[0]["email"], "")
        self.assertFalse(signers[0]["send_email"])

    def test_agent_name_uses_full_name(self):
        signers = build_mandate_signers(self.mandate, self.agent)
        self.assertEqual(signers[1]["name"], "Mary Manager")
        self.assertEqual(signers[1]["email"], "mary@klikk.co.za")
        self.assertTrue(signers[1]["send_email"])

    def test_agent_name_falls_back_to_email(self):
        nameless = self.create_agent(email="nameless@klikk.co.za", first_name="", last_name="")
        signers = build_mandate_signers(self.mandate, nameless)
        self.assertEqual(signers[1]["name"], "nameless@klikk.co.za")

    def test_send_email_flag_false_when_owner_email_missing(self):
        self.landlord.email = ""
        self.landlord.representative_email = ""
        self.landlord.save()
        signers = build_mandate_signers(self.mandate, self.agent)
        self.assertFalse(signers[0]["send_email"])
