"""Tests for ``apps.leases.merge_fields_loader``.

Covers the YAML-backed loader + the per-request `filter_by_context()`
that fixes ``docs/system/lease-ai-agent-architecture.md`` §2 failure
mode 2 ("AI pulls `tenant_2_*` even with one tenant").

Run via:
    cd backend && .venv/bin/python -m pytest apps/leases/tests/test_merge_fields_loader.py -q
"""
from __future__ import annotations

import re
import textwrap

import yaml
from django.test import TestCase

from apps.leases.merge_fields_loader import (
    MergeField,
    StringDateSafeLoader,
    field_by_name,
    filter_by_context,
    load_all_fields,
    render_for_drafter_system_block,
)


# ── Fixture: snapshot of the legacy hand-coded list ────────────────── #
#
# Captured 2026-05-13 from ``apps/leases/merge_fields.py`` BEFORE the
# YAML cutover. Round-trip: every (category, name, label) here MUST
# resolve to an equivalent entry from the YAML loader.

_LEGACY_CANONICAL_MERGE_FIELDS: list[tuple[str, str, str]] = [
    ("landlord", "landlord_name", "Full name (individual) or trading name (company)"),
    ("landlord", "landlord_entity_name", "Registered company / CC / trust name"),
    ("landlord", "landlord_registration_no", "Company / CC / trust registration number"),
    ("landlord", "landlord_vat_no", "VAT registration number"),
    ("landlord", "landlord_representative", "Authorised representative name (companies)"),
    ("landlord", "landlord_representative_id", "ID number of authorised representative"),
    ("landlord", "landlord_title", "Title (Mr / Ms / Dr / Pty Ltd / etc.)"),
    ("landlord", "landlord_id", "SA ID number (individual landlord)"),
    ("landlord", "landlord_contact", "Primary contact / phone"),
    ("landlord", "landlord_phone", "Phone number (alias for landlord_contact)"),
    ("landlord", "landlord_email", "Email address"),
    ("landlord", "landlord_physical_address", "Physical / postal address"),
    ("landlord_bank", "landlord_bank_name", "Bank name (e.g. FNB, Standard Bank)"),
    ("landlord_bank", "landlord_bank_branch_code", "Branch / universal branch code"),
    ("landlord_bank", "landlord_bank_account_no", "Bank account number"),
    ("landlord_bank", "landlord_bank_account_holder", "Account holder name"),
    ("landlord_bank", "landlord_bank_account_type", "Account type (cheque / savings / current)"),
    ("property", "property_address", "Full street address of the property"),
    ("property", "property_name", "Estate / building / complex name"),
    ("property", "property_description", "Full legal or erf description"),
    ("property", "unit_number", "Unit / flat / door number"),
    ("property", "city", "City or town"),
    ("property", "province", "Province (e.g. Western Cape)"),
    ("tenant", "tenant_name", "Full name of primary tenant"),
    ("tenant", "tenant_id", "SA ID number of primary tenant"),
    ("tenant", "tenant_phone", "Phone number"),
    ("tenant", "tenant_contact", "Contact number (alias for tenant_phone)"),
    ("tenant", "tenant_email", "Email address"),
    ("tenant", "tenant_address", "Current residential address"),
    ("tenant", "tenant_employer", "Employer name"),
    ("tenant", "tenant_occupation", "Occupation / job title"),
    ("tenant", "tenant_dob", "Date of birth"),
    ("tenant", "tenant_emergency_contact", "Emergency contact person name"),
    ("tenant", "tenant_emergency_phone", "Emergency contact phone number"),
    ("tenant_1", "tenant_1_name", "Tenant 1 full name (alias for tenant_name)"),
    ("tenant_1", "tenant_1_id", "Tenant 1 SA ID number"),
    ("tenant_1", "tenant_1_phone", "Tenant 1 phone"),
    ("tenant_1", "tenant_1_email", "Tenant 1 email"),
    ("tenant_1", "tenant_1_address", "Tenant 1 address"),
    ("tenant_1", "tenant_1_employer", "Tenant 1 employer"),
    ("tenant_1", "tenant_1_occupation", "Tenant 1 occupation"),
    ("tenant_1", "tenant_1_dob", "Tenant 1 date of birth"),
    ("tenant_1", "tenant_1_emergency_contact", "Tenant 1 emergency contact"),
    ("tenant_1", "tenant_1_emergency_phone", "Tenant 1 emergency phone"),
    ("tenant_1", "primary_tenant_payment_reference", "Primary tenant payment reference (EFT)"),
    ("tenant_1", "cotenant_1_payment_reference", "Co-tenant 1 payment reference (EFT)"),
    ("tenant_2", "tenant_2_name", "Tenant 2 full name"),
    ("tenant_2", "tenant_2_id", "Tenant 2 SA ID number"),
    ("tenant_2", "tenant_2_phone", "Tenant 2 phone"),
    ("tenant_2", "tenant_2_email", "Tenant 2 email"),
    ("tenant_2", "tenant_2_address", "Tenant 2 address"),
    ("tenant_2", "tenant_2_employer", "Tenant 2 employer"),
    ("tenant_2", "tenant_2_occupation", "Tenant 2 occupation"),
    ("tenant_2", "tenant_2_dob", "Tenant 2 date of birth"),
    ("tenant_2", "tenant_2_emergency_contact", "Tenant 2 emergency contact"),
    ("tenant_2", "tenant_2_emergency_phone", "Tenant 2 emergency phone"),
    ("tenant_2", "cotenant_2_payment_reference", "Co-tenant 2 payment reference (EFT)"),
    ("tenant_3", "tenant_3_name", "Tenant 3 full name"),
    ("tenant_3", "tenant_3_id", "Tenant 3 SA ID number"),
    ("tenant_3", "tenant_3_phone", "Tenant 3 phone"),
    ("tenant_3", "tenant_3_email", "Tenant 3 email"),
    ("tenant_3", "tenant_3_address", "Tenant 3 address"),
    ("tenant_3", "tenant_3_employer", "Tenant 3 employer"),
    ("tenant_3", "tenant_3_occupation", "Tenant 3 occupation"),
    ("tenant_3", "tenant_3_dob", "Tenant 3 date of birth"),
    ("tenant_3", "tenant_3_emergency_contact", "Tenant 3 emergency contact"),
    ("tenant_3", "tenant_3_emergency_phone", "Tenant 3 emergency phone"),
    ("tenant_3", "cotenant_3_payment_reference", "Co-tenant 3 payment reference (EFT)"),
    ("co_tenants", "co_tenants", "Comma-separated list of all co-tenant names"),
    ("occupant_1", "occupant_1_name", "Occupant 1 full name"),
    ("occupant_1", "occupant_1_id", "Occupant 1 SA ID number"),
    ("occupant_1", "occupant_1_relationship", "Occupant 1 relationship to tenant"),
    ("occupant_2", "occupant_2_name", "Occupant 2 full name"),
    ("occupant_2", "occupant_2_id", "Occupant 2 SA ID number"),
    ("occupant_2", "occupant_2_relationship", "Occupant 2 relationship to tenant"),
    ("occupant_3", "occupant_3_name", "Occupant 3 full name"),
    ("occupant_3", "occupant_3_id", "Occupant 3 SA ID number"),
    ("occupant_3", "occupant_3_relationship", "Occupant 3 relationship to tenant"),
    ("occupant_4", "occupant_4_name", "Occupant 4 full name"),
    ("occupant_4", "occupant_4_id", "Occupant 4 SA ID number"),
    ("occupant_4", "occupant_4_relationship", "Occupant 4 relationship to tenant"),
    ("lease_terms", "lease_start", "Lease commencement date"),
    ("lease_terms", "lease_end", "Lease expiry / end date"),
    ("lease_terms", "monthly_rent", "Monthly rental amount (numeric)"),
    ("lease_terms", "monthly_rent_words", "Monthly rental amount in words"),
    ("lease_terms", "deposit", "Deposit amount (numeric)"),
    ("lease_terms", "deposit_words", "Deposit amount in words"),
    ("lease_terms", "notice_period_days", "Notice period in days (minimum 20 business days per RHA)"),
    ("lease_terms", "water_included", "Whether water is included (Yes/No)"),
    ("lease_terms", "electricity_prepaid", "Whether electricity is prepaid (Yes/No)"),
    ("services", "water_arrangement", "Water arrangement key: included | not_included"),
    ("services", "water_arrangement_label", "Water arrangement (human-readable)"),
    ("services", "electricity_arrangement", "Electricity arrangement key: prepaid | eskom_direct | included | not_included"),
    ("services", "electricity_arrangement_label", "Electricity arrangement (human-readable)"),
    ("services", "gardening_service_included", "Gardening service included (boolean)"),
    ("services", "gardening_service_included_label", "Gardening service included (Yes/No)"),
    ("services", "wifi_included", "Wifi included (boolean)"),
    ("services", "wifi_included_label", "Wifi included (Yes/No)"),
    ("services", "security_service_included", "Armed response / security service included (boolean)"),
    ("services", "security_service_included_label", "Armed response / security service included (Yes/No)"),
    ("lease_terms", "max_occupants", "Maximum number of authorised occupants"),
    ("lease_terms", "payment_reference", "Payment reference for EFT (legacy alias for primary_tenant_payment_reference)"),
    ("lease_terms", "lease_number", "Unique lease reference number"),
]


def _by_name(fields: list[MergeField]) -> dict[str, MergeField]:
    return {f.name: f for f in fields}


class TestLegacyRoundTrip(TestCase):
    """Every legacy tuple must survive the YAML cutover with the same
    name, category, and label."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Make sure the cache is warm + uncontaminated.
        load_all_fields.cache_clear()
        cls.fields = load_all_fields()
        cls.by_name = _by_name(cls.fields)

    def test_legacy_count_matches_yaml_count(self):
        self.assertEqual(
            len(self.fields),
            len(_LEGACY_CANONICAL_MERGE_FIELDS),
            "YAML field count must equal the legacy tuple count.",
        )

    def test_all_legacy_fields_round_trip(self):
        """Every (category, name, label) from the legacy list must have a
        matching YAML entry."""
        for legacy_cat, legacy_name, legacy_label in _LEGACY_CANONICAL_MERGE_FIELDS:
            with self.subTest(name=legacy_name):
                self.assertIn(legacy_name, self.by_name)
                field = self.by_name[legacy_name]
                self.assertEqual(
                    field.category,
                    legacy_cat,
                    f"Category drifted for {legacy_name}: "
                    f"legacy={legacy_cat} yaml={field.category}",
                )
                self.assertEqual(
                    field.label,
                    legacy_label,
                    f"Label drifted for {legacy_name}",
                )

    def test_no_duplicate_names(self):
        names = [f.name for f in self.fields]
        self.assertEqual(len(names), len(set(names)))

    def test_every_field_has_an_example(self):
        for field in self.fields:
            with self.subTest(name=field.name):
                self.assertGreater(len(field.example), 0)

    def test_every_field_has_plain_english(self):
        for field in self.fields:
            with self.subTest(name=field.name):
                self.assertGreater(len(field.plain_english), 0)


class TestFilterByContext(TestCase):
    """``filter_by_context`` materialises the context-aware subset used by
    the lease-AI Front Door to build the cached merge-fields system block.

    These tests are the literal §2 failure-mode-2 enforcement and the
    sectional-title applicability gates."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_all_fields.cache_clear()

    def test_filter_by_context_drops_tenant_2_fields_when_count_is_1(self):
        """THE §2 FAILURE-MODE-2 TEST. With a 1-tenant request, no
        tenant_2_* or tenant_3_* field is returned to the Drafter."""
        fields = filter_by_context(
            tenant_count=1, property_type="freehold", lease_type="fixed_term"
        )
        leakage = [
            f.name for f in fields if f.category in ("tenant_2", "tenant_3")
        ]
        self.assertEqual(
            leakage,
            [],
            "tenant_2/3 fields leaked into a single-tenant context — "
            "this is the §2 failure-mode-2 v1 bug.",
        )

    def test_filter_by_context_includes_tenant_2_fields_when_count_is_2(self):
        fields = filter_by_context(
            tenant_count=2, property_type="freehold", lease_type="fixed_term"
        )
        t2_names = [f.name for f in fields if f.category == "tenant_2"]
        self.assertIn("tenant_2_name", t2_names)
        self.assertIn("tenant_2_id", t2_names)
        # tenant_3 still excluded
        self.assertEqual(
            [f.name for f in fields if f.category == "tenant_3"], []
        )

    def test_filter_by_context_includes_all_tenant_buckets_when_count_is_3(self):
        fields = filter_by_context(
            tenant_count=3, property_type="freehold", lease_type="fixed_term"
        )
        for cat in ("tenant_1", "tenant_2", "tenant_3"):
            with self.subTest(category=cat):
                self.assertTrue(
                    any(f.category == cat for f in fields),
                    f"Expected {cat} fields at tenant_count=3.",
                )

    def test_filter_by_context_includes_sectional_title_specific_when_correct(self):
        fields = filter_by_context(
            tenant_count=1,
            property_type="sectional_title",
            lease_type="fixed_term",
        )
        names = [f.name for f in fields]
        # unit_number is sectional-title / apartment / townhouse / student /
        # holiday_let only — must appear when property_type=sectional_title.
        self.assertIn("unit_number", names)

    def test_filter_by_context_excludes_sectional_title_specific_for_freehold(self):
        fields = filter_by_context(
            tenant_count=1, property_type="freehold", lease_type="fixed_term"
        )
        names = [f.name for f in fields]
        self.assertNotIn(
            "unit_number",
            names,
            "unit_number applies to sectional-title-like property types only; "
            "must not leak into a freehold context.",
        )

    def test_filter_excludes_lease_end_for_month_to_month(self):
        fields = filter_by_context(
            tenant_count=1,
            property_type="freehold",
            lease_type="month_to_month",
        )
        names = [f.name for f in fields]
        self.assertNotIn(
            "lease_end",
            names,
            "lease_end only applies to fixed_term / lease_renewal — "
            "must not leak into a month_to_month context.",
        )


class TestRenderForDrafterSystemBlock(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_all_fields.cache_clear()

    def test_render_for_drafter_system_block_is_compact(self):
        """The rendered block must fit comfortably in the Drafter's cached
        system block budget for the typical 1-tenant freehold scenario."""
        fields = filter_by_context(
            tenant_count=1, property_type="freehold", lease_type="fixed_term"
        )
        rendered = render_for_drafter_system_block(fields)
        self.assertLess(
            len(rendered),
            4000,
            f"Rendered block is {len(rendered)} chars; must stay under 4000 "
            "to fit the cached system block (architecture doc §6.6).",
        )

    def test_render_is_deterministic(self):
        """Same context → same string. The block must be fully cacheable."""
        ctx = dict(
            tenant_count=2,
            property_type="sectional_title",
            lease_type="fixed_term",
        )
        a = render_for_drafter_system_block(filter_by_context(**ctx))
        b = render_for_drafter_system_block(filter_by_context(**ctx))
        self.assertEqual(a, b)

    def test_render_marks_required_fields(self):
        fields = filter_by_context(
            tenant_count=1, property_type="freehold", lease_type="fixed_term"
        )
        rendered = render_for_drafter_system_block(fields)
        # Required fields are tagged with a leading `*` in the rendering.
        self.assertIn("* `landlord_name`", rendered)
        self.assertIn("* `tenant_name`", rendered)
        self.assertIn("* `property_address`", rendered)
        self.assertIn("* `monthly_rent`", rendered)
        self.assertIn("* `deposit`", rendered)


class TestValidationRegex(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_all_fields.cache_clear()

    def test_validation_regex_for_sa_id(self):
        """tenant_id carries the SA-ID regex and accepts a 13-digit string."""
        field = field_by_name("tenant_1_id")
        self.assertIsNotNone(field)
        self.assertEqual(field.validation_regex, r"^\d{13}$")
        self.assertTrue(re.fullmatch(field.validation_regex, "9203124567083"))
        self.assertFalse(re.fullmatch(field.validation_regex, "abc"))
        self.assertFalse(re.fullmatch(field.validation_regex, "920312"))

    def test_validation_regex_for_branch_code(self):
        field = field_by_name("landlord_bank_branch_code")
        self.assertIsNotNone(field)
        self.assertEqual(field.validation_regex, r"^\d{6}$")
        self.assertTrue(re.fullmatch(field.validation_regex, "250655"))
        self.assertFalse(re.fullmatch(field.validation_regex, "25065"))

    def test_validation_regex_for_vat_no(self):
        field = field_by_name("landlord_vat_no")
        self.assertIsNotNone(field)
        self.assertEqual(field.validation_regex, r"^4\d{9}$")
        self.assertTrue(re.fullmatch(field.validation_regex, "4123456789"))
        self.assertFalse(re.fullmatch(field.validation_regex, "5123456789"))


class TestSchemaEnforcement(TestCase):
    """Loader rejects malformed YAML records."""

    def test_unknown_yaml_field_raises(self):
        """A YAML record with an extra field must fail schema validation."""
        # Write a temp YAML file inside the merge_fields/ dir, then
        # invalidate the cache to force a re-read. We restore afterwards.
        from apps.leases import merge_fields_loader

        merge_fields_dir = merge_fields_loader._merge_fields_dir()
        temp_yaml = merge_fields_dir / "_test_invalid.yaml"
        try:
            temp_yaml.write_text(
                textwrap.dedent(
                    """\
                    ---
                    - name: bogus_field
                      label: Bogus
                      category: landlord
                      type: string
                      required: false
                      applicability:
                        tenant_counts: any
                        property_types: any
                        lease_types: any
                      example: bogus
                      plain_english: Bogus.
                      related_legal_facts: []
                      this_key_does_not_exist: true
                    """
                ),
                encoding="utf-8",
            )
            load_all_fields.cache_clear()
            with self.assertRaises(ValueError) as ctx:
                load_all_fields()
            self.assertIn("this_key_does_not_exist", str(ctx.exception))
        finally:
            temp_yaml.unlink(missing_ok=True)
            load_all_fields.cache_clear()

    def test_loader_returns_sorted_stable(self):
        """Same content → same order on every call. Used by caching."""
        load_all_fields.cache_clear()
        a = [f.name for f in load_all_fields()]
        load_all_fields.cache_clear()
        b = [f.name for f in load_all_fields()]
        self.assertEqual(a, b)
        # Also stable across categories
        cats_a = [f.category for f in load_all_fields()]
        load_all_fields.cache_clear()
        cats_b = [f.category for f in load_all_fields()]
        self.assertEqual(cats_a, cats_b)


class TestStringDateLoader(TestCase):
    """The PyYAML SafeLoader subclass MUST keep ISO date strings as strings.

    This is the same architectural concern the legal_rag checks
    documented: ``yaml.SafeLoader`` resolves ``"2026-05-12"`` to
    ``datetime.date(2026, 5, 12)`` which then breaks JSON Schema
    ``format: date`` validation. We verify the loader stripped the
    timestamp resolver.
    """

    def test_iso_date_string_stays_a_string(self):
        loaded = yaml.load(
            "value: 2026-05-12", Loader=StringDateSafeLoader
        )
        self.assertEqual(loaded["value"], "2026-05-12")
        self.assertIsInstance(loaded["value"], str)
