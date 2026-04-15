from rest_framework import serializers

from .models import VaultOwner


class VaultOwnerSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_full_name = serializers.SerializerMethodField()

    class Meta:
        model = VaultOwner
        fields = ["id", "user_id", "user_email", "user_full_name", "created_at", "updated_at"]
        read_only_fields = ["id", "user_id", "created_at", "updated_at"]

    def get_user_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()
