"""Klikk → Vault33 bridge (read-only, no FK).

Thin wrapper around the `vault33_client` PyPI-style package. Gives Klikk app
code a single entry point to read vault entity data without coupling to
Vault33's Django models. Every call writes a DataCheckout audit row on the
Vault33 side (delivery_method=INTERNAL, authorisation_method=AUTO_GRANT).

Design rule (see plan spec "Data Sovereignty Architecture"): no Django
ForeignKey from any Klikk model to any Vault33 model. Downstream models store
`vault_entity_id` as a plain PositiveIntegerField and fetch via this helper.

This module is a bridge + POC only. It is NOT wired into Person, Lease, or any
existing Klikk model. The Person→VaultEntity data migration is a separate
future phase.
"""
from __future__ import annotations

from django.conf import settings

from vault33_client import Vault33Client, Vault33ClientError


def _client() -> Vault33Client:
    base_url = getattr(settings, "VAULT33_BASE_URL", "") or ""
    token = getattr(settings, "VAULT33_INTERNAL_TOKEN", "") or ""
    if not base_url or not token:
        raise RuntimeError(
            "VAULT33_BASE_URL / VAULT33_INTERNAL_TOKEN not configured. "
            "Set them in the Klikk .env and match them to Vault33's "
            "VOLT_INTERNAL_SHARED_TOKEN."
        )
    return Vault33Client(base_url=base_url, internal_token=token)


def fetch_vault_entity(vault_owner_id: int, vault_entity_id: int, caller: str) -> dict:
    """Fetch a vault entity from Vault33 via the internal gateway.

    Args:
        vault_owner_id: PK of the ``VaultOwner`` in Vault33 (NOT the Klikk user id).
        vault_entity_id: PK of the ``VaultEntity`` in Vault33.
        caller: Short identifier of the calling module, e.g. ``"klikk.leases"``.
                Shown in Vault33 audit logs.

    Returns:
        Dict with keys: ``id``, ``entity_type``, ``name``, ``data``,
        ``_checkout_token`` (audit row id on Vault33 side).

    Raises:
        Vault33ClientError: on non-2xx from the gateway.
        RuntimeError: if settings are not configured.
    """
    return _client().fetch_entity(
        vault_owner_id=vault_owner_id,
        entity_id=vault_entity_id,
        caller_module=caller,
    )


__all__ = ["fetch_vault_entity", "Vault33ClientError"]
