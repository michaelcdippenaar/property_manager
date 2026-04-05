"""
Unit tests for maintenance models.

Tests run without database access where possible (using model instantiation only).
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock

pytestmark = pytest.mark.unit


class TestMaintenanceRequestStr:
    """MaintenanceRequest.__str__ and choice fields."""

    def test_str_returns_title_and_unit(self):
        from apps.maintenance.models import MaintenanceRequest
        from django.db.models.base import ModelState
        mr = MaintenanceRequest.__new__(MaintenanceRequest)
        mr._state = ModelState()
        mr.title = "Leaking tap"
        unit_mock = MagicMock()
        unit_mock.__str__ = lambda self: "Unit 3A"
        mr._state.fields_cache["unit"] = unit_mock
        assert "Leaking tap" in str(mr)

    def test_priority_choices_exist(self):
        from apps.maintenance.models import MaintenanceRequest
        choices = [c[0] for c in MaintenanceRequest.Priority.choices]
        assert "low" in choices
        assert "medium" in choices
        assert "high" in choices
        assert "urgent" in choices

    def test_status_choices_exist(self):
        from apps.maintenance.models import MaintenanceRequest
        choices = [c[0] for c in MaintenanceRequest.Status.choices]
        assert "open" in choices
        assert "in_progress" in choices
        assert "resolved" in choices
        assert "closed" in choices

    def test_category_choices_exist(self):
        from apps.maintenance.models import MaintenanceRequest
        choices = [c[0] for c in MaintenanceRequest.Category.choices]
        assert "plumbing" in choices
        assert "electrical" in choices
        assert "other" in choices

    def test_default_priority_is_medium(self):
        from apps.maintenance.models import MaintenanceRequest
        assert MaintenanceRequest.Priority.MEDIUM == "medium"

    def test_default_status_is_open(self):
        from apps.maintenance.models import MaintenanceRequest
        assert MaintenanceRequest.Status.OPEN == "open"


class TestSupplierStr:
    """Supplier.__str__ and trade fields."""

    def test_str_returns_name_when_no_company(self):
        from apps.maintenance.models import Supplier
        supplier = Supplier.__new__(Supplier)
        supplier.name = "Bob the Builder"
        supplier.company_name = ""
        assert str(supplier) == "Bob the Builder"

    def test_str_returns_company_and_name_when_company_set(self):
        from apps.maintenance.models import Supplier
        supplier = Supplier.__new__(Supplier)
        supplier.name = "Bob Smith"
        supplier.company_name = "Bob's Plumbing"
        assert "Bob's Plumbing" in str(supplier)
        assert "Bob Smith" in str(supplier)

    def test_trade_choices_exist(self):
        from apps.maintenance.models import Supplier
        choices = [c[0] for c in Supplier.Trade.choices]
        assert "plumbing" in choices
        assert "electrical" in choices
        assert "general" in choices
        assert "other" in choices

    def test_display_name_property_prefers_company(self):
        from apps.maintenance.models import Supplier
        supplier = Supplier.__new__(Supplier)
        supplier.company_name = "Acme Corp"
        supplier.name = "John Doe"
        assert supplier.display_name == "Acme Corp"

    def test_display_name_property_falls_back_to_name(self):
        from apps.maintenance.models import Supplier
        supplier = Supplier.__new__(Supplier)
        supplier.company_name = ""
        supplier.name = "John Doe"
        assert supplier.display_name == "John Doe"


class TestJobDispatchStr:
    """JobDispatch.__str__ and status field."""

    def test_str_references_maintenance_request(self):
        from apps.maintenance.models import JobDispatch
        from django.db.models.base import ModelState
        dispatch = JobDispatch.__new__(JobDispatch)
        dispatch._state = ModelState()
        mr_mock = MagicMock()
        mr_mock.__str__ = lambda self: "Broken geyser — Unit 5"
        dispatch._state.fields_cache["maintenance_request"] = mr_mock
        result = str(dispatch)
        assert "Dispatch" in result

    def test_status_choices_exist(self):
        from apps.maintenance.models import JobDispatch
        choices = [c[0] for c in JobDispatch.Status.choices]
        assert "draft" in choices
        assert "sent" in choices
        assert "awarded" in choices
        assert "cancelled" in choices

    def test_default_status_is_draft(self):
        from apps.maintenance.models import JobDispatch
        assert JobDispatch.Status.DRAFT == "draft"


class TestJobQuoteStr:
    """JobQuote.__str__ and amount validation."""

    def test_str_includes_amount(self):
        from apps.maintenance.models import JobQuote
        from django.db.models.base import ModelState
        quote = JobQuote.__new__(JobQuote)
        quote._state = ModelState()
        quote.amount = Decimal("2500.00")
        supplier_mock = MagicMock()
        supplier_mock.__str__ = lambda self: "Plumber Joe"
        qr_mock = MagicMock()
        qr_mock.supplier = supplier_mock
        quote._state.fields_cache["quote_request"] = qr_mock
        result = str(quote)
        assert "2500" in result

    def test_amount_field_uses_decimal(self):
        from apps.maintenance.models import JobQuote
        # Check the field allows large values (max_digits=12, decimal_places=2)
        field = JobQuote._meta.get_field("amount")
        assert field.max_digits == 12
        assert field.decimal_places == 2

    def test_amount_is_not_nullable(self):
        from apps.maintenance.models import JobQuote
        field = JobQuote._meta.get_field("amount")
        assert not field.null
