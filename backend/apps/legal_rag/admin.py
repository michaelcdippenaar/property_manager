"""Django admin registrations for the legal RAG store.

Design intent (per ``content/cto/centralised-legal-rag-store-plan.md``
§5 audit trail + §11 attestation storage):

* :class:`~apps.legal_rag.models.LegalFact` and
  :class:`~apps.legal_rag.models.LegalFactVersion` rows are edited via
  YAML PRs (the workflow lives in git, not Django admin). Admin is
  registered read-only so internal staff can search/inspect facts but
  cannot mutate them through the UI — that would bypass the
  PR-as-lawyer-review-workflow.
* :class:`~apps.legal_rag.models.LegalAttestation` is append-only at the
  model layer (``save()`` raises on update). Admin reinforces this by
  prohibiting edit *and* delete actions; new attestations are still
  creatable via the admin so MC can record a lawyer opinion letter
  without writing YAML by hand.
* :class:`~apps.legal_rag.models.LegalCorpusVersion` is set by
  ``manage.py sync_legal_facts``. Admin is read-only — bumping the
  active version through the UI would corrupt the audit trail.

All four models are surfaced in admin (list, detail, search, filter) so
the team can inspect state during incident response without needing to
SSH into the database.
"""
from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from .models import (
    LegalAttestation,
    LegalCorpusVersion,
    LegalFact,
    LegalFactVersion,
)


# ── Helpers ───────────────────────────────────────────────────────────── #


class _ReadOnlyModelAdmin(admin.ModelAdmin):
    """Inspect-only admin: no add, no change, no delete."""

    def has_add_permission(self, request: HttpRequest) -> bool:  # type: ignore[override]
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: Any = None
    ) -> bool:  # type: ignore[override]
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: Any = None
    ) -> bool:  # type: ignore[override]
        return False


class _AppendOnlyModelAdmin(admin.ModelAdmin):
    """Create + read, never update or delete.

    Used for :class:`LegalAttestation` — the model itself raises on
    ``save()`` of an existing row, but admin needs to express the same
    constraint up front so staff don't see a "Save" button on edit pages
    that would only fail at submit.
    """

    def has_change_permission(
        self, request: HttpRequest, obj: Any = None
    ) -> bool:  # type: ignore[override]
        # Allow viewing the change form (Django uses change_view for detail)
        # but prevent actual save by setting all fields read-only when
        # editing an existing row — see ``get_readonly_fields`` below.
        return True

    def has_delete_permission(
        self, request: HttpRequest, obj: Any = None
    ) -> bool:  # type: ignore[override]
        return False

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None):  # type: ignore[override]
        # When obj is None we're on the "add" page → all fields editable.
        # When obj exists we're on "change" page → freeze everything.
        if obj is None:
            return super().get_readonly_fields(request, obj)
        return [field.name for field in obj._meta.fields]


# ── LegalFact ─────────────────────────────────────────────────────────── #


@admin.register(LegalFact)
class LegalFactAdmin(_ReadOnlyModelAdmin):
    list_display = (
        "concept_id",
        "citation_string",
        "type",
        "citation_confidence",
        "verification_status",
        "legal_provisional",
        "updated_at",
    )
    list_filter = (
        "type",
        "citation_confidence",
        "verification_status",
        "legal_provisional",
    )
    search_fields = ("concept_id", "citation_string", "plain_english_summary")
    readonly_fields = tuple(field.name for field in LegalFact._meta.fields)
    ordering = ("concept_id",)


# ── LegalFactVersion ──────────────────────────────────────────────────── #


@admin.register(LegalFactVersion)
class LegalFactVersionAdmin(_ReadOnlyModelAdmin):
    list_display = (
        "fact",
        "version",
        "content_hash",
        "created_at",
        "attestation",
    )
    list_filter = ("created_at",)
    search_fields = ("fact__concept_id", "content_hash")
    readonly_fields = tuple(field.name for field in LegalFactVersion._meta.fields)
    ordering = ("-created_at",)


# ── LegalAttestation ──────────────────────────────────────────────────── #


@admin.register(LegalAttestation)
class LegalAttestationAdmin(_AppendOnlyModelAdmin):
    list_display = (
        "attestation_id",
        "attorney_name",
        "attorney_firm",
        "attestation_method",
        "attestation_date",
        "cost_zar",
    )
    list_filter = ("attestation_method", "attestation_date")
    search_fields = (
        "attestation_id",
        "attorney_name",
        "attorney_firm",
        "attorney_admission_number",
    )
    ordering = ("-attestation_date",)


# ── LegalCorpusVersion ────────────────────────────────────────────────── #


@admin.register(LegalCorpusVersion)
class LegalCorpusVersionAdmin(_ReadOnlyModelAdmin):
    list_display = (
        "version",
        "fact_count",
        "embedding_model",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "embedding_model")
    search_fields = ("version", "merkle_root")
    readonly_fields = tuple(field.name for field in LegalCorpusVersion._meta.fields)
    ordering = ("-created_at",)
