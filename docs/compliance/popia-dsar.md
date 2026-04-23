# POPIA DSAR Compliance — Klikk Rentals v1

**Document owner:** Information Officer  
**Version:** 1.0  
**Effective date:** 2026-04-23  
**Regulation:** Protection of Personal Information Act 4 of 2013 (POPIA) — sections 23 and 24

---

## Overview

Klikk provides data subjects (tenants, owners, prospects) with two self-service rights:

| Right | Section | Mechanism | SLA |
|-------|---------|-----------|-----|
| Subject Access Request (SAR) — copy of personal information | s23 POPIA | `POST /api/v1/popia/data-export/` | 30 days |
| Right to Erasure / Be Forgotten (RTBF) | s24 POPIA | `POST /api/v1/popia/erasure-request/` | 30 days (operator review) |

---

## Data Flows

### SAR (Section 23 — Access)

1. Data subject clicks "Download my data" in the tenant web app or mobile settings.
2. Frontend calls `POST /api/v1/popia/data-export/`.
3. Backend creates a `DSARRequest` (type=SAR, status=in_review) and an `ExportJob` (status=queued).
4. An audit event `popia.sar_requested` is written to the append-only `AuditEvent` log.
5. A background thread compiles the data export ZIP containing:
   - `profile.json` — User + Person profile fields
   - `leases.json` — Lease records where the data subject is a party
   - `payments.json` — Payment records linked to those leases
   - `maintenance.json` — Maintenance tickets submitted by the user
   - `audit_events.json` — Audit events where the user is the actor
   - `README.txt` — Human-readable retention statement
6. On completion, the system emails a signed download link to the data subject's email address.
   The link is a URL-safe 128-character token with a 7-day TTL.
7. The data subject downloads the ZIP via `GET /api/v1/popia/download/<token>/`.
8. An audit event `popia.export_downloaded` is written on download.

### RTBF (Section 24 — Erasure)

1. Data subject clicks "Delete my account" in the tenant web app settings.
2. Frontend calls `POST /api/v1/popia/erasure-request/` (optionally with a `reason`).
3. Backend creates a `DSARRequest` (type=RTBF, status=pending).
4. An audit event `popia.rtbf_requested` is written.
5. An alert email is sent to `POPIA_OFFICER_EMAIL` (default: `privacy@klikk.co.za`).
6. An operator reviews the request in the DSAR queue (`GET /api/v1/popia/dsar-queue/`).
7. Operator approves or denies via `POST /api/v1/popia/dsar-queue/<id>/review/`.
8. **On approval:** `execute_erasure()` is called:
   - User email scrambled to `<sha256_prefix>@deleted.klikk.co.za`
   - PII fields cleared: `first_name`, `last_name`, `phone`, `id_number`
   - `is_active=False`, password set unusable
   - All JWT tokens, OTP codes, and push tokens revoked
   - Linked `Person` profile PII blanked
   - Maintenance request `submitted_by` FK set to null
   - Audit event `popia.user_erased` written (retention_years=7)
   - Confirmation email sent to the original address (before scramble)
9. **On denial:** Denial reason recorded, data subject notified by email.
   Data subject may lodge a complaint with the Information Regulator.

---

## Retention Rules

Deletion anonymises but preserves structural records as required by law.

| Record type | Retention | Authority |
|-------------|-----------|-----------|
| Lease agreements | 5 years post-termination | RHA s13 / FICA s22 |
| Payment records | 7 years | SARS / Income Tax Act s73 |
| Audit events | 5 years minimum | FICA s22 |
| User PII | Deleted on erasure approval | POPIA s14 |
| Person profile PII | Anonymised on erasure approval | POPIA s14 |
| Maintenance tickets | Anonymised (author unlinked) | POPIA s14 |

Records falling within retention windows are NOT deleted. The structural row is
preserved with PII replaced by hash placeholders or blanked fields. This is
permitted under POPIA s11(3)(a) (legal obligation) and s14(4) (retention override).

---

## DSAR Queue — Operator Workflow

| Step | Action | System state |
|------|--------|--------------|
| Request received | Data subject submits | `DSARRequest.status = pending` |
| Operator picks up | Operator opens queue | `status = in_review` |
| Operator approves | Calls review endpoint with `action=approve` | `status = approved` then `completed` (RTBF) or `approved` (SAR) |
| Operator denies | Calls review endpoint with `action=deny` + `denial_reason` | `status = denied` |

The operator queue at `/admin/compliance/dsar-queue` shows:
- SLA deadline and days remaining (red when overdue)
- Request type badge (SAR / Erasure)
- One-click review modal with approval/denial workflow

---

## SLA Compliance

- SAR: 30-day statutory deadline (POPIA s23).
- RTBF: 30-day review window (POPIA s24).
- The DSAR queue sorts requests by `sla_deadline` ascending — most urgent at the top.
- `DSARRequest.is_overdue` property returns `True` when `now > sla_deadline` and status is not terminal.
- Overdue rows are highlighted red in the queue UI.

---

## Audit Trail

Every POPIA action writes an immutable `AuditEvent` row with `retention_years=7`:

| Action code | Trigger |
|-------------|---------|
| `popia.sar_requested` | Data subject submits SAR |
| `popia.rtbf_requested` | Data subject submits RTBF |
| `popia.export_downloaded` | Data subject downloads export ZIP |
| `popia.dsar_approved` | Operator approves any DSAR request |
| `popia.dsar_denied` | Operator denies any DSAR request |
| `popia.user_erased` | User account anonymised (RTBF approved) |

Audit events are hash-chained (SHA-256) and append-only — tampering is detectable.

---

## Information Officer

All POPIA queries and complaints should be directed to:

- **Email:** privacy@klikk.co.za
- **External escalation:** Information Regulator (South Africa) at complaints.IR@justice.gov.za

---

## Technical References

- Backend app: `backend/apps/popia/`
- Models: `DSARRequest`, `ExportJob`
- Services: `export_service.py`, `deletion_service.py`
- Admin UI: `admin/src/views/compliance/DSARQueueView.vue`
- Tenant UI: `tenant/src/views/privacy/MyDataView.vue`
- Email templates: `content/emails/popia_*.md`
- Tests: `backend/apps/popia/tests/test_dsar.py`
