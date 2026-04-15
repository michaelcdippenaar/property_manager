from rest_framework import serializers

from .models import DataSubscriber, DataRequest, DataCheckout, DataRequestApprovalLink, RequestStatus


class DataSubscriberSerializer(serializers.ModelSerializer):
    """Returned when a subscriber is created. api_key_raw is in context on create only."""
    api_key_raw = serializers.SerializerMethodField()

    class Meta:
        model = DataSubscriber
        fields = [
            "id",
            "org_name",
            "org_contact_email",
            "api_key_prefix",
            "is_active",
            "created_at",
            "api_key_raw",
        ]
        read_only_fields = ["id", "api_key_prefix", "is_active", "created_at"]

    def get_api_key_raw(self, obj):
        # Only return on create (context["api_key_raw"] set by view)
        return self.context.get("api_key_raw")


class DataRequestSerializer(serializers.ModelSerializer):
    subscriber_name = serializers.CharField(source="subscriber.org_name", read_only=True)
    vault_user_email = serializers.CharField(source="vault.user.email", read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = DataRequest
        fields = [
            "id",
            "access_token",
            "subscriber_name",
            "vault_user_email",
            "status",
            "requested_entity_types",
            "requested_fields",
            "requested_document_types",
            "purpose",
            "expires_at",
            "approved_by_id",
            "approved_at",
            "created_at",
            "is_expired",
        ]
        read_only_fields = [
            "id", "access_token", "status", "expires_at",
            "approved_by_id", "approved_at", "created_at", "is_expired",
        ]


class DataCheckoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataCheckout
        fields = [
            "id",
            "checkout_token",
            "entities_shared",
            "documents_shared",
            "data_hash",
            "package_signature",
            "delivery_method",
            "authorisation_method",
            "ip_address",
            "checked_out_at",
        ]
        read_only_fields = fields


class ApprovalInfoSerializer(serializers.ModelSerializer):
    """Public view of a DataRequest for the owner approval page (no OTP required to view)."""
    subscriber_name = serializers.CharField(source="subscriber.org_name", read_only=True)
    subscriber_email = serializers.CharField(source="subscriber.org_contact_email", read_only=True)

    class Meta:
        model = DataRequest
        fields = [
            "access_token",
            "status",
            "subscriber_name",
            "subscriber_email",
            "requested_entity_types",
            "requested_document_types",
            "purpose",
            "expires_at",
            "created_at",
        ]
