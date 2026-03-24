from rest_framework import serializers
from .models import Property, PropertyGroup, Unit


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
