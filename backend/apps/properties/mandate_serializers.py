from rest_framework import serializers
from .models import RentalMandate


class RentalMandateSerializer(serializers.ModelSerializer):
    property_name  = serializers.CharField(source="property.name", read_only=True)
    landlord_name  = serializers.CharField(source="landlord.name", read_only=True)
    submission_id  = serializers.SerializerMethodField()
    signing_status = serializers.SerializerMethodField()
    signing_progress = serializers.SerializerMethodField()
    owner_email    = serializers.SerializerMethodField()
    owner_name     = serializers.SerializerMethodField()

    class Meta:
        model = RentalMandate
        fields = [
            "id",
            "property", "property_name",
            "landlord", "landlord_name",
            "mandate_type", "exclusivity",
            "commission_rate", "commission_period",
            "start_date", "end_date",
            "notice_period_days", "maintenance_threshold",
            "status",
            "notes",
            "submission_id",
            "signing_status",
            "signing_progress",
            "owner_email",
            "owner_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["status", "created_at", "updated_at"]

    def get_submission_id(self, obj):
        sub = getattr(obj, "esigning_submission", None)
        return sub.pk if sub else None

    def get_signing_status(self, obj):
        sub = getattr(obj, "esigning_submission", None)
        return sub.status if sub else None

    def get_signing_progress(self, obj):
        sub = getattr(obj, "esigning_submission", None)
        if not sub:
            return None
        signers = sub.signers or []
        total = len(signers)
        completed = sum(
            1 for s in signers
            if (s.get("status") or "").lower() in ("completed", "signed")
        )
        return {"total": total, "completed": completed}

    def get_owner_email(self, obj):
        ll = obj.landlord
        if ll:
            return ll.representative_email or ll.email or ""
        ownership = obj.property.ownerships.filter(is_current=True).first()
        if ownership:
            return ownership.representative_email or ownership.owner_email or ""
        return ""

    def get_owner_name(self, obj):
        ll = obj.landlord
        if ll:
            return ll.representative_name or ll.name or ""
        ownership = obj.property.ownerships.filter(is_current=True).first()
        if ownership:
            return ownership.representative_name or ownership.owner_name or ""
        return ""
