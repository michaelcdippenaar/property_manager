from rest_framework import serializers
from .models import LegalDocument, UserConsent


class LegalDocumentSerializer(serializers.ModelSerializer):
    doc_type_display = serializers.CharField(source="get_doc_type_display", read_only=True)

    class Meta:
        model = LegalDocument
        fields = [
            "id",
            "doc_type",
            "doc_type_display",
            "version",
            "effective_date",
            "summary_of_changes",
            "url",
            "is_current",
            "requires_re_ack",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class UserConsentSerializer(serializers.ModelSerializer):
    document_version = serializers.CharField(source="document.version", read_only=True)
    document_type = serializers.CharField(source="document.doc_type", read_only=True)

    class Meta:
        model = UserConsent
        fields = [
            "id",
            "document",
            "document_version",
            "document_type",
            "accepted_at",
        ]
        read_only_fields = ["id", "accepted_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user

        document = validated_data["document"]

        # Idempotent: if consent already recorded, return existing row
        consent, _ = UserConsent.objects.get_or_create(
            user=user,
            document=document,
            defaults={
                "ip_address": self._get_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
            },
        )
        return consent

    @staticmethod
    def _get_ip(request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR") or None


class PendingConsentSerializer(serializers.ModelSerializer):
    """Minimal payload returned when a user needs to re-accept a document."""
    doc_type_display = serializers.CharField(source="get_doc_type_display", read_only=True)

    class Meta:
        model = LegalDocument
        fields = ["id", "doc_type", "doc_type_display", "version", "effective_date", "summary_of_changes", "url"]
