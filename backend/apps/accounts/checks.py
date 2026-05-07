"""
Django system checks for accounts app URL settings.

These fire during ``manage.py check`` (and at startup) to catch misconfigured
production deployments before they send customers localhost URLs.
"""
from django.conf import settings
from django.core.checks import Critical, Warning as CheckWarning, register


@register()
def check_no_orphan_users(app_configs, **kwargs):
    """
    Phase 3.1 — every authenticated staff/owner user MUST have an agency_id.

    TENANT and SUPPLIER users are legitimately agency-less (they belong to
    a property/lease, not a managing agency). Any other role without an
    ``agency_id`` is an orphan caused by a buggy signup/invite path; the
    Phase 4 cutover will repair existing rows.

    Returns Critical errors so ``manage.py check --deploy`` fails until
    orphans are repaired.
    """
    # Lazy-import — apps may not be ready at import time.
    try:
        from django.apps import apps as django_apps
        User = django_apps.get_model("accounts", "User")
    except Exception:
        return []

    # The DB connection may not be set up during initial check phases
    # (e.g. fresh migrate) — be defensive.
    try:
        agencyless_roles = ["tenant", "supplier"]
        orphans = (
            User.objects
            .filter(agency__isnull=True, is_active=True)
            .exclude(role__in=agencyless_roles)
        )
        count = orphans.count()
    except Exception:
        return []

    if count == 0:
        return []

    sample = list(orphans.values_list("email", flat=True)[:5])
    return [
        Critical(
            f"{count} active user(s) have no agency_id but require one "
            f"(role not in tenant/supplier). Sample: {sample}. "
            "Run the Phase 4 backfill to repair, or assign each user an "
            "agency manually.",
            id="accounts.E003",
            hint="Phase 3.1 prevents new orphans. Phase 4 backfills existing ones.",
        )
    ]


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
