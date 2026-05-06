"""
Data migration — backfill ``agency_id`` on every per-tenant esigning model.

Resolution chain per model:

* ``ESigningSubmission``    — ``lease.agency_id`` (preferred — leases is
                              already backfilled in ``leases.0025``), fall
                              back to ``mandate.property.agency_id`` for
                              rental-mandate submissions.
* ``ESigningAuditEvent``    — ``submission.agency_id``.
* ``ESigningPublicLink``    — ``submission.agency_id``.
* ``SigningDraft``          — ``public_link.submission.agency_id``.
* ``SupportingDocument``    — ``submission.agency_id``.

Idempotent — only updates rows where ``agency_id IS NULL``. Reverse direction
clears agency_id (cosmetic, used only on full unwind).

Depends on ``leases.0025_backfill_agency_id_leases`` to ensure parent
``Lease.agency_id`` is populated before this migration walks the chain.

See ~/.claude/plans/fuzzy-giggling-squid.md (Phase 1.5) and
docs/compliance/popia-klikk-rentals-brief.md.
"""
from __future__ import annotations

from django.db import migrations


def backfill_agency_id(apps, schema_editor):
    Lease = apps.get_model("leases", "Lease")
    Property = apps.get_model("properties", "Property")
    RentalMandate = apps.get_model("properties", "RentalMandate")

    ESigningSubmission = apps.get_model("esigning", "ESigningSubmission")
    ESigningAuditEvent = apps.get_model("esigning", "ESigningAuditEvent")
    ESigningPublicLink = apps.get_model("esigning", "ESigningPublicLink")
    SigningDraft = apps.get_model("esigning", "SigningDraft")
    SupportingDocument = apps.get_model("esigning", "SupportingDocument")

    summary: list[tuple[str, int, int, int]] = []  # (label, updated, total, orphan)

    # Pre-load lookups to avoid N+1 queries.
    lease_to_agency: dict[int, int] = dict(
        Lease.objects.filter(agency_id__isnull=False).values_list("pk", "agency_id")
    )
    property_to_agency: dict[int, int] = dict(
        Property.objects.filter(agency_id__isnull=False).values_list("pk", "agency_id")
    )
    mandate_to_agency: dict[int, int] = {}
    for m in RentalMandate.objects.all().only("pk", "property_id"):
        agency_id = property_to_agency.get(m.property_id)
        if agency_id is not None:
            mandate_to_agency[m.pk] = agency_id

    # ── ESigningSubmission — lease.agency_id, else mandate.property.agency_id
    sub_qs = ESigningSubmission.objects.filter(agency__isnull=True)
    sub_total = sub_qs.count()
    sub_updated = 0
    sub_orphan = 0
    for row in sub_qs.iterator():
        agency_id = None
        if row.lease_id:
            agency_id = lease_to_agency.get(row.lease_id)
        if agency_id is None and row.mandate_id:
            agency_id = mandate_to_agency.get(row.mandate_id)
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            sub_updated += 1
        else:
            sub_orphan += 1
    summary.append(("ESigningSubmission", sub_updated, sub_total, sub_orphan))

    # Reload — children resolve via submission.agency_id.
    submission_to_agency: dict[int, int] = dict(
        ESigningSubmission.objects.filter(agency_id__isnull=False).values_list(
            "pk", "agency_id"
        )
    )

    def _backfill_via_lookup(model, fk_field: str, lookup: dict, label: str):
        qs = model.objects.filter(agency__isnull=True)
        total = qs.count()
        updated = 0
        orphan = 0
        for row in qs.iterator():
            fk_id = getattr(row, f"{fk_field}_id", None)
            agency_id = lookup.get(fk_id) if fk_id else None
            if agency_id is not None:
                row.agency_id = agency_id
                row.save(update_fields=["agency_id"])
                updated += 1
            else:
                orphan += 1
        summary.append((label, updated, total, orphan))

    _backfill_via_lookup(
        ESigningAuditEvent, "submission", submission_to_agency, "ESigningAuditEvent"
    )
    _backfill_via_lookup(
        ESigningPublicLink, "submission", submission_to_agency, "ESigningPublicLink"
    )
    _backfill_via_lookup(
        SupportingDocument, "submission", submission_to_agency, "SupportingDocument"
    )

    # SigningDraft — via public_link.submission.agency_id (resolved through
    # ESigningPublicLink which we just backfilled).
    link_to_agency: dict = dict(
        ESigningPublicLink.objects.filter(agency_id__isnull=False).values_list(
            "pk", "agency_id"
        )
    )
    draft_qs = SigningDraft.objects.filter(agency__isnull=True)
    draft_total = draft_qs.count()
    draft_updated = 0
    draft_orphan = 0
    for row in draft_qs.iterator():
        agency_id = link_to_agency.get(row.public_link_id) if row.public_link_id else None
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            draft_updated += 1
        else:
            draft_orphan += 1
    summary.append(("SigningDraft", draft_updated, draft_total, draft_orphan))

    # ── Summary ────────────────────────────────────────────────────────────
    print("\n[esigning.0013] Backfilled agency_id:")
    for label, updated, total, orphan in summary:
        print(f"  {label:<22}: {updated}/{total} updated, {orphan} orphan")


def reverse_clear(apps, schema_editor):
    """Reverse: clear agency_id on every esigning-app model touched."""
    for name in [
        "ESigningSubmission",
        "ESigningAuditEvent",
        "ESigningPublicLink",
        "SigningDraft",
        "SupportingDocument",
    ]:
        apps.get_model("esigning", name).objects.update(agency_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("esigning", "0012_add_agency_and_popia_fields_esigning"),
        ("leases", "0025_backfill_agency_id_leases"),
    ]

    operations = [
        migrations.RunPython(backfill_agency_id, reverse_code=reverse_clear),
    ]
