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
