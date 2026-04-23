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
        """Legacy role="landlord" in HTML matches signer_role="landlord".

        _role_to_tiptap maps 'Landlord' / 'lessor' → 'landlord' (unsuffixed),
        which is the canonical tiptap landlord role used throughout the system
        (see SignatureBlockNode.ts).  This test mirrors the production call
        contract: create_native_submission stores role='landlord' in the signer
        record, then extract_signer_fields is called with 'landlord'.

        Also covers the lessor alias path: both 'landlord' and 'lessor' in HTML
        must resolve to the same canonical 'landlord' so that either input
        produces fields for a landlord signer.
        """
        from apps.esigning.services import extract_signer_fields
        # Standard legacy landlord field
        html = (
            '<signature-field name="ll_sig" role="landlord" required="true" '
            'format="drawn_or_typed" style="display:inline-block;width:200px;height:60px"> </signature-field>'
            # Lessor is an alias for landlord — must also match
            '<initials-field name="ll_init" role="lessor" required="true" '
            'style="display:inline-block;width:100px;height:40px"> </initials-field>'
        )
        # signer record carries 'landlord' — exactly what _role_to_tiptap produces
        fields = extract_signer_fields(html, 'landlord')
        assert len(fields) == 2, (
            "Expected 2 fields (signature + initials) for landlord signer "
            "when HTML uses legacy role='landlord' / role='lessor'"
        )
        field_names = {f['fieldName'] for f in fields}
        assert 'll_sig' in field_names
        assert 'll_init' in field_names

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

    def test_div_signature_block_converted(self):
        """_convert_legacy_signing_span must handle <div data-type="signature-block"> elements.

        Template 57 stores signature blocks as <div> not <span>.  The regex at
        services.py must match both element names so that extract_signer_fields
        returns fields for submissions built from those templates.
        """
        import re
        from apps.esigning.services import _HTML_ROLE_CANONICAL

        # Replicate the exact regex + callback from generate_lease_html so we can
        # exercise it without a DB-backed Lease fixture.
        def _convert(m: re.Match) -> str:
            attrs_str = m.group(2)
            field_type = re.search(r'data-field-type="([^"]+)"', attrs_str)
            field_name = re.search(r'data-field-name="([^"]+)"', attrs_str)
            signer_role = re.search(r'data-signer-role="([^"]+)"', attrs_str)
            ftype = field_type.group(1) if field_type else 'signature'
            fname = field_name.group(1) if field_name else ''
            role = signer_role.group(1) if signer_role else 'landlord'
            role = _HTML_ROLE_CANONICAL.get(role.lower(), role)
            tag_map = {'signature': 'signature-field', 'initials': 'initials-field', 'date': 'date-field'}
            tag = tag_map.get(ftype, 'signature-field')
            dims = {'signature': 'width:200px;height:60px', 'initials': 'width:100px;height:40px',
                    'date': 'width:120px;height:24px'}.get(ftype, 'width:200px;height:60px')
            fmt = ' format="drawn_or_typed"' if ftype == 'signature' else ''
            return (f'<{tag} name="{fname}" role="{role}" required="true"{fmt} '
                    f'style="display:inline-block;{dims};margin:4px 6px;vertical-align:middle;"> </{tag}>')

        # Simulate template 57 HTML with <div> signature blocks
        raw_html = (
            '<div data-type="signature-block" data-field-name="tenant_sig" '
            'data-field-type="signature" data-signer-role="tenant">{{tenant_sig}}</div>'
            '<div data-type="signature-block" data-field-name="tenant_init" '
            'data-field-type="initials" data-signer-role="tenant">{{tenant_init}}</div>'
        )
        converted = re.sub(
            r'<(span|div)([^>]+data-type="signature-block"[^>]*)>.*?</\1>',
            _convert, raw_html, flags=re.DOTALL,
        )

        assert '<signature-field' in converted, "signature-field tag not produced from <div> block"
        assert '<initials-field' in converted, "initials-field tag not produced from <div> block"
        assert 'role="tenant_1"' in converted, "tenant alias not normalised to tenant_1"
        assert 'name="tenant_sig"' in converted
        assert 'name="tenant_init"' in converted
        # Originals must be gone
        assert 'data-type="signature-block"' not in converted

        # Round-trip: extract_signer_fields must now find both fields for tenant_1 signer
        from apps.esigning.services import extract_signer_fields
        fields = extract_signer_fields(converted, 'tenant_1')
        assert len(fields) == 2, (
            f"Expected 2 fields for tenant_1 after <div> conversion, got {len(fields)}"
        )

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
