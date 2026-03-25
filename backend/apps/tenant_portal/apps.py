from django.apps import AppConfig


class TenantPortalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenant_portal"
    verbose_name = "Tenant portal"
