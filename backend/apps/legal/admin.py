from django.contrib import admin
from .models import LegalDocument, UserConsent


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ["doc_type", "version", "effective_date", "is_current", "requires_re_ack", "created_at"]
    list_filter = ["doc_type", "is_current", "requires_re_ack"]
    ordering = ["-effective_date"]
    readonly_fields = ["created_at"]
    fieldsets = [
        (None, {
            "fields": ["doc_type", "version", "effective_date", "url"],
        }),
        ("Change management", {
            "fields": ["is_current", "requires_re_ack", "summary_of_changes"],
        }),
        ("Metadata", {
            "fields": ["created_at"],
        }),
    ]


@admin.register(UserConsent)
class UserConsentAdmin(admin.ModelAdmin):
    list_display = ["user", "document", "accepted_at", "ip_address"]
    list_filter = ["document__doc_type"]
    search_fields = ["user__email"]
    readonly_fields = ["user", "document", "accepted_at", "ip_address", "user_agent"]
    ordering = ["-accepted_at"]
