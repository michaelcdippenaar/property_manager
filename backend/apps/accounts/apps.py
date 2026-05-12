from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        # Register system checks for production URL settings.
        import apps.accounts.checks  # noqa: F401

        # Defence-in-depth: backfill agency_id from a model's declared parent
        # FK when a child row is saved without one. Opt-in per model via the
        # AGENCY_PARENT_FIELD class attribute. See apps/accounts/tenancy.py.
        from apps.accounts.tenancy import connect_agency_backfill_signal
        connect_agency_backfill_signal()

        # Sync tiers from pricing.yaml into DB on every startup.
        # Wrapped in a try/except so test runners without a full DB still work.
        try:
            from apps.accounts.tier_service import sync_tiers
            sync_tiers()
        except Exception:
            pass  # graceful degradation during initial migrate / test setup
