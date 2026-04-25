from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        # Register system checks for production URL settings.
        import apps.accounts.checks  # noqa: F401

        # Sync tiers from pricing.yaml into DB on every startup.
        # Wrapped in a try/except so test runners without a full DB still work.
        try:
            from apps.accounts.tier_service import sync_tiers
            sync_tiers()
        except Exception:
            pass  # graceful degradation during initial migrate / test setup
