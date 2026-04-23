from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    verbose_name = "Notifications"

    def ready(self):
        # Registers push notification signals for key lifecycle events.
        import apps.notifications.push_signals  # noqa: F401
