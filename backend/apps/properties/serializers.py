from rest_framework import serializers
from .models import Property, PropertyAgentConfig, PropertyGroup, Unit, UnitInfo


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = "__all__"


class PropertySerializer(serializers.ModelSerializer):
    units = UnitSerializer(many=True, read_only=True)
    unit_count = serializers.IntegerField(source="units.count", read_only=True)

    class Meta:
        model = Property
        fields = "__all__"
        read_only_fields = ["agent"]

    def create(self, validated_data):
        validated_data["agent"] = self.context["request"].user
        return super().create(validated_data)


class UnitInfoSerializer(serializers.ModelSerializer):
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True, default=None)
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = UnitInfo
        fields = ["id", "property", "property_name", "unit", "unit_number", "icon_type", "label", "value", "sort_order", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PropertyAgentConfigSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = PropertyAgentConfig
        fields = ["id", "property", "property_name", "maintenance_playbook", "ai_notes", "is_active", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class PropertyGroupSerializer(serializers.ModelSerializer):
    property_count = serializers.IntegerField(source="properties.count", read_only=True)
    property_ids = serializers.PrimaryKeyRelatedField(
        source="properties", queryset=Property.objects.all(),
        many=True, required=False,
    )

    class Meta:
        model = PropertyGroup
        fields = ["id", "name", "description", "property_ids", "property_count", "created_at"]
        read_only_fields = ["created_at"]

    def create(self, validated_data):
        props = validated_data.pop("properties", [])
        group = PropertyGroup.objects.create(**validated_data)
        if props:
            group.properties.set(props)
        return group

    def update(self, instance, validated_data):
        props = validated_data.pop("properties", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if props is not None:
            instance.properties.set(props)
        return instance
