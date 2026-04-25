"""
Django system checks for maintenance app URL settings.
"""
from django.conf import settings
from django.core.checks import Critical, register


@register()
def check_production_url_settings(app_configs, **kwargs):
    """
    In production (DEBUG=False) BASE_URL must be set.  An empty value would
    cause supplier SMS/WhatsApp job-notification links to contain localhost
    URLs, which are unreachable for suppliers.
    """
    if getattr(settings, "DEBUG", True):
        return []

    errors = []

    if not getattr(settings, "BASE_URL", ""):
        errors.append(
            Critical(
                "BASE_URL must be set in production. "
                "Supplier job-notification links in SMS/WhatsApp will contain "
                "broken localhost URLs without it.",
                id="maintenance.E001",
            )
        )

    return errors
