"""
Unit tests for key service functions in apps/esigning/services.py.

All DocuSeal API calls are mocked.
"""
import pytest
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.unit


class TestGenerateLeaseHtml:
    """generate_lease_html(): renders HTML containing lease data."""

    @pytest.mark.red
    def test_returns_html_string_with_tenant_name(self):
        """RED: generate_lease_html() returns an HTML string containing the tenant name.

        This test requires a DB-backed Lease and LeaseTemplate. It is marked red
        because it crosses into integration territory. Move to integration/ once
        the test factory is accessible from unit tests.
        """
        raise NotImplementedError(
            "Use TremlyAPITestCase.create_lease() + LeaseTemplate to test generate_lease_html. "
            "See apps/test_hub/esigning/integration/test_html_rendering.py for full coverage."
        )

    # DocuSeal backend removed — _docuseal_headers, _docuseal_base, _map_signing_roles tests deleted


class TestDeduplicateFieldNames:
    """_deduplicate_field_names(): makes signing field name attributes unique."""

    def test_unique_names_unchanged(self):
        from apps.esigning.services import _deduplicate_field_names
        html = (
            '<signature-field name="sig_1" role="First Party"> </signature-field>'
            '<signature-field name="sig_2" role="Signer 2"> </signature-field>'
        )
        result = _deduplicate_field_names(html)
        assert 'name="sig_1"' in result
        assert 'name="sig_2"' in result

    def test_duplicate_names_get_suffix(self):
        from apps.esigning.services import _deduplicate_field_names
        html = (
            '<initials-field name="ll_init" role="First Party"> </initials-field>'
            '<initials-field name="ll_init" role="First Party"> </initials-field>'
        )
        result = _deduplicate_field_names(html)
        assert 'name="ll_init"' in result
        assert 'name="ll_init_2"' in result

class TestExtractSignerFields:
    """extract_signer_fields(): finds signing fields in rendered HTML."""

    def test_explicit_tenant_1_role_matched(self):
        """Fields with role="tenant_1" are returned when querying tenant_1."""
        from apps.esigning.services import extract_signer_fields
        html = (
            '<signature-field name="sig_t1" role="tenant_1" required="true" '
            'format="drawn_or_typed" style="display:inline-block;width:200px;height:60px"> </signature-field>'
        )
        fields = extract_signer_fields(html, 'tenant_1')
        assert len(fields) == 1
        assert fields[0]['fieldName'] == 'sig_t1'

    def test_extract_signer_fields_tenant_alias(self):
        """Signer record has role=tenant_1 but HTML uses legacy role="tenant".

        extract_signer_fields must treat "tenant" as an alias for "tenant_1"
        so that templates saved before role normalisation are still usable.
        """
        from apps.esigning.services import extract_signer_fields
        # HTML produced by legacy templates that stored data-signer-role="tenant"
        html = (
            '<signature-field name="tenant_sig" role="tenant" required="true" '
            'format="drawn_or_typed" style="display:inline-block;width:200px;height:60px"> </signature-field>'
            '<initials-field name="tenant_init" role="tenant" required="true" '
            'style="display:inline-block;width:100px;height:40px"> </initials-field>'
        )
        # The signer record carries the canonical tiptap role "tenant_1"
        fields = extract_signer_fields(html, 'tenant_1')
        assert len(fields) == 2, (
            "Expected 2 fields (signature + initials) for tenant_1 signer "
            "when HTML uses legacy role='tenant'"
        )
        field_names = {f['fieldName'] for f in fields}
        assert 'tenant_sig' in field_names
        assert 'tenant_init' in field_names

    def test_landlord_alias_matched(self):
        """Legacy role="landlord" in HTML matches signer_role="landlord_1"."""
        from apps.esigning.services import extract_signer_fields
        html = (
            '<signature-field name="ll_sig" role="landlord" required="true" '
            'format="drawn_or_typed" style="display:inline-block;width:200px;height:60px"> </signature-field>'
        )
        fields = extract_signer_fields(html, 'landlord_1')
        assert len(fields) == 1
        assert fields[0]['fieldName'] == 'll_sig'

    def test_no_cross_role_contamination(self):
        """Fields for tenant must not appear when querying landlord_1."""
        from apps.esigning.services import extract_signer_fields
        html = (
            '<signature-field name="t_sig" role="tenant_1" required="true" '
            'format="drawn_or_typed" style="display:inline-block;"> </signature-field>'
            '<signature-field name="ll_sig" role="landlord_1" required="true" '
            'format="drawn_or_typed" style="display:inline-block;"> </signature-field>'
        )
        tenant_fields = extract_signer_fields(html, 'tenant_1')
        landlord_fields = extract_signer_fields(html, 'landlord_1')
        assert len(tenant_fields) == 1 and tenant_fields[0]['fieldName'] == 't_sig'
        assert len(landlord_fields) == 1 and landlord_fields[0]['fieldName'] == 'll_sig'

    @pytest.mark.red
    def test_extract_editable_merge_fields_returns_field_names(self):
        """RED: extract_editable_merge_fields() extracts field names from HTML template.

        This test requires reading the function signature from services.py.
        It is marked red for verification.
        """
        raise NotImplementedError(
            "Verify extract_editable_merge_fields() function signature in services.py "
            "and test that it returns a list of field name strings from HTML content."
        )
