from rest_framework import serializers
from .models import RentalMandate


class MandateRenewSerializer(serializers.Serializer):
    """Validates the optional override fields accepted by the `renew` action.

    All fields are optional — omitted fields inherit values from the source
    mandate.  This serializer exists solely to reject malformed input before
    anything reaches the ORM.
    """

    commission_rate = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False
    )
    commission_period = serializers.ChoiceField(
        choices=RentalMandate.CommissionPeriod.choices, required=False
    )
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False, allow_null=True)
    notice_period_days = serializers.IntegerField(min_value=0, required=False)
    maintenance_threshold = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)


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
            "terminated_at", "terminated_reason",
            "previous_mandate",
            "submission_id",
            "signing_status",
            "signing_progress",
            "owner_email",
            "owner_name",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "status", "terminated_at", "terminated_reason",
            "previous_mandate", "created_at", "updated_at",
        ]

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
