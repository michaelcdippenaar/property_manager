"""
Unit tests for maintenance serializers.

These tests exercise field-level validation without full DB integration.
"""
import pytest

pytestmark = pytest.mark.unit


class TestMaintenanceRequestSerializerFields:
    """MaintenanceRequestSerializer required fields and validation."""

    def test_required_fields_in_serializer(self):
        from apps.maintenance.serializers import MaintenanceRequestSerializer
        serializer = MaintenanceRequestSerializer()
        fields = serializer.fields
        assert "title" in fields
        assert "description" in fields
        assert "priority" in fields

    def test_title_is_required(self):
        from apps.maintenance.serializers import MaintenanceRequestSerializer
        # Missing title — should be invalid
        data = {
            "description": "Something is broken",
            "priority": "medium",
        }
        serializer = MaintenanceRequestSerializer(data=data)
        assert not serializer.is_valid()
        assert "title" in serializer.errors

    def test_description_is_required(self):
        from apps.maintenance.serializers import MaintenanceRequestSerializer
        data = {
            "title": "Broken tap",
            "priority": "medium",
        }
        serializer = MaintenanceRequestSerializer(data=data)
        assert not serializer.is_valid()
        assert "description" in serializer.errors

    def test_invalid_priority_rejected(self):
        from apps.maintenance.serializers import MaintenanceRequestSerializer
        data = {
            "title": "Broken tap",
            "description": "Tap is dripping",
            "priority": "catastrophic",  # not a valid choice
        }
        serializer = MaintenanceRequestSerializer(data=data)
        assert not serializer.is_valid()
        assert "priority" in serializer.errors


class TestSupplierSerializerFields:
    """SupplierSerializer required fields."""

    def test_name_is_required(self):
        from apps.maintenance.serializers import SupplierSerializer
        data = {"phone": "0820001111"}
        serializer = SupplierSerializer(data=data)
        assert not serializer.is_valid()
        assert "name" in serializer.errors

    def test_phone_is_required(self):
        from apps.maintenance.serializers import SupplierSerializer
        data = {"name": "Plumber Joe"}
        serializer = SupplierSerializer(data=data)
        assert not serializer.is_valid()
        assert "phone" in serializer.errors

    def test_valid_minimal_data(self):
        from apps.maintenance.serializers import SupplierSerializer
        data = {"name": "Sparky", "phone": "0821112222"}
        serializer = SupplierSerializer(data=data)
        # Should be valid with just name + phone
        assert serializer.is_valid(), serializer.errors

    def test_trades_field_is_read_only(self):
        from apps.maintenance.serializers import SupplierSerializer
        serializer = SupplierSerializer()
        trades_field = serializer.fields["trades"]
        assert trades_field.read_only
