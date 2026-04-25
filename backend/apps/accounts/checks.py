"""
Django system checks for accounts app URL settings.

These fire during ``manage.py check`` (and at startup) to catch misconfigured
production deployments before they send customers localhost URLs.
"""
from django.conf import settings
from django.core.checks import Critical, register


@register()
def check_production_url_settings(app_configs, **kwargs):
    """
    In production (DEBUG=False) both SIGNING_PUBLIC_APP_BASE_URL and
    TENANT_APP_BASE_URL must be set.  An empty value would cause password-reset,
    invite, and 2FA-reset emails to contain localhost URLs, which look like
    phishing to customers and break the flow entirely.
    """
    if getattr(settings, "DEBUG", True):
        return []

    errors = []

    if not getattr(settings, "SIGNING_PUBLIC_APP_BASE_URL", ""):
        errors.append(
            Critical(
                "SIGNING_PUBLIC_APP_BASE_URL must be set in production. "
                "Password-reset, invite, and 2FA-reset emails will contain "
                "broken localhost URLs without it.",
                id="accounts.E001",
            )
        )

    if not getattr(settings, "TENANT_APP_BASE_URL", ""):
        errors.append(
            Critical(
                "TENANT_APP_BASE_URL must be set in production. "
                "Tenant invite emails will contain broken localhost URLs without it.",
                id="accounts.E002",
            )
        )

    return errors
