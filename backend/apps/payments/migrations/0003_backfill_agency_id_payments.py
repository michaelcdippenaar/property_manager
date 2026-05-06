"""
Data migration — backfill ``agency_id`` on every payments-app model.

Resolution chain per model:

* ``RentInvoice``        — ``lease.agency_id`` (already set by leases.0025).
* ``RentPayment``        — ``invoice.lease.agency_id`` via the parent invoice.
* ``UnmatchedPayment``   — ``assigned_to_invoice.lease.agency_id`` when the
                            unmatched payment has been reconciled; otherwise
                            left null (operator triages and assigns later).
* ``PaymentAuditLog``    — ``actor.agency_id`` first, then a per-entity-type
                            lookup (invoice/payment/unmatched → invoice →
                            lease → agency). Logs without an actor or a
                            resolvable entity are left null.

Idempotent — only updates rows where ``agency_id IS NULL``. Reverse direction
clears agency_id (cosmetic, used only on full unwind).

Depends on ``leases.0025`` so ``Lease.agency_id`` is settled before this
migration runs.
"""
from __future__ import annotations

from django.db import migrations


def backfill_agency_id(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Lease = apps.get_model("leases", "Lease")

    RentInvoice = apps.get_model("payments", "RentInvoice")
    RentPayment = apps.get_model("payments", "RentPayment")
    UnmatchedPayment = apps.get_model("payments", "UnmatchedPayment")
    PaymentAuditLog = apps.get_model("payments", "PaymentAuditLog")

    summary: list[tuple[str, int, int, int]] = []

    lease_to_agency: dict[int, int] = dict(
        Lease.objects.filter(agency_id__isnull=False).values_list("pk", "agency_id")
    )
    user_to_agency: dict[int, int] = {
        u.pk: u.agency_id
        for u in User.objects.filter(agency_id__isnull=False).only("pk", "agency_id")
    }

    # ── RentInvoice — via lease ────────────────────────────────────────────
    inv_qs = RentInvoice.objects.filter(agency__isnull=True)
    inv_total = inv_qs.count()
    inv_updated = 0
    inv_orphan = 0
    for row in inv_qs.iterator():
        agency_id = lease_to_agency.get(row.lease_id) if row.lease_id else None
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            inv_updated += 1
        else:
            inv_orphan += 1
    summary.append(("RentInvoice", inv_updated, inv_total, inv_orphan))

    invoice_to_agency: dict[int, int] = dict(
        RentInvoice.objects.filter(agency_id__isnull=False).values_list(
            "pk", "agency_id"
        )
    )

    # ── RentPayment — via invoice ──────────────────────────────────────────
    pay_qs = RentPayment.objects.filter(agency__isnull=True)
    pay_total = pay_qs.count()
    pay_updated = 0
    pay_orphan = 0
    for row in pay_qs.iterator():
        agency_id = invoice_to_agency.get(row.invoice_id) if row.invoice_id else None
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            pay_updated += 1
        else:
            pay_orphan += 1
    summary.append(("RentPayment", pay_updated, pay_total, pay_orphan))

    # ── UnmatchedPayment — via assigned invoice (if reconciled) ────────────
    um_qs = UnmatchedPayment.objects.filter(agency__isnull=True)
    um_total = um_qs.count()
    um_updated = 0
    um_orphan = 0
    for row in um_qs.iterator():
        agency_id = (
            invoice_to_agency.get(row.assigned_to_invoice_id)
            if row.assigned_to_invoice_id
            else None
        )
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            um_updated += 1
        else:
            um_orphan += 1
    summary.append(("UnmatchedPayment", um_updated, um_total, um_orphan))

    # ── PaymentAuditLog — actor.agency first, then entity chain ────────────
    log_qs = PaymentAuditLog.objects.filter(agency__isnull=True)
    log_total = log_qs.count()
    log_updated = 0
    log_orphan = 0
    for row in log_qs.iterator():
        agency_id = user_to_agency.get(row.actor_id) if row.actor_id else None
        if agency_id is None and row.entity_id:
            if row.entity_type == "invoice":
                agency_id = invoice_to_agency.get(row.entity_id)
            elif row.entity_type == "payment":
                lookup_inv_id = (
                    RentPayment.objects.filter(pk=row.entity_id)
                    .values_list("invoice_id", flat=True)
                    .first()
                )
                if lookup_inv_id is not None:
                    agency_id = invoice_to_agency.get(lookup_inv_id)
            elif row.entity_type == "unmatched":
                lookup_inv_id = (
                    UnmatchedPayment.objects.filter(pk=row.entity_id)
                    .values_list("assigned_to_invoice_id", flat=True)
                    .first()
                )
                if lookup_inv_id is not None:
                    agency_id = invoice_to_agency.get(lookup_inv_id)
        if agency_id is None and row.lease_id:
            agency_id = lease_to_agency.get(row.lease_id)
        if agency_id is not None:
            row.agency_id = agency_id
            row.save(update_fields=["agency_id"])
            log_updated += 1
        else:
            log_orphan += 1
    summary.append(("PaymentAuditLog", log_updated, log_total, log_orphan))

    print("\n[payments.0003] Backfilled agency_id:")
    for label, updated, total, orphan in summary:
        print(f"  {label:<20}: {updated}/{total} updated, {orphan} orphan")


def reverse_clear(apps, schema_editor):
    for name in ["RentInvoice", "RentPayment", "UnmatchedPayment", "PaymentAuditLog"]:
        apps.get_model("payments", name).objects.update(agency_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0002_add_agency_and_popia_fields_payments"),
        ("leases", "0025_backfill_agency_id_leases"),
        ("accounts", "0024_backfill_agency_id_accounts"),
    ]

    operations = [
        migrations.RunPython(backfill_agency_id, reverse_code=reverse_clear),
    ]
