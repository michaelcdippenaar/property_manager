"""
Test HTML rendering pipeline: TipTap template → generate_lease_html() → DocuSeal-ready HTML.

Verifies:
  - Inline signing fields (<signature-field>, <initials-field>, <date-field>) are preserved
  - TipTap signer roles are mapped to DocuSeal roles (landlord → First Party, etc.)
  - Merge fields are replaced with lease context values (v1 and v2 formats)
  - {{mustache}} placeholders are replaced
  - Page breaks are converted
  - No fallback signature page is appended
  - Legacy template formats (v1 spans, block divs) are handled
"""
import json
import re
from html.parser import HTMLParser

from django.test import TestCase

from apps.esigning.services import (
    generate_lease_html,
    _deduplicate_field_names,
    build_lease_context,
)
from apps.leases.models import LeaseTemplate
from apps.test_hub.base.test_case import TremlyAPITestCase
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.green]


# ── HTML Parsing Helpers ──────────────────────────────────────────────────

class SigningFieldExtractor(HTMLParser):
    """Extract all DocuSeal signing field tags from HTML."""

    FIELD_TAGS = {'signature-field', 'initials-field', 'date-field'}

    def __init__(self):
        super().__init__()
        self.fields = []

    def handle_starttag(self, tag, attrs):
        if tag in self.FIELD_TAGS:
            self.fields.append({
                'tag': tag,
                **dict(attrs),
            })

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def extract_signing_fields(html: str) -> list[dict]:
    """Parse HTML and return list of signing field dicts with tag name and attributes."""
    parser = SigningFieldExtractor()
    parser.feed(html)
    return parser.fields


def assert_has_field(fields: list[dict], *, tag: str, role: str, name_contains: str = None):
    """Assert that at least one field matches the given criteria."""
    for f in fields:
        if f['tag'] != tag:
            continue
        if f.get('role', '') != role:
            continue
        if name_contains and name_contains not in f.get('name', ''):
            continue
        return f
    criteria = f'tag={tag}, role={role}'
    if name_contains:
        criteria += f', name contains "{name_contains}"'
    raise AssertionError(
        f'No signing field matching ({criteria}) found.\n'
        f'Fields present: {json.dumps(fields, indent=2)}'
    )


# ── Template HTML Fixtures ────────────────────────────────────────────────

# v2 template: TipTap editor output with DocuSeal-native signing tags
V2_TEMPLATE_HTML = json.dumps({
    'v': 2,
    'html': (
        '<h1>Lease Agreement</h1>'
        '<p>Landlord: <span data-type="merge-field" data-field-name="landlord_name" '
        'class="merge-field">landlord_name</span></p>'
        '<p>Tenant: <span data-field-name="tenant_name" data-type="merge-field" '
        'class="merge-field">tenant_name</span></p>'
        '<p>Monthly Rent: {{monthly_rent}}</p>'
        '<p>Unit: {{unit_number}}</p>'
        '<div data-page-break="true"></div>'
        '<h2>Signatures</h2>'
        '<p>Landlord signs here: '
        '<signature-field name="landlord_signature_1" role="landlord" required="true" '
        'format="drawn_or_typed" data-field-type="signature" data-signer-role="landlord" '
        'data-field-name="landlord_signature_1" '
        'style="display:inline-block;width:200px;height:60px;margin:4px 6px;vertical-align:middle;"> </signature-field>'
        '</p>'
        '<p>Landlord initials: '
        '<initials-field name="landlord_initials_1" role="landlord" required="true" '
        'data-field-type="initials" data-signer-role="landlord" '
        'data-field-name="landlord_initials_1" '
        'style="display:inline-block;width:100px;height:40px;margin:4px 6px;vertical-align:middle;"> </initials-field>'
        '</p>'
        '<p>Landlord date: '
        '<date-field name="landlord_date_1" role="landlord" required="true" '
        'data-field-type="date" data-signer-role="landlord" '
        'data-field-name="landlord_date_1" '
        'style="display:inline-block;width:120px;height:24px;margin:4px 6px;vertical-align:middle;"> </date-field>'
        '</p>'
        '<p>Tenant signs here: '
        '<signature-field name="tenant_1_signature_1" role="tenant_1" required="true" '
        'format="drawn_or_typed" data-field-type="signature" data-signer-role="tenant_1" '
        'data-field-name="tenant_1_signature_1" '
        'style="display:inline-block;width:200px;height:60px;margin:4px 6px;vertical-align:middle;"> </signature-field>'
        '</p>'
        '<p>Tenant initials: '
        '<initials-field name="tenant_1_initials_1" role="tenant_1" required="true" '
        'data-field-type="initials" data-signer-role="tenant_1" '
        'data-field-name="tenant_1_initials_1" '
        'style="display:inline-block;width:100px;height:40px;margin:4px 6px;vertical-align:middle;"> </initials-field>'
        '</p>'
    ),
    'fields': [],
})

# v1 template with legacy merge field format
V1_TEMPLATE_HTML = json.dumps({
    'v': 1,
    'html': (
        '<h1>Lease Agreement</h1>'
        '<p>Landlord: <span data-merge-field="landlord_name">__</span></p>'
        '<p>Tenant: <span data-merge-field="tenant_name">__</span></p>'
        '<p>Rent: {{monthly_rent}}</p>'
        '<h2>Signatures</h2>'
        '<p><signature-field name="landlord_sig" role="landlord" required="true" '
        'format="drawn_or_typed" style="width:200px;height:60px;display:inline-block;"> </signature-field></p>'
        '<p><signature-field name="tenant_sig" role="tenant_1" required="true" '
        'format="drawn_or_typed" style="width:200px;height:60px;display:inline-block;"> </signature-field></p>'
    ),
    'fields': [],
})

# Template with NO signing fields at all
NO_SIGNING_TEMPLATE = json.dumps({
    'v': 2,
    'html': (
        '<h1>Lease Agreement</h1>'
        '<p>Landlord: <span data-type="merge-field" data-field-name="landlord_name">landlord_name</span></p>'
        '<p>Tenant: <span data-type="merge-field" data-field-name="tenant_name">tenant_name</span></p>'
        '<p>[Signatures to be added]</p>'
    ),
    'fields': [],
})

# Raw HTML (legacy, no JSON envelope)
RAW_HTML_TEMPLATE = (
    '<h1>Simple Lease</h1>'
    '<p>Landlord: {{landlord_name}}</p>'
    '<p>Tenant: {{tenant_name}}</p>'
    '<p><signature-field name="sig1" role="landlord" required="true" '
    'style="width:200px;height:60px;display:inline-block;"> </signature-field></p>'
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Signing Field Rendering
# ═══════════════════════════════════════════════════════════════════════════


class InlineSigningFieldTests(TremlyAPITestCase):
    """Verify inline signing fields are preserved and role-mapped in output HTML."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.tenant_person = self.create_person(
            full_name='Jane Tenant',
            id_number='9001015800085',
            phone='0821234567',
            email='jane@test.com',
        )
        self.lease = self.create_lease(
            unit=self.unit,
            primary_tenant=self.tenant_person,
        )

    def _make_template(self, content_html, name='Test Template'):
        return LeaseTemplate.objects.create(
            name=name,
            content_html=content_html,
            is_active=True,
        )

    def test_v2_signature_fields_preserved(self):
        """v2 template: signature-field tags survive the rendering pipeline."""
        tmpl = self._make_template(V2_TEMPLATE_HTML)
        html = generate_lease_html(self.lease, num_signers=2, template_id=tmpl.pk)
        fields = extract_signing_fields(html)

        # Should have signature, initials, date for landlord + signature, initials for tenant
        sig_fields = [f for f in fields if f['tag'] == 'signature-field']
        init_fields = [f for f in fields if f['tag'] == 'initials-field']
        date_fields = [f for f in fields if f['tag'] == 'date-field']

        self.assertGreaterEqual(len(sig_fields), 2, f'Expected >=2 signature fields, got {len(sig_fields)}')
        self.assertGreaterEqual(len(init_fields), 2, f'Expected >=2 initials fields, got {len(init_fields)}')
        self.assertGreaterEqual(len(date_fields), 1, f'Expected >=1 date field, got {len(date_fields)}')

    def test_v2_roles_preserved_for_native_signing(self):
        """Native signing: TipTap roles (landlord, tenant_1) are preserved in HTML."""
        tmpl = self._make_template(V2_TEMPLATE_HTML)
        html = generate_lease_html(self.lease, num_signers=2, template_id=tmpl.pk, native=True)
        fields = extract_signing_fields(html)

        # Native signing keeps original role names
        assert_has_field(fields, tag='signature-field', role='landlord')
        assert_has_field(fields, tag='initials-field', role='landlord')
        assert_has_field(fields, tag='signature-field', role='tenant_1')
        assert_has_field(fields, tag='initials-field', role='tenant_1')

    def test_v1_signing_fields_preserved(self):
        """v1 template with inline signing tags also works."""
        tmpl = self._make_template(V1_TEMPLATE_HTML)
        html = generate_lease_html(self.lease, num_signers=2, template_id=tmpl.pk)
        fields = extract_signing_fields(html)

        sig_fields = [f for f in fields if f['tag'] == 'signature-field']
        self.assertGreaterEqual(len(sig_fields), 2)

    def test_raw_html_signing_fields_preserved(self):
        """Legacy raw HTML templates (no JSON envelope) preserve signing tags."""
        tmpl = self._make_template(RAW_HTML_TEMPLATE)
        html = generate_lease_html(self.lease, num_signers=1, template_id=tmpl.pk, native=True)
        fields = extract_signing_fields(html)

        self.assertGreaterEqual(len(fields), 1)
        # Native signing: raw HTML preserves the original role attribute as-is
        roles = [f.get('role', '') for f in fields]
        self.assertTrue(any(roles), 'Expected at least one field with a role')

    def test_no_fallback_signature_page(self):
        """Templates without signing fields should NOT get a fallback signature page."""
        tmpl = self._make_template(NO_SIGNING_TEMPLATE)
        html = generate_lease_html(self.lease, num_signers=2, template_id=tmpl.pk)
        fields = extract_signing_fields(html)

        # No signing fields should be present — no fallback page
        self.assertEqual(len(fields), 0, 'Fallback signature page should not be generated')
        self.assertNotIn('page-break-before', html)

    def test_signing_field_attributes_complete(self):
        """Each signing field has all required DocuSeal attributes."""
        tmpl = self._make_template(V2_TEMPLATE_HTML)
        html = generate_lease_html(self.lease, num_signers=2, template_id=tmpl.pk)
        fields = extract_signing_fields(html)

        for f in fields:
            self.assertIn('name', f, f'Field missing name: {f}')
            self.assertIn('role', f, f'Field missing role: {f}')
            self.assertTrue(f.get('name'), f'Field has empty name: {f}')
            self.assertTrue(f.get('role'), f'Field has empty role: {f}')

            if f['tag'] == 'signature-field':
                self.assertEqual(f.get('format'), 'drawn_or_typed',
                                 f'Signature field missing format: {f}')

    def test_multiple_signers_role_mapping(self):
        """Native signing: with 3 signers, original role names are preserved."""
        html_content = json.dumps({
            'v': 2,
            'html': (
                '<p><signature-field name="ll_sig" role="landlord" data-field-type="signature" '
                'data-signer-role="landlord" style="width:200px;height:60px;display:inline-block;"> </signature-field></p>'
                '<p><signature-field name="t1_sig" role="tenant_1" data-field-type="signature" '
                'data-signer-role="tenant_1" style="width:200px;height:60px;display:inline-block;"> </signature-field></p>'
                '<p><signature-field name="t2_sig" role="tenant_2" data-field-type="signature" '
                'data-signer-role="tenant_2" style="width:200px;height:60px;display:inline-block;"> </signature-field></p>'
            ),
            'fields': [],
        })
        tmpl = self._make_template(html_content)
        html = generate_lease_html(self.lease, num_signers=3, template_id=tmpl.pk, native=True)
        fields = extract_signing_fields(html)

        roles = [f['role'] for f in fields]
        # Native signing: roles preserved as TipTap native roles
        self.assertIn('landlord', roles)
        self.assertIn('tenant_1', roles)
        self.assertIn('tenant_2', roles)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Merge Field Replacement
# ═══════════════════════════════════════════════════════════════════════════


class MergeFieldReplacementTests(TremlyAPITestCase):
    """Verify merge fields are replaced with lease context values."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent, name='Sunset Apartments')
        self.unit = self.create_unit(property_obj=self.prop, unit_number='42')
        self.tenant_person = self.create_person(
            full_name='Jane Tenant',
            id_number='9001015800085',
            phone='0821234567',
            email='jane@test.com',
        )
        self.lease = self.create_lease(
            unit=self.unit,
            primary_tenant=self.tenant_person,
        )

    def _make_template(self, content_html):
        return LeaseTemplate.objects.create(
            name='Test', content_html=content_html, is_active=True,
        )

    def test_v2_merge_fields_replaced(self):
        """v2 data-type="merge-field" spans are replaced with values."""
        tmpl = self._make_template(V2_TEMPLATE_HTML)
        html = generate_lease_html(self.lease, num_signers=2, template_id=tmpl.pk)

        # Should NOT contain the raw merge field spans
        self.assertNotIn('data-type="merge-field"', html)
        self.assertNotIn('data-field-name="landlord_name"', html)
        self.assertNotIn('data-field-name="tenant_name"', html)

        # Should contain the filled values
        self.assertIn('Jane Tenant', html)

    def test_v2_reverse_attribute_order(self):
        """v2 merge fields with data-field-name before data-type are also replaced."""
        html_content = json.dumps({
            'v': 2,
            'html': '<p><span data-field-name="tenant_name" data-type="merge-field">tenant_name</span></p>',
            'fields': [],
        })
        tmpl = self._make_template(html_content)
        html = generate_lease_html(self.lease, num_signers=1, template_id=tmpl.pk)

        self.assertNotIn('data-type="merge-field"', html)
        self.assertIn('Jane Tenant', html)

    def test_v1_merge_fields_replaced(self):
        """v1 data-merge-field spans are replaced."""
        tmpl = self._make_template(V1_TEMPLATE_HTML)
        html = generate_lease_html(self.lease, num_signers=1, template_id=tmpl.pk)

        self.assertNotIn('data-merge-field="landlord_name"', html)
        self.assertNotIn('data-merge-field="tenant_name"', html)
        self.assertIn('Jane Tenant', html)

    def test_mustache_placeholders_replaced(self):
        """{{field}} mustache markers are replaced with values."""
        tmpl = self._make_template(V2_TEMPLATE_HTML)
        html = generate_lease_html(self.lease, num_signers=1, template_id=tmpl.pk)

        # monthly_rent and unit_number are in the template as {{...}}
        self.assertNotIn('{{monthly_rent}}', html)
        self.assertNotIn('{{unit_number}}', html)
        self.assertIn('42', html)  # unit number
        self.assertIn('R ', html)  # rent formatting

    def test_unknown_merge_fields_show_placeholder(self):
        """Unknown merge fields show { field_name } placeholder."""
        html_content = json.dumps({
            'v': 2,
            'html': '<p><span data-type="merge-field" data-field-name="nonexistent_field">nonexistent_field</span></p>',
            'fields': [],
        })
        tmpl = self._make_template(html_content)
        html = generate_lease_html(self.lease, num_signers=1, template_id=tmpl.pk)

        # Should contain the fallback placeholder
        self.assertIn('{ nonexistent_field }', html)

    def test_raw_html_mustache_replaced(self):
        """Raw HTML (no JSON envelope) mustache fields are replaced."""
        tmpl = self._make_template(RAW_HTML_TEMPLATE)
        html = generate_lease_html(self.lease, num_signers=1, template_id=tmpl.pk)

        self.assertNotIn('{{landlord_name}}', html)
        self.assertNotIn('{{tenant_name}}', html)
        self.assertIn('Jane Tenant', html)


# ═══════════════════════════════════════════════════════════════════════════
# 3. Page Breaks & Document Structure
# ═══════════════════════════════════════════════════════════════════════════


class DocumentStructureTests(TremlyAPITestCase):
    """Verify HTML document structure, CSS, and page breaks."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.tenant_person = self.create_person(full_name='Test Tenant')
        self.lease = self.create_lease(
            unit=self.unit, primary_tenant=self.tenant_person,
        )

    def _make_template(self, content_html):
        return LeaseTemplate.objects.create(
            name='Test', content_html=content_html, is_active=True,
        )

    def test_output_is_valid_html5(self):
        """Output starts with DOCTYPE and has html/head/body structure."""
        tmpl = self._make_template(V2_TEMPLATE_HTML)
        html = generate_lease_html(self.lease, num_signers=2, template_id=tmpl.pk)

        self.assertTrue(html.startswith('<!DOCTYPE html>'))
        self.assertIn('<html>', html)
        self.assertIn('<head>', html)
        self.assertIn('<body>', html)
        self.assertIn('</body></html>', html)

    def test_css_included(self):
        """Output includes CSS for A4 page sizing and typography."""
        tmpl = self._make_template(V2_TEMPLATE_HTML)
        html = generate_lease_html(self.lease, num_signers=1, template_id=tmpl.pk)

        self.assertIn('@page', html)
        self.assertIn('A4', html)
        self.assertIn('font-family', html)

    def test_page_breaks_converted(self):
        """data-page-break divs are converted to CSS page-break-after."""
        tmpl = self._make_template(V2_TEMPLATE_HTML)
        html = generate_lease_html(self.lease, num_signers=1, template_id=tmpl.pk)

        self.assertNotIn('data-page-break', html)
        self.assertIn('page-break-after:always', html)

    def test_no_template_generates_table(self):
        """When no template exists, generates a simple key/value table."""
        # Ensure no templates exist
        LeaseTemplate.objects.all().delete()
        html = generate_lease_html(self.lease, num_signers=1)

        self.assertIn('<table', html)
        self.assertIn('Lease Agreement', html)


# ═══════════════════════════════════════════════════════════════════════════
# 4. (DocuSeal role-mapping tests removed — DocuSeal backend retired)
# ═══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
# 5. Build Lease Context
# ═══════════════════════════════════════════════════════════════════════════


class BuildLeaseContextTests(TremlyAPITestCase):
    """Verify build_lease_context() produces expected keys with real values."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent, name='Ocean View')
        self.unit = self.create_unit(property_obj=self.prop, unit_number='7B')
        self.landlord = self.create_landlord()
        self.bank = self.create_bank_account(landlord=self.landlord)
        self.ownership = self.create_property_ownership(
            property_obj=self.prop, landlord=self.landlord,
        )
        self.tenant_person = self.create_person(
            full_name='Alice Smith',
            id_number='8801015800085',
            phone='0829876543',
            email='alice@test.com',
        )
        self.lease = self.create_lease(
            unit=self.unit,
            primary_tenant=self.tenant_person,
        )

    def test_context_has_required_keys(self):
        ctx = build_lease_context(self.lease)

        required_keys = [
            'landlord_name', 'landlord_contact', 'landlord_email',
            'landlord_entity_name', 'landlord_registration_no', 'landlord_vat_no',
            'landlord_representative', 'landlord_physical_address',
            'landlord_bank_name', 'landlord_bank_account_no',
            'landlord_bank_branch_code', 'landlord_bank_account_holder',
            'tenant_name', 'tenant_id', 'tenant_phone', 'tenant_email',
            'tenant_1_name', 'tenant_1_id', 'tenant_1_phone', 'tenant_1_email',
            'property_address', 'property_name', 'unit_number',
            'lease_start', 'lease_end', 'monthly_rent', 'deposit',
        ]
        for key in required_keys:
            self.assertIn(key, ctx, f'Missing context key: {key}')
            # Verify landlord/bank keys have real values, not just em-dash fallbacks
            if 'landlord' in key or 'bank' in key:
                self.assertNotEqual(ctx[key], '—', f'{key} should have a real value, got em-dash')

    def test_tenant_values_filled(self):
        ctx = build_lease_context(self.lease)

        self.assertEqual(ctx['tenant_name'], 'Alice Smith')
        self.assertEqual(ctx['tenant_1_name'], 'Alice Smith')
        self.assertEqual(ctx['tenant_email'], 'alice@test.com')
        self.assertEqual(ctx['unit_number'], '7B')
        self.assertEqual(ctx['property_name'], 'Ocean View')

    def test_missing_tenant_slots_filled_with_dash(self):
        ctx = build_lease_context(self.lease)

        # No co-tenants, so tenant_2 and tenant_3 slots should be em-dash
        self.assertEqual(ctx['tenant_2_name'], '—')
        self.assertEqual(ctx['tenant_3_name'], '—')


# ═══════════════════════════════════════════════════════════════════════════
# 5b. Landlord & Banking Merge Field Population
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.green
@pytest.mark.integration
class LandlordBankingMergeFieldTests(TremlyAPITestCase):
    """Verify landlord & banking merge fields populate with REAL values.

    The previous test (BuildLeaseContextTests.test_context_has_required_keys)
    only checked key existence, not actual values. This class verifies the full
    data chain: PropertyOwnership → Landlord → BankAccount → merge field values.
    """

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent, name='Landlord Test Property')
        self.unit = self.create_unit(property_obj=self.prop, unit_number='5A')
        self.landlord = self.create_landlord(
            name='Bosch En Dal Properties (Pty) Ltd',
            email='info@boschdal.co.za',
            phone='0211234567',
            registration_number='2019/456789/07',
            vat_number='4987654321',
            representative_name='Marius de Villiers',
            representative_id_number='7501015800085',
            representative_email='marius@boschdal.co.za',
            representative_phone='0829998877',
            address={'street': '45 Stellenbosch Ave', 'city': 'Stellenbosch', 'province': 'Western Cape', 'postal_code': '7600'},
        )
        self.bank = self.create_bank_account(
            landlord=self.landlord,
            bank_name='First National Bank',
            branch_code='250655',
            account_number='62098765432',
            account_type='Cheque',
            account_holder='Bosch En Dal Properties (Pty) Ltd',
        )
        self.ownership = self.create_property_ownership(
            property_obj=self.prop,
            landlord=self.landlord,
            owner_name='Bosch En Dal Properties (Pty) Ltd',
        )
        self.tenant = self.create_person(
            full_name='Alice Tenant',
            email='alice@test.com',
            phone='0831112222',
            id_number='9001015800085',
        )
        self.lease = self.create_lease(unit=self.unit, primary_tenant=self.tenant)

    # ── Landlord identity fields ──

    def test_landlord_name_is_legal_entity_name(self):
        """landlord_name must be the legal entity name, NOT the representative."""
        ctx = build_lease_context(self.lease)
        self.assertEqual(ctx['landlord_name'], 'Bosch En Dal Properties (Pty) Ltd')

    def test_landlord_email_populated(self):
        ctx = build_lease_context(self.lease)
        self.assertEqual(ctx['landlord_email'], 'marius@boschdal.co.za')

    def test_landlord_contact_populated(self):
        ctx = build_lease_context(self.lease)
        self.assertEqual(ctx['landlord_contact'], '0829998877')

    def test_landlord_entity_name_populated(self):
        ctx = build_lease_context(self.lease)
        self.assertEqual(ctx['landlord_entity_name'], 'Bosch En Dal Properties (Pty) Ltd')

    def test_landlord_registration_no_populated(self):
        ctx = build_lease_context(self.lease)
        self.assertEqual(ctx['landlord_registration_no'], '2019/456789/07')

    def test_landlord_vat_no_populated(self):
        ctx = build_lease_context(self.lease)
        self.assertEqual(ctx['landlord_vat_no'], '4987654321')

    def test_landlord_representative_populated(self):
        ctx = build_lease_context(self.lease)
        self.assertEqual(ctx['landlord_representative'], 'Marius de Villiers')

    def test_landlord_representative_id_populated(self):
        ctx = build_lease_context(self.lease)
        self.assertEqual(ctx['landlord_representative_id'], '7501015800085')

    def test_landlord_physical_address_populated(self):
        ctx = build_lease_context(self.lease)
        self.assertIn('Stellenbosch', ctx['landlord_physical_address'])
        self.assertNotEqual(ctx['landlord_physical_address'], '—')

    # ── Banking fields ──

    def test_bank_name_populated(self):
        ctx = build_lease_context(self.lease)
        self.assertEqual(ctx['landlord_bank_name'], 'First National Bank')

    def test_bank_account_no_populated(self):
        ctx = build_lease_context(self.lease)
        self.assertEqual(ctx['landlord_bank_account_no'], '62098765432')

    def test_bank_branch_code_populated(self):
        ctx = build_lease_context(self.lease)
        self.assertEqual(ctx['landlord_bank_branch_code'], '250655')

    def test_bank_account_holder_populated(self):
        ctx = build_lease_context(self.lease)
        self.assertEqual(ctx['landlord_bank_account_holder'], 'Bosch En Dal Properties (Pty) Ltd')

    def test_bank_account_type_populated(self):
        ctx = build_lease_context(self.lease)
        self.assertEqual(ctx['landlord_bank_account_type'], 'Cheque')

    # ── Fallback behaviour ──

    def test_without_ownership_falls_back_to_dash(self):
        """No PropertyOwnership → all landlord/bank fields default to em-dash."""
        self.ownership.delete()
        ctx = build_lease_context(self.lease)
        self.assertEqual(ctx['landlord_name'], '—')
        self.assertEqual(ctx['landlord_bank_name'], '—')
        self.assertEqual(ctx['landlord_bank_account_no'], '—')

    def test_without_bank_account_falls_back_to_dash(self):
        """Landlord exists but no BankAccount → bank fields default to em-dash."""
        self.bank.delete()
        ctx = build_lease_context(self.lease)
        # Landlord fields should still populate
        self.assertNotEqual(ctx['landlord_name'], '—')
        # Bank fields should fall back to em-dash
        self.assertEqual(ctx['landlord_bank_name'], '—')
        self.assertEqual(ctx['landlord_bank_account_no'], '—')


# ═══════════════════════════════════════════════════════════════════════════
# 6. End-to-End Rendering Validation
# ═══════════════════════════════════════════════════════════════════════════


class EndToEndRenderingTests(TremlyAPITestCase):
    """Full pipeline test: template → generate_lease_html → validate output."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent, name='Harbour Heights')
        self.unit = self.create_unit(property_obj=self.prop, unit_number='12A')
        self.tenant_person = self.create_person(
            full_name='Bob Builder',
            id_number='7501015800085',
            phone='0831112222',
            email='bob@test.com',
        )
        self.lease = self.create_lease(
            unit=self.unit,
            primary_tenant=self.tenant_person,
        )

    def test_full_v2_pipeline(self):
        """Complete v2 template renders with fields replaced and signing tags intact."""
        tmpl = LeaseTemplate.objects.create(
            name='Full Test', content_html=V2_TEMPLATE_HTML, is_active=True,
        )
        html = generate_lease_html(self.lease, num_signers=2, template_id=tmpl.pk, native=True)

        # 1. Document structure
        self.assertTrue(html.startswith('<!DOCTYPE html>'))

        # 2. Merge fields replaced — tenant_name is populated from fixture
        self.assertIn('Bob Builder', html)  # tenant_name resolved
        # Landlord merge field may remain unreplaced if no landlord in fixture; that's OK

        # 3. Mustache fields replaced
        self.assertNotIn('{{monthly_rent}}', html)
        self.assertNotIn('{{unit_number}}', html)
        self.assertIn('12A', html)

        # 4. Signing fields present with native roles (DocuSeal removed)
        fields = extract_signing_fields(html)
        self.assertGreaterEqual(len(fields), 4)  # 2 sig + 2 init minimum

        roles = {f['role'] for f in fields}
        self.assertIn('landlord', roles)
        self.assertIn('tenant_1', roles)

        # 5. All signature fields have required attrs
        for f in fields:
            self.assertTrue(f.get('name'), f'Missing name: {f}')
            self.assertTrue(f.get('role'), f'Missing role: {f}')
            if f['tag'] == 'signature-field':
                self.assertEqual(f.get('format'), 'drawn_or_typed')

        # 6. Page break converted
        self.assertIn('page-break-after:always', html)
        self.assertNotIn('data-page-break', html)

        # 7. No fallback signature page
        self.assertNotIn('Signatures</h1>', html)  # fallback page heading

    def test_field_count_summary(self):
        """Print a summary of all signing fields found (useful for debugging)."""
        tmpl = LeaseTemplate.objects.create(
            name='Summary Test', content_html=V2_TEMPLATE_HTML, is_active=True,
        )
        html = generate_lease_html(self.lease, num_signers=2, template_id=tmpl.pk)
        fields = extract_signing_fields(html)

        summary = {
            'total': len(fields),
            'signature': len([f for f in fields if f['tag'] == 'signature-field']),
            'initials': len([f for f in fields if f['tag'] == 'initials-field']),
            'date': len([f for f in fields if f['tag'] == 'date-field']),
            'roles': list({f['role'] for f in fields}),
            'field_names': [f.get('name', '?') for f in fields],
        }

        # Assertions on the summary
        self.assertGreater(summary['total'], 0, f'No signing fields found! Summary: {summary}')
        self.assertGreater(summary['signature'], 0, f'No signature fields! Summary: {summary}')
        self.assertGreater(summary['initials'], 0, f'No initials fields! Summary: {summary}')


# ═══════════════════════════════════════════════════════════════════════════
# 7. Field Name Deduplication
# ═══════════════════════════════════════════════════════════════════════════


class FieldDeduplicationUnitTests(TestCase):
    """Unit tests for _deduplicate_field_names()."""

    def test_unique_names_unchanged(self):
        html = (
            '<signature-field name="sig_1" role="First Party"> </signature-field>'
            '<signature-field name="sig_2" role="Signer 2"> </signature-field>'
        )
        result = _deduplicate_field_names(html)
        self.assertIn('name="sig_1"', result)
        self.assertIn('name="sig_2"', result)

    def test_duplicate_names_get_suffix(self):
        html = (
            '<initials-field name="ll_init" role="First Party"> </initials-field>'
            '<initials-field name="ll_init" role="First Party"> </initials-field>'
            '<initials-field name="ll_init" role="First Party"> </initials-field>'
        )
        result = _deduplicate_field_names(html)
        self.assertIn('name="ll_init"', result)      # first unchanged
        self.assertIn('name="ll_init_2"', result)
        self.assertIn('name="ll_init_3"', result)

    def test_data_field_name_also_updated(self):
        html = '<initials-field name="x" data-field-name="x"> </initials-field><initials-field name="x" data-field-name="x"> </initials-field>'
        result = _deduplicate_field_names(html)
        self.assertIn('data-field-name="x_2"', result)

    def test_different_field_types_independent(self):
        html = (
            '<signature-field name="ll_sig" role="First Party"> </signature-field>'
            '<initials-field name="ll_init" role="First Party"> </initials-field>'
            '<signature-field name="ll_sig" role="First Party"> </signature-field>'
            '<initials-field name="ll_init" role="First Party"> </initials-field>'
        )
        result = _deduplicate_field_names(html)
        self.assertIn('name="ll_sig"', result)
        self.assertIn('name="ll_sig_2"', result)
        self.assertIn('name="ll_init"', result)
        self.assertIn('name="ll_init_2"', result)

    def test_non_signing_tags_untouched(self):
        html = '<p name="test">text</p><initials-field name="x"> </initials-field>'
        result = _deduplicate_field_names(html)
        self.assertIn('<p name="test">', result)

    def test_10_duplicates(self):
        """Simulates template 35: same initials name repeated 10 times."""
        html = '<initials-field name="ll_init" role="First Party"> </initials-field>' * 10
        result = _deduplicate_field_names(html)
        names = re.findall(r'name="([^"]+)"', result)
        self.assertEqual(len(names), 10)
        self.assertEqual(len(set(names)), 10, f'Not all unique: {names}')


class FieldDeduplicationIntegrationTests(TremlyAPITestCase):
    """Integration test: deduplication through generate_lease_html()."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.tenant_person = self.create_person(full_name='Test Tenant')
        self.lease = self.create_lease(
            unit=self.unit, primary_tenant=self.tenant_person,
        )

    def test_repeated_initials_are_deduplicated(self):
        """Template with repeated initials names produces all unique names."""
        html_content = json.dumps({
            'v': 2,
            'html': (
                '<p><initials-field name="ll_init" role="landlord" required="true" '
                'style="display:inline-block;width:100px;height:40px;"> </initials-field></p>'
                '<p><initials-field name="ll_init" role="landlord" required="true" '
                'style="display:inline-block;width:100px;height:40px;"> </initials-field></p>'
                '<p><initials-field name="ll_init" role="landlord" required="true" '
                'style="display:inline-block;width:100px;height:40px;"> </initials-field></p>'
                '<p><signature-field name="ll_sig" role="landlord" required="true" format="drawn_or_typed" '
                'style="display:inline-block;width:200px;height:60px;"> </signature-field></p>'
            ),
            'fields': [],
        })
        tmpl = LeaseTemplate.objects.create(
            name='Dedup Test', content_html=html_content, is_active=True,
        )
        html = generate_lease_html(self.lease, num_signers=1, template_id=tmpl.pk)
        fields = extract_signing_fields(html)

        names = [f['name'] for f in fields]
        self.assertEqual(len(names), 4)
        self.assertEqual(len(set(names)), 4, f'Duplicate names found: {names}')


# ═══════════════════════════════════════════════════════════════════════════
# 8. Signing Builder Consistency (Page Layout CSS)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.integration
@pytest.mark.green
class SigningBuilderConsistencyTests(TremlyAPITestCase):
    """Verify generated HTML has correct A4 page sizing, margins, and page-break CSS."""

    def setUp(self):
        self.agent = self.create_agent()
        self.prop = self.create_property(agent=self.agent)
        self.unit = self.create_unit(property_obj=self.prop)
        self.tenant_person = self.create_person(
            full_name='Test Tenant',
            id_number='9001015800085',
            phone='0821234567',
            email='tenant@test.com',
        )
        self.lease = self.create_lease(
            unit=self.unit,
            primary_tenant=self.tenant_person,
        )

    def _make_template(self, content_html):
        return LeaseTemplate.objects.create(
            name='Consistency Test', content_html=content_html, is_active=True,
        )

    def test_generated_html_page_size_is_a4(self):
        """generate_lease_html() output contains @page rule with size: A4."""
        tmpl = self._make_template(V2_TEMPLATE_HTML)
        html = generate_lease_html(self.lease, num_signers=2, template_id=tmpl.pk)

        # Find the @page rule and verify it sets A4 size
        self.assertIn('@page', html)
        # Extract the @page block and check for A4
        page_match = re.search(r'@page\s*\{[^}]*\}', html)
        self.assertIsNotNone(page_match, '@page rule not found in generated HTML')
        page_rule = page_match.group()
        self.assertIn('A4', page_rule, f'@page rule does not specify A4 size: {page_rule}')

    def test_generated_html_has_page_margins(self):
        """@page rule includes margin values from pdf_settings (matching TipTap)."""
        from apps.esigning.pdf_settings import MARGIN_TOP_MM, MARGIN_BOTTOM_MM, MARGIN_LEFT_MM, MARGIN_RIGHT_MM

        tmpl = self._make_template(V2_TEMPLATE_HTML)
        html = generate_lease_html(self.lease, num_signers=2, template_id=tmpl.pk)

        page_match = re.search(r'@page\s*\{[^}]*\}', html)
        self.assertIsNotNone(page_match, '@page rule not found in generated HTML')
        page_rule = page_match.group()
        self.assertIn('margin', page_rule, f'@page rule has no margin: {page_rule}')
        # Verify margins match shared pdf_settings (aligned with tiptapSettings.ts)
        self.assertIn(f'{MARGIN_TOP_MM}mm', page_rule, f'Missing top margin in @page: {page_rule}')
        self.assertIn(f'{MARGIN_RIGHT_MM}mm', page_rule, f'Missing right margin in @page: {page_rule}')
        self.assertIn(f'{MARGIN_BOTTOM_MM}mm', page_rule, f'Missing bottom margin in @page: {page_rule}')
        self.assertIn(f'{MARGIN_LEFT_MM}mm', page_rule, f'Missing left margin in @page: {page_rule}')

    def test_generated_html_has_page_break_css(self):
        """page-break-after:always is present when template has page breaks."""
        tmpl = self._make_template(V2_TEMPLATE_HTML)
        html = generate_lease_html(self.lease, num_signers=2, template_id=tmpl.pk)

        # V2_TEMPLATE_HTML contains data-page-break="true" which should be
        # converted to page-break-after:always in the output
        self.assertIn('page-break-after:always', html,
                       'Expected page-break-after:always in output for template with page breaks')
