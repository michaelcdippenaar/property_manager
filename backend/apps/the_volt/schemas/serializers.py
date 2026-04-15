from rest_framework import serializers

from .models import EntitySchema


class EntitySchemaSerializer(serializers.ModelSerializer):
    entity_type_display = serializers.CharField(source="get_entity_type_display", read_only=True)

    class Meta:
        model = EntitySchema
        fields = [
            "id",
            "entity_type",
            "entity_type_display",
            "country_code",
            "version",
            "label",
            "description",
            "fields",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_fields(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("fields must be a list of field definition objects.")
        required_keys = {"key", "label", "type"}
        for i, field in enumerate(value):
            if not isinstance(field, dict):
                raise serializers.ValidationError(f"Field at index {i} must be an object.")
            missing = required_keys - field.keys()
            if missing:
                raise serializers.ValidationError(
                    f"Field at index {i} is missing required keys: {missing}"
                )
        return value
