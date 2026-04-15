from django.apps import AppConfig


class TheVoltConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.the_volt"
    verbose_name = "The Volt"

    def ready(self):
        import apps.the_volt.documents.signals  # noqa: F401
