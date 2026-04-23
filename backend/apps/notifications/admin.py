from django.contrib import admin

from .models import NotificationLog, PushPreference


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "channel",
        "to_address",
        "status",
        "subject",
        "provider_message_id",
    )
    list_filter = ("channel", "status")
    search_fields = ("to_address", "subject", "body", "provider_message_id")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(PushPreference)
class PushPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "enabled", "updated_at")
    list_filter = ("category", "enabled")
    search_fields = ("user__email",)
    readonly_fields = ("updated_at",)
