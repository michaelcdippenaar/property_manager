"""
Pricing-tier service for Klikk.

Responsibilities:
  1. Load tier definitions from content/product/pricing.yaml at startup (once).
  2. Seed/sync SubscriptionTier rows so the DB always matches pricing.yaml.
  3. Provide has_feature() and quota_status() helpers for Agency instances.

Feature flags map pricing.yaml limits to named capability slugs:
  ai_lease_generation   - AI conversational lease builder
  ai_chat               - Tenant AI chat (RAG)
  e_signing             - Native e-signing
  api_access            - REST API access
  mcp_access            - MCP server access
  owner_portal          - Owner portal
  tenant_portal         - Tenant portal
  supplier_portal       - Supplier portal
  multiple_users        - More than 1 user on the account
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from django.db import models
from django.utils import timezone

# ---------------------------------------------------------------------------
# Path to pricing.yaml (relative to project root — not inside backend/).
# ---------------------------------------------------------------------------
_PRICING_YAML_PATH = Path(__file__).resolve().parents[3] / "content" / "product" / "pricing.yaml"


@lru_cache(maxsize=1)
def load_pricing_config() -> dict:
    """Load and cache pricing.yaml. Callable safely at module import time."""
    if not _PRICING_YAML_PATH.exists():
        return {}
    with open(_PRICING_YAML_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


# ---------------------------------------------------------------------------
# Derive boolean feature flags from pricing.yaml tier limits.
# ---------------------------------------------------------------------------

def _tier_features(limits: dict, tier_key: str) -> dict:
    """Convert raw tier limits to a normalised feature-flag dict."""
    return {
        "ai_lease_generation": limits.get("ai_contracts_yearly") != 0,  # None = unlimited; 0 = blocked
        "ai_chat": limits.get("maintenance") in ("full", "ai_reporting"),
        "e_signing": tier_key != "free",
        "api_access": bool(limits.get("api")),
        "mcp_access": bool(limits.get("mcp")),
        "owner_portal": True,   # always available
        "tenant_portal": tier_key != "free",
        "supplier_portal": tier_key not in ("free",),
        "multiple_users": tier_key != "free",
    }


def _tier_quota_from_pricing(limits: dict) -> dict:
    """Extract hard quota values from pricing.yaml limits section."""
    return {
        "max_properties": limits.get("max_properties"),   # None = unlimited
        "max_units": limits.get("max_units"),
        "max_users": limits.get("max_users"),
        "max_ai_contracts_yearly": limits.get("ai_contracts_yearly"),  # None = unlimited
    }


# ---------------------------------------------------------------------------
# DB-backed SubscriptionTier model (populated by sync_tiers).
# ---------------------------------------------------------------------------

class SubscriptionTier(models.Model):
    """
    One row per pricing tier (free / pro / enterprise / custom).
    Seeded/updated by sync_tiers() via an AppConfig.ready() signal.
    """
    slug = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=60)
    price_monthly = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Monthly price in ZAR excl VAT. Null = quoted (enterprise/custom).",
    )
    features = models.JSONField(default=dict, help_text="Boolean feature flag dict.")
    quotas = models.JSONField(default=dict, help_text="Numeric quota dict (None = unlimited).")
    display_order = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounts"
        ordering = ["display_order"]

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def has_feature(self, slug: str) -> bool:
        """Return True if this tier includes the named feature."""
        return bool(self.features.get(slug, False))

    @classmethod
    def get_default(cls) -> "SubscriptionTier | None":
        """Return the 'pro' tier (fallback default for existing agencies)."""
        return cls.objects.filter(slug="pro").first()


def sync_tiers() -> None:
    """
    Idempotent upsert of all tiers from pricing.yaml into SubscriptionTier.
    Called from AccountsConfig.ready() so it runs at every Django startup.
    Skips gracefully if the DB table doesn't exist yet (pre-migration).
    """
    from django.db import connection

    # Guard: table may not exist during first migrate
    if "accounts_subscriptiontier" not in connection.introspection.table_names():
        return

    config = load_pricing_config()
    tiers_raw = config.get("tiers", {})
    if not tiers_raw:
        return

    order_map = {"free": 0, "pro": 1, "enterprise": 2, "custom": 3}
    for slug, tier_data in tiers_raw.items():
        limits = tier_data.get("limits", {})
        defaults = {
            "name": tier_data.get("name", slug.title()),
            "price_monthly": tier_data.get("price_monthly"),
            "features": _tier_features(limits, slug),
            "quotas": _tier_quota_from_pricing(limits),
            "display_order": order_map.get(slug, 99),
        }
        SubscriptionTier.objects.update_or_create(slug=slug, defaults=defaults)


# ---------------------------------------------------------------------------
# Usage / quota helpers.
# ---------------------------------------------------------------------------

class QuotaStatus:
    """Snapshot of one quota dimension for an agency."""

    def __init__(self, key: str, used: int, limit: int | None):
        self.key = key
        self.used = used
        self.limit = limit  # None = unlimited

    @property
    def is_unlimited(self) -> bool:
        return self.limit is None

    @property
    def fraction(self) -> float | None:
        """0.0..1.0 or None if unlimited."""
        if self.limit is None:
            return None
        return self.used / self.limit if self.limit > 0 else 1.0

    @property
    def warning(self) -> bool:
        """Soft warning at >= 80%."""
        f = self.fraction
        return f is not None and f >= 0.80 and f < 1.0

    @property
    def blocked(self) -> bool:
        """Hard block at >= 100%."""
        f = self.fraction
        return f is not None and f >= 1.0

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "used": self.used,
            "limit": self.limit,
            "fraction": round(self.fraction, 4) if self.fraction is not None else None,
            "warning": self.warning,
            "blocked": self.blocked,
            "unlimited": self.is_unlimited,
        }


class TierService:
    """
    Stateless service: agency-aware feature + quota checks.

    Usage::

        svc = TierService(agency)
        if not svc.has_feature("ai_lease_generation"):
            return tier_upgrade_response(request)

        for qs in svc.quota_statuses():
            if qs.blocked:
                ...
    """

    def __init__(self, agency):
        self._agency = agency

    # ------------------------------------------------------------------
    # Feature flags
    # ------------------------------------------------------------------

    @property
    def tier(self) -> SubscriptionTier | None:
        if self._agency is None:
            return None
        return getattr(self._agency, "subscription_tier", None)

    def has_feature(self, slug: str) -> bool:
        """
        Returns True when the agency's current tier includes `slug`.
        Falls back to True when no tier is set (backwards compat: existing
        agencies without a tier get all features rather than being hard-blocked
        on upgrade before any tier is assigned).
        """
        t = self.tier
        if t is None:
            return True
        return t.has_feature(slug)

    # ------------------------------------------------------------------
    # Quota status
    # ------------------------------------------------------------------

    def _property_count(self) -> int:
        from apps.properties.models import Property
        from apps.accounts.models import Agency
        agency = self._agency
        if agency is None:
            return 0
        # Properties managed by any agent in this agency
        agent_ids = agency.members.values_list("id", flat=True)
        return Property.objects.filter(agent_id__in=agent_ids).count()

    def _unit_count(self) -> int:
        from apps.properties.models import Unit, Property
        agency = self._agency
        if agency is None:
            return 0
        agent_ids = agency.members.values_list("id", flat=True)
        prop_ids = Property.objects.filter(agent_id__in=agent_ids).values_list("id", flat=True)
        return Unit.objects.filter(property_id__in=prop_ids).count()

    def _user_count(self) -> int:
        agency = self._agency
        if agency is None:
            return 0
        return agency.members.filter(is_active=True).count()

    def _ai_contracts_this_year(self) -> int:
        """Count LeaseBuilderSession finalizations in the current calendar year."""
        from apps.leases.models import LeaseBuilderSession
        year = timezone.now().year
        agency = self._agency
        if agency is None:
            return 0
        agent_ids = agency.members.values_list("id", flat=True)
        return LeaseBuilderSession.objects.filter(
            created_by_id__in=agent_ids,
            status="finalized",
            updated_at__year=year,
        ).count()

    def quota_statuses(self) -> list[QuotaStatus]:
        """Return a list of QuotaStatus objects for all enforced dimensions."""
        quotas = self.tier.quotas if self.tier else {}
        return [
            QuotaStatus("properties", self._property_count(), quotas.get("max_properties")),
            QuotaStatus("units", self._unit_count(), quotas.get("max_units")),
            QuotaStatus("users", self._user_count(), quotas.get("max_users")),
            QuotaStatus("ai_contracts_yearly", self._ai_contracts_this_year(), quotas.get("max_ai_contracts_yearly")),
        ]

    def quota_dict(self) -> list[dict]:
        return [qs.to_dict() for qs in self.quota_statuses()]

    def tier_info(self) -> dict:
        """Serialisable snapshot of tier + usage for the Billing tab API."""
        config = load_pricing_config()
        stripe_link = os.environ.get("STRIPE_UPGRADE_LINK", "https://klikk.co.za/pricing")
        t = self.tier
        return {
            "tier": {
                "slug": t.slug if t else "pro",
                "name": t.name if t else "Pro",
                "price_monthly": float(t.price_monthly) if t and t.price_monthly is not None else None,
                "features": t.features if t else {},
            } if t else None,
            "quotas": self.quota_dict(),
            "upgrade_url": stripe_link,
            "all_tiers": [
                {
                    "slug": slug,
                    "name": data.get("name"),
                    "price_monthly": data.get("price_monthly"),
                    "price_label": data.get("price_label"),
                    "highlight": data.get("highlight", False),
                }
                for slug, data in config.get("tiers", {}).items()
            ],
        }
