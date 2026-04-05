"""Unit tests for properties serializers — validate field configuration."""
import pytest

pytestmark = pytest.mark.unit


class TestUnitSerializer:

    @pytest.mark.green
    def test_serializer_uses_all_fields(self):
        """UnitSerializer uses fields='__all__' — all model fields are included."""
        from apps.properties.serializers import UnitSerializer
        # __all__ means Meta.fields == '__all__'
        assert UnitSerializer.Meta.fields == "__all__"

    @pytest.mark.green
    def test_unit_serializer_model_is_unit(self):
        from apps.properties.serializers import UnitSerializer
        from apps.properties.models import Unit
        assert UnitSerializer.Meta.model is Unit

    @pytest.mark.green
    def test_rent_amount_has_no_min_value_validator(self):
        """
        Documents vuln #21: no positive rent validation in serializer.
        Marked red — verify the serializer does NOT declare a custom rent validator.
        Flip the assertion when a min_value=0 validator is added.
        """
        from apps.properties.serializers import UnitSerializer
        # If no custom rent_amount field override exists, no validation is present
        declared_fields = UnitSerializer._declared_fields
        assert "rent_amount" not in declared_fields  # no override means no validator


class TestPropertySerializer:

    @pytest.mark.green
    def test_serializer_model_is_property(self):
        from apps.properties.serializers import PropertySerializer
        from apps.properties.models import Property
        assert PropertySerializer.Meta.model is Property

    @pytest.mark.green
    def test_units_field_is_read_only(self):
        """Nested units are read-only (populated by reverse FK)."""
        from apps.properties.serializers import PropertySerializer
        field = PropertySerializer().fields["units"]
        assert field.read_only is True

    @pytest.mark.green
    def test_unit_count_field_is_read_only(self):
        from apps.properties.serializers import PropertySerializer
        field = PropertySerializer().fields["unit_count"]
        assert field.read_only is True

    @pytest.mark.green
    def test_fields_include_all_model_fields(self):
        """PropertySerializer uses __all__, so all model fields are included."""
        from apps.properties.serializers import PropertySerializer
        assert PropertySerializer.Meta.fields == "__all__"


class TestPropertyGroupSerializer:

    @pytest.mark.green
    def test_property_count_is_read_only(self):
        from apps.properties.serializers import PropertyGroupSerializer
        field = PropertyGroupSerializer().fields["property_count"]
        assert field.read_only is True

    @pytest.mark.green
    def test_property_ids_source_is_properties(self):
        """property_ids maps to the 'properties' M2M field."""
        from apps.properties.serializers import PropertyGroupSerializer
        field = PropertyGroupSerializer().fields["property_ids"]
        assert field.source == "properties"

    @pytest.mark.green
    def test_created_at_is_read_only(self):
        from apps.properties.serializers import PropertyGroupSerializer
        assert "created_at" in PropertyGroupSerializer.Meta.read_only_fields


class TestUnitInfoSerializer:

    @pytest.mark.green
    def test_id_is_read_only(self):
        from apps.properties.serializers import UnitInfoSerializer
        assert "id" in UnitInfoSerializer.Meta.read_only_fields

    @pytest.mark.green
    def test_unit_number_is_read_only_derived(self):
        from apps.properties.serializers import UnitInfoSerializer
        field = UnitInfoSerializer().fields["unit_number"]
        assert field.read_only is True

    @pytest.mark.green
    def test_property_name_is_read_only(self):
        from apps.properties.serializers import UnitInfoSerializer
        field = UnitInfoSerializer().fields["property_name"]
        assert field.read_only is True


class TestPropertyAgentConfigSerializer:

    @pytest.mark.green
    def test_property_name_is_read_only(self):
        from apps.properties.serializers import PropertyAgentConfigSerializer
        field = PropertyAgentConfigSerializer().fields["property_name"]
        assert field.read_only is True

    @pytest.mark.green
    def test_id_is_read_only(self):
        from apps.properties.serializers import PropertyAgentConfigSerializer
        assert "id" in PropertyAgentConfigSerializer.Meta.read_only_fields
