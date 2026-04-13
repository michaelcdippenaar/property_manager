from django.apps import AppConfig


class TenantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenant"
    verbose_name = "Tenants"

    def ready(self):
        import apps.tenant.signals  # noqa: F401
