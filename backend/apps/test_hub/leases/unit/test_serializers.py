"""Unit tests for leases serializers — field presence and validation logic."""
import pytest
from datetime import date
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# LeaseSerializer
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_lease_serializer_required_fields():
    """LeaseSerializer should expose all core lease fields."""
    from apps.leases.serializers import LeaseSerializer
    field_names = set(LeaseSerializer().fields.keys())
    required = {"unit", "start_date", "end_date", "monthly_rent", "deposit", "status"}
    assert required.issubset(field_names)


@pytest.mark.green
def test_lease_serializer_computed_fields():
    """LeaseSerializer must include computed/read-only convenience fields."""
    from apps.leases.serializers import LeaseSerializer
    field_names = set(LeaseSerializer().fields.keys())
    assert "tenant_name" in field_names
    assert "all_tenant_names" in field_names
    assert "document_count" in field_names
    assert "unit_label" in field_names


@pytest.mark.red
def test_lease_serializer_rejects_end_before_start():
    """
    RED: LeaseSerializer currently does not validate that end_date > start_date.
    This test documents the missing validation — once a validate() method is added
    it should raise a ValidationError and this test should be flipped to green.
    """
    from apps.leases.serializers import LeaseSerializer

    data = {
        "unit": 1,
        "start_date": date(2027, 1, 1),
        "end_date": date(2026, 1, 1),
        "monthly_rent": "5000.00",
        "deposit": "10000.00",
    }
    serializer = LeaseSerializer(data=data)
    # Currently is_valid() returns True for this invalid data (no cross-field validation)
    # When validation is added, change this assertion to assertFalse + check error keys.
    # serializer.is_valid()
    # This test intentionally documents the gap without asserting the wrong thing.
    assert False, "Gap documented: LeaseSerializer missing end_date > start_date validation"


# ---------------------------------------------------------------------------
# LeaseTemplateSerializer
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_lease_template_serializer_exposes_content_html():
    """LeaseTemplateSerializer must expose content_html field."""
    from apps.leases.serializers import LeaseTemplateSerializer
    field_names = set(LeaseTemplateSerializer().fields.keys())
    assert "content_html" in field_names


@pytest.mark.green
def test_lease_template_serializer_exposes_detected_variables():
    """LeaseTemplateSerializer must include detected_variables (computed)."""
    from apps.leases.serializers import LeaseTemplateSerializer
    field_names = set(LeaseTemplateSerializer().fields.keys())
    assert "detected_variables" in field_names


@pytest.mark.green
def test_lease_template_serializer_readonly_fields():
    """created_at and updated_at must be read-only."""
    from apps.leases.serializers import LeaseTemplateSerializer
    s = LeaseTemplateSerializer()
    assert s.fields["created_at"].read_only
    assert s.fields["updated_at"].read_only


# ---------------------------------------------------------------------------
# ReusableClauseSerializer
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_reusable_clause_serializer_required_fields():
    """ReusableClauseSerializer must expose title, category, and html."""
    from apps.leases.serializers import ReusableClauseSerializer
    field_names = set(ReusableClauseSerializer().fields.keys())
    assert "title" in field_names
    assert "category" in field_names
    assert "html" in field_names


@pytest.mark.green
def test_reusable_clause_serializer_readonly_fields():
    """use_count and created_at must be read-only in ReusableClauseSerializer."""
    from apps.leases.serializers import ReusableClauseSerializer
    s = ReusableClauseSerializer()
    assert s.fields["use_count"].read_only
    assert s.fields["created_at"].read_only


@pytest.mark.green
def test_reusable_clause_serializer_title_required():
    """
    RED: Verify that ReusableClauseSerializer rejects empty title.
    Marked red because the field is a plain CharField — we need to check
    whether allow_blank=False is enforced (it should be by default).
    """
    from apps.leases.serializers import ReusableClauseSerializer
    data = {"title": "", "category": "general", "html": "<p>Content</p>"}
    s = ReusableClauseSerializer(data=data)
    # Default CharField does not allow blank — expect is_valid() == False
    # If this assertion fails, title allows blank and validation needs tightening.
    is_valid = s.is_valid()
    assert not is_valid, "title should be required (non-blank)"


# ---------------------------------------------------------------------------
# _detect_and_group helper
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_detect_and_group_landlord_prefix():
    """_detect_and_group groups landlord_* merge fields under 'landlord'."""
    from apps.leases.serializers import _detect_and_group
    html = '<span data-merge-field="landlord_name">X</span>'
    result = _detect_and_group(html)
    assert "landlord" in result
    assert "landlord_name" in result["landlord"]


@pytest.mark.green
def test_detect_and_group_empty_html():
    """_detect_and_group returns empty dict for empty HTML."""
    from apps.leases.serializers import _detect_and_group
    assert _detect_and_group("") == {}
    assert _detect_and_group(None) == {}


@pytest.mark.green
def test_detect_and_group_deduplicates():
    """_detect_and_group should not produce duplicate field names."""
    from apps.leases.serializers import _detect_and_group
    html = (
        '<span data-merge-field="tenant_name">A</span>'
        '<span data-merge-field="tenant_name">B</span>'
    )
    result = _detect_and_group(html)
    all_fields = [f for group in result.values() for f in group]
    assert all_fields.count("tenant_name") == 1
