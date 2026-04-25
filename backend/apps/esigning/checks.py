"""
Django system checks for esigning app URL settings.
"""
from django.conf import settings
from django.core.checks import Critical, register


@register()
def check_production_url_settings(app_configs, **kwargs):
    """
    In production (DEBUG=False) SITE_URL must be set.  An empty value would
    cause signed-PDF download URLs built from relative paths to become
    localhost URLs in e-signing completion emails.
    """
    if getattr(settings, "DEBUG", True):
        return []

    errors = []

    if not getattr(settings, "SITE_URL", ""):
        errors.append(
            Critical(
                "SITE_URL must be set in production. "
                "Signed-PDF download links in e-signing completion emails will "
                "contain broken localhost URLs without it.",
                id="esigning.E001",
            )
        )

    return errors
