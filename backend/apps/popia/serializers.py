"""
apps/popia/serializers.py
"""
from rest_framework import serializers

from .models import DSARRequest, ExportJob


class DSARRequestSerializer(serializers.ModelSerializer):
    days_remaining = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    requester_email = serializers.EmailField(read_only=True)

    class Meta:
        model = DSARRequest
        fields = [
            "id",
            "requester",
            "requester_email",
            "request_type",
            "reason",
            "status",
            "operator_notes",
            "denial_reason",
            "reviewed_by",
            "reviewed_at",
            "sla_deadline",
            "days_remaining",
            "is_overdue",
            "created_at",
            "updated_at",
            "completed_at",
        ]
        read_only_fields = [
            "id", "requester", "requester_email", "status",
            "reviewed_by", "reviewed_at", "sla_deadline",
            "days_remaining", "is_overdue",
            "created_at", "updated_at", "completed_at",
        ]


class DSARRequestCreateSerializer(serializers.Serializer):
    """
    Minimal input for creating a SAR or RTBF request.
    `reason` is optional — the data subject may provide context.
    """
    request_type = serializers.ChoiceField(choices=DSARRequest.RequestType.choices)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class OperatorReviewSerializer(serializers.Serializer):
    """
    Input for an operator approving or denying a DSAR request.
    """
    action = serializers.ChoiceField(choices=["approve", "deny"])
    operator_notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    denial_reason = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate(self, data):
        if data["action"] == "deny" and not data.get("denial_reason"):
            raise serializers.ValidationError(
                {"denial_reason": "A denial reason is required when denying a DSAR request."}
            )
        return data


class ExportJobSerializer(serializers.ModelSerializer):
    is_downloadable = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = ExportJob
        fields = [
            "id",
            "status",
            "expires_at",
            "is_downloadable",
            "is_expired",
            "created_at",
        ]
        read_only_fields = fields
