"""
apps/audit/serializers.py

Read-only DRF serializers for the AuditEvent model.
"""

from rest_framework import serializers

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    content_type_label = serializers.SerializerMethodField()
    actor_display = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "actor",
            "actor_email",
            "actor_display",
            "action",
            "content_type",
            "content_type_label",
            "object_id",
            "target_repr",
            "before_snapshot",
            "after_snapshot",
            "ip_address",
            "user_agent",
            "timestamp",
            "prev_hash",
            "self_hash",
            "retention_years",
        ]
        read_only_fields = fields

    def get_content_type_label(self, obj: AuditEvent) -> str | None:
        if obj.content_type:
            return f"{obj.content_type.app_label}.{obj.content_type.model}"
        return None

    def get_actor_display(self, obj: AuditEvent) -> str:
        if obj.actor:
            return obj.actor.email
        if obj.actor_email:
            return obj.actor_email
        return "system"
