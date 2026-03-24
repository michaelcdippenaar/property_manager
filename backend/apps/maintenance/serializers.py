from rest_framework import serializers
from .models import MaintenanceRequest


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRequest
        fields = "__all__"
        read_only_fields = ["tenant", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["tenant"] = self.context["request"].user
        return super().create(validated_data)
