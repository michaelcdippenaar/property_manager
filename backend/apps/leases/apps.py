from django.apps import AppConfig


class LeasesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.leases"

    def ready(self):
        # Register post_save broadcast signals
        from . import signals  # noqa: F401
