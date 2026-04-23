"""
0002_seed_genesis_event.py

Seeds the genesis AuditEvent that anchors the hash chain.

The genesis row has:
  prev_hash = ""        (no predecessor)
  action    = "audit.genesis"
  self_hash = SHA-256("" || canonical_json(payload))

All subsequent events will reference this row's self_hash as their prev_hash.
"""

import hashlib
import json

from django.db import migrations
from django.utils import timezone


def _canonical_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def _compute_hash(prev_hash: str, payload: dict) -> str:
    raw = prev_hash + _canonical_json(payload)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def seed_genesis(apps, schema_editor):
    AuditEvent = apps.get_model("audit", "AuditEvent")

    # Only seed if the table is empty (idempotent)
    if AuditEvent.objects.exists():
        return

    # Construct the genesis event — actor/content_type/object_id all null
    genesis_ts = timezone.now()
    event = AuditEvent(
        actor=None,
        actor_email="",
        action="audit.genesis",
        content_type=None,
        object_id=None,
        target_repr="GENESIS — hash chain anchor",
        before_snapshot=None,
        after_snapshot={"note": "Hash chain genesis event.  Do not modify or delete."},
        ip_address=None,
        user_agent="",
        timestamp=genesis_ts,
        prev_hash="",
        self_hash="",
        retention_years=99,  # retain forever
    )
    event.save()

    # Compute canonical payload (needs PK)
    payload = {
        "id": event.id,
        "actor_id": None,
        "actor_email": "",
        "action": "audit.genesis",
        "content_type_id": None,
        "object_id": None,
        "target_repr": "GENESIS — hash chain anchor",
        "before_snapshot": None,
        "after_snapshot": {"note": "Hash chain genesis event.  Do not modify or delete."},
        "ip_address": None,
        "user_agent": "",
        "timestamp": genesis_ts.isoformat(),
        "retention_years": 99,
    }
    event.self_hash = _compute_hash("", payload)
    event.save()


def unseed_genesis(apps, schema_editor):
    AuditEvent = apps.get_model("audit", "AuditEvent")
    AuditEvent.objects.filter(action="audit.genesis").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_genesis, reverse_code=unseed_genesis),
    ]
