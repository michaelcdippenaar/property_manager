"""
apps/popia/admin.py

Django admin for POPIA DSAR models.
Operators can review, approve, and deny requests here as well as via the API.
"""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import DSARRequest, ExportJob


class ExportJobInline(admin.StackedInline):
    model = ExportJob
    extra = 0
    readonly_fields = [
        "status", "archive_path", "download_token", "expires_at",
        "error_detail", "is_downloadable", "is_expired", "created_at", "updated_at",
    ]
    fields = [
        "status", "archive_path", "expires_at",
        "error_detail", "created_at", "updated_at",
    ]
    can_delete = False

    def is_downloadable(self, obj):
        return obj.is_downloadable
    is_downloadable.boolean = True

    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True


@admin.register(DSARRequest)
class DSARRequestAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "requester_email",
        "request_type",
        "status",
        "days_remaining_display",
        "is_overdue_display",
        "created_at",
        "sla_deadline",
    ]
    list_filter = ["request_type", "status"]
    search_fields = ["requester_email", "requester__email", "requester__first_name"]
    readonly_fields = [
        "requester", "requester_email", "request_type", "reason",
        "reviewed_by", "reviewed_at", "sla_deadline",
        "days_remaining", "is_overdue",
        "created_at", "updated_at", "completed_at",
    ]
    fieldsets = [
        ("Request", {
            "fields": [
                "requester", "requester_email", "request_type", "reason",
                "status", "sla_deadline", "created_at",
            ],
        }),
        ("Review", {
            "fields": [
                "reviewed_by", "reviewed_at", "operator_notes",
                "denial_reason", "completed_at",
            ],
        }),
    ]
    inlines = [ExportJobInline]
    ordering = ["sla_deadline"]

    def days_remaining_display(self, obj):
        days = obj.days_remaining
        if days < 0:
            return format_html('<span style="color:red">OVERDUE ({} days)</span>', abs(days))
        if days <= 5:
            return format_html('<span style="color:orange">{} days</span>', days)
        return f"{days} days"
    days_remaining_display.short_description = "Days remaining"

    def is_overdue_display(self, obj):
        return obj.is_overdue
    is_overdue_display.boolean = True
    is_overdue_display.short_description = "Overdue?"

    def save_model(self, request, obj, form, change):
        """Auto-execute erasure when an operator approves an RTBF via admin."""
        if change:
            old_obj = DSARRequest.objects.get(pk=obj.pk)
            if (
                old_obj.status != DSARRequest.Status.APPROVED
                and obj.status == DSARRequest.Status.APPROVED
                and obj.request_type == DSARRequest.RequestType.RTBF
            ):
                obj.reviewed_by = request.user
                obj.reviewed_at = timezone.now()
                super().save_model(request, obj, form, change)
                from .services.deletion_service import execute_erasure
                execute_erasure(obj, reviewer=request.user)
                return
        super().save_model(request, obj, form, change)


@admin.register(ExportJob)
class ExportJobAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "dsar_request",
        "status",
        "is_downloadable_display",
        "expires_at",
        "created_at",
    ]
    list_filter = ["status"]
    readonly_fields = [
        "dsar_request", "status", "archive_path", "download_token",
        "expires_at", "error_detail", "created_at", "updated_at",
    ]
    ordering = ["-created_at"]

    def is_downloadable_display(self, obj):
        return obj.is_downloadable
    is_downloadable_display.boolean = True
    is_downloadable_display.short_description = "Downloadable?"
