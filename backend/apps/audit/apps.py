from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Audit Log"

    def ready(self) -> None:
        # Register all signal handlers when Django starts.
        from . import signals  # noqa: F401
