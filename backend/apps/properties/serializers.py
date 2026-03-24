from rest_framework import serializers
from .models import Property, Unit


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
