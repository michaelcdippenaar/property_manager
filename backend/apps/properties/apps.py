from django.apps import AppConfig


class PropertiesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.properties"

    def ready(self):
        from . import signals  # noqa: F401
        from .dashboard_signals import register as register_dashboard_signals
        register_dashboard_signals()
