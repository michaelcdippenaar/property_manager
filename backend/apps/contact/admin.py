from django.contrib import admin
from django.utils import timezone

from .models import ContactEnquiry


@admin.action(description="Mark selected as responded")
def mark_responded(modeladmin, request, queryset):
    queryset.update(responded_at=timezone.now(), handled=True)


@admin.action(description="Anonymise PI (POPIA retention)")
def anonymise_pi(modeladmin, request, queryset):
    for obj in queryset:
        obj.anonymise()


@admin.register(ContactEnquiry)
class ContactEnquiryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "email", "role", "organisation", "handled", "email_sent")
    list_filter = ("handled", "role", "email_sent", "created_at")
    search_fields = ("name", "email", "organisation", "message")
    readonly_fields = (
        "created_at", "name", "email", "organisation", "role",
        "message", "consent_at", "ip_address", "user_agent", "email_sent",
    )
    fields = (
        "created_at",
        ("name", "email"),
        ("organisation", "role"),
        "message",
        "consent_at",
        ("ip_address", "user_agent"),
        "email_sent",
        ("handled", "responded_at"),
        "notes",
    )
    actions = [mark_responded, anonymise_pi]
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
