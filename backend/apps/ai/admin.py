import json

from django.contrib import admin

from .models import TenantChatSession, TenantIntelligence


@admin.register(TenantChatSession)
class TenantChatSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "user",
        "maintenance_request",
        "agent_question",
        "maintenance_report_suggested",
        "updated_at",
    )
    list_filter = ("maintenance_report_suggested", "updated_at")
    search_fields = ("title", "user__email")
    readonly_fields = ("created_at", "updated_at", "messages_preview")
    raw_id_fields = ("user", "maintenance_request", "agent_question")

    fieldsets = (
        (None, {"fields": ("user", "title", "maintenance_report_suggested")}),
        ("Links", {"fields": ("maintenance_request", "agent_question")}),
        ("Messages (JSON)", {"fields": ("messages",)}),
        ("Preview", {"fields": ("messages_preview",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Messages preview")
    def messages_preview(self, obj: TenantChatSession) -> str:
        try:
            return json.dumps(obj.messages, indent=2, ensure_ascii=False)[:8000]
        except Exception:
            return str(obj.messages)[:2000]


@admin.register(TenantIntelligence)
class TenantIntelligenceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "property_ref",
        "unit_ref",
        "total_chats",
        "total_messages",
        "complaint_score",
        "last_chat_at",
    )
    list_filter = ("property_ref", "last_chat_at")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    readonly_fields = ("created_at", "updated_at", "facts_preview", "categories_preview")
    raw_id_fields = ("user", "property_ref", "unit_ref")

    fieldsets = (
        (None, {"fields": ("user", "property_ref", "unit_ref")}),
        ("Stats", {"fields": ("total_chats", "total_messages", "complaint_score", "last_chat_at")}),
        ("Data", {"fields": ("facts", "question_categories")}),
        ("Previews", {"fields": ("facts_preview", "categories_preview")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Facts preview")
    def facts_preview(self, obj: TenantIntelligence) -> str:
        try:
            return json.dumps(obj.facts, indent=2, ensure_ascii=False)[:4000]
        except Exception:
            return str(obj.facts)[:2000]

    @admin.display(description="Question categories")
    def categories_preview(self, obj: TenantIntelligence) -> str:
        try:
            return json.dumps(obj.question_categories, indent=2, ensure_ascii=False)[:2000]
        except Exception:
            return str(obj.question_categories)[:1000]
