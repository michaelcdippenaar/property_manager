from django.contrib import admin

from .models import TenantAiConversation, TenantAiMessage


class TenantAiMessageInline(admin.TabularInline):
    model = TenantAiMessage
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(TenantAiConversation)
class TenantAiConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "updated_at")
    list_filter = ("updated_at",)
    search_fields = ("title", "user__email")
    inlines = [TenantAiMessageInline]
