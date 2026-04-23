"""POC management command: fetch a Vault33 entity via the internal gateway.

Usage:
    python manage.py fetch_vault_entity_poc --owner-id 1 --entity-id 36

Proves the multi-consumer thesis: Klikk reads vault data with no Django FK to
Vault33, only HTTP + shared token + a thin client lib. Every fetch writes an
audit row on the Vault33 side.
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from apps.integrations.vault33 import fetch_vault_entity, Vault33ClientError


class Command(BaseCommand):
    help = "POC: fetch a Vault33 entity via the internal gateway"

    def add_arguments(self, parser):
        parser.add_argument("--owner-id", type=int, required=True, help="VaultOwner PK in Vault33")
        parser.add_argument("--entity-id", type=int, required=True, help="VaultEntity PK in Vault33")
        parser.add_argument("--caller", type=str, default="klikk.poc", help="caller_module tag")

    def handle(self, *args, **opts):
        owner_id = opts["owner_id"]
        entity_id = opts["entity_id"]
        caller = opts["caller"]

        self.stdout.write(
            f"Fetching vault entity owner={owner_id} entity={entity_id} caller={caller} …"
        )
        try:
            entity = fetch_vault_entity(
                vault_owner_id=owner_id,
                vault_entity_id=entity_id,
                caller=caller,
            )
        except Vault33ClientError as exc:
            raise CommandError(f"Vault33 gateway error: {exc}")
        except Exception as exc:
            raise CommandError(f"Fetch failed: {exc}")

        self.stdout.write(self.style.SUCCESS("Entity fetched OK"))
        self.stdout.write(f"  id            : {entity['id']}")
        self.stdout.write(f"  entity_type   : {entity['entity_type']}")
        self.stdout.write(f"  name          : {entity['name']}")
        self.stdout.write(f"  checkout_token: {entity.get('_checkout_token')}")
        self.stdout.write("  data (redacted summary):")
        data = entity.get("data") or {}
        for k in sorted(data.keys()):
            val = data[k]
            if isinstance(val, str) and len(val) > 60:
                val = val[:57] + "..."
            self.stdout.write(f"    {k}: {val}")
        self.stdout.write("")
        self.stdout.write("Full JSON response:")
        self.stdout.write(json.dumps(entity, indent=2, default=str))
