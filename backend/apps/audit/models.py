"""
apps/audit/models.py

Tamper-evident audit log for high-risk actions (RNT-SEC-008).

Every event that modifies a RentalMandate, Lease, ESigningSubmission,
RentPayment or changes a User's role is appended here as an AuditEvent row.

Hash-chain guarantee
---------------------
Each row carries:
  prev_hash  — self_hash of the immediately preceding row (empty string for genesis)
  self_hash  — SHA-256( prev_hash || canonical_json(payload) )

The chain makes silent row deletion or mutation detectable:
  verify_audit_chain management command walks from genesis → latest
  and recomputes each self_hash.

Retention
---------
Events are never deleted.  The `retention_years` field is informational only;
enforcement is left to a periodic archiver (OPS task).  Minimum 5 years per
FICA + RHA requirements.
"""

from __future__ import annotations

import hashlib
import json

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from apps.accounts.tenancy import TenantManager
from django.utils import timezone

from apps.popia.choices import LawfulBasis, RetentionPolicy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _canonical_json(data: dict) -> str:
    """Deterministic JSON serialisation used in hash computation."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def compute_self_hash(prev_hash: str, payload: dict) -> str:
    """
    SHA-256( prev_hash || canonical_json(payload) )

    prev_hash is the empty string "" for the genesis row.
    payload is the full canonical event dict (see AuditEvent.canonical_payload).
    """
    raw = prev_hash + _canonical_json(payload)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class AuditEvent(models.Model):
    """
    One immutable row per auditable action.

    Never UPDATE or DELETE rows — this is an append-only log.
    The hash chain will detect any tampering.
    """

    # ── Tenancy / POPIA ──────────────────────────────────────────────────── #
    # Owning agency / tenant. Denormalised directly on the audit row — this is
    # the most security-critical scoping in the codebase: an agency must
    # never see another agency's audit trail. Resolved at write time from
    # actor.agency_id (system events stay null; cleaned up at Phase 4 cutover).
    # Deliberately NOT included in canonical_payload() — adding a tenancy
    # marker after the fact must not invalidate existing hash-chain rows.
    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="audit_events",
        help_text="Owning agency / tenant. Denormalised from actor.agency.",
    )
    # POPIA s11(1)(c) — keeping a tamper-evident audit trail is a legal
    # obligation under FICA s42/43 and the EAAB Code of Conduct.
    lawful_basis = models.CharField(
        max_length=32, choices=LawfulBasis.choices,
        default=LawfulBasis.LEGAL_OBLIGATION,
        help_text="POPIA s11 basis. Audit trails = legal obligation (FICA / EAAB).",
    )
    # POPIA s14 read with s19 — audit rows are append-only and survive
    # subject anonymisation. Subject references inside snapshots get
    # anonymised at the parent's retention window; the row itself stays.
    retention_policy = models.CharField(
        max_length=32, choices=RetentionPolicy.choices,
        default=RetentionPolicy.AUDIT_PERMANENT,
        help_text="POPIA s14 retention. Audit trail permanent — references anonymised.",
    )

    # ── Actor ────────────────────────────────────────────────────────────── #
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events_authored",
        help_text="User who triggered the action (null = system/signal-driven)",
    )
    actor_email = models.EmailField(
        blank=True,
        help_text="Denormalised email at time of action for resilience against user deletion",
    )

    # ── Action ───────────────────────────────────────────────────────────── #
    action = models.CharField(
        max_length=80,
        help_text=(
            "Machine-readable action code, e.g. 'lease.created', 'mandate.status_changed', "
            "'payment.reversed', 'user.role_changed'"
        ),
    )

    # ── Target (GFK) ─────────────────────────────────────────────────────── #
    content_type = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Django ContentType of the target object",
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="PK of the target object",
    )
    target = GenericForeignKey("content_type", "object_id")

    # Denormalised human label — cheap lookup without a join
    target_repr = models.CharField(
        max_length=255,
        blank=True,
        help_text="str() of the target object at the time of the event",
    )

    # ── Snapshots ────────────────────────────────────────────────────────── #
    before_snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text="Model field dict before this change (null for creation events)",
    )
    after_snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text="Model field dict after this change (null for deletion events)",
    )

    # ── Request context ──────────────────────────────────────────────────── #
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Client IP at time of action (null for signal-only/system events)",
    )
    user_agent = models.TextField(
        blank=True,
        help_text="HTTP User-Agent at time of action",
    )

    # ── Timestamp ────────────────────────────────────────────────────────── #
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="UTC timestamp of the event",
    )

    # ── Hash chain ───────────────────────────────────────────────────────── #
    prev_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="self_hash of the immediately preceding AuditEvent ('' for genesis)",
    )
    self_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="SHA-256 of (prev_hash || canonical_json(payload))",
    )

    # ── Retention marker ─────────────────────────────────────────────────── #
    retention_years = models.PositiveSmallIntegerField(
        default=5,
        help_text="Minimum years to retain this event (FICA=5, RHA=3; default 5)",
    )

    class Meta:
        ordering = ["id"]  # chain order is insertion order
        indexes = [
            models.Index(fields=["content_type", "object_id", "timestamp"]),
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["agency", "timestamp"], name="audit_event_agency_ts_idx"),
        ]
        verbose_name = "Audit Event"
        verbose_name_plural = "Audit Events"

    def __str__(self) -> str:
        return f"[{self.id}] {self.action} @ {self.timestamp:%Y-%m-%d %H:%M:%S}"

    # ── Hash helpers ─────────────────────────────────────────────────────── #

    def canonical_payload(self) -> dict:
        """
        Deterministic dict used as the hash input.

        Uses stable field values only — no Python object references.
        """
        return {
            "id": self.id,
            "actor_id": self.actor_id,
            "actor_email": self.actor_email,
            "action": self.action,
            "content_type_id": self.content_type_id,
            "object_id": self.object_id,
            "target_repr": self.target_repr,
            "before_snapshot": self.before_snapshot,
            "after_snapshot": self.after_snapshot,
            "ip_address": str(self.ip_address) if self.ip_address else None,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp.isoformat(),
            "retention_years": self.retention_years,
        }

    def compute_hash(self) -> str:
        """Return the expected self_hash for this event."""
        return compute_self_hash(self.prev_hash, self.canonical_payload())

    def is_hash_valid(self) -> bool:
        """True when self_hash matches recomputed value."""
        return self.self_hash == self.compute_hash()

    # Multi-tenant managers (Phase 2.1) — `objects` stays default,
    # `tenant_objects` auto-scopes to current_agency_id().
    objects = models.Manager()
    tenant_objects = TenantManager()
