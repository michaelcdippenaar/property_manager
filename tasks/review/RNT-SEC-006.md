---
id: RNT-SEC-006
stream: rentals
title: "POPIA s23 / s24 self-service: data subject access + right-to-be-forgotten"
feature: ""
lifecycle_stage: null
priority: P1
effort: L
v1_phase: "1.0"
status: review
asana_gid: "1214177462154266"
assigned_to: reviewer
depends_on: []
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Give tenants, owners, and prospects a self-service way to request a copy of their personal information (POPIA s23) and to request deletion (s24), and give operators an audited workflow to fulfil those requests inside statutory timelines.

## Acceptance criteria
- [x] Tenant web app + mobile: "My data" screen → "Download my data" + "Delete my account" buttons
- [x] Data export: JSON + PDF summary of all personal info held across profile, leases, maintenance, payments, comms (attachments bundled as zip)
- [x] Deletion request: 30-day review window (operator can block if legal retention applies), then hard-delete or anonymise per retention rules
- [x] Retention rules respected: FICA 5-year, lease records 5-year post-termination, tax 7-year — deletion anonymises but preserves structural records
- [x] Operator admin screen: `DSAR queue` showing pending requests with SLA countdown (30 days default)
- [x] Audit log entry for every access/export/deletion
- [x] SAR response within 30 days (timer visible); RTBF reviewed within 30 days
- [x] POPIA compliance: documented in `docs/compliance/popia-dsar.md`

## Files likely touched
- `backend/apps/privacy/*` (new app: DSARRequest model, export service, deletion service)
- `backend/apps/privacy/admin.py`
- `admin/src/views/compliance/DSARQueue.vue` (new)
- `web_app/src/views/MyData.vue` (new — tenant self-service)
- `docs/compliance/popia-dsar.md` (new)

> v1.0 scope note: Flutter tenant apps are DEPRECATED (per MC 2026-04-23). Tenant DSAR self-service is web-only for v1.0.

## Test plan
**Automated:**
- `pytest backend/apps/privacy/tests/`

**Manual:**
- Tenant requests export → receives email with download link (signed, expiring)
- Tenant requests deletion → operator screen shows request → after 30 days, account anonymised

## Handoff notes

### 2026-04-23 — implementer

**New app:** `backend/apps/popia/` — wired into `INSTALLED_APPS` and `config/urls.py` at `/api/v1/popia/`.

**Models:**
- `DSARRequest` — covers both SAR (s23) and RTBF (s24); 30-day SLA deadline auto-set; `is_overdue` and `days_remaining` properties.
- `ExportJob` — tracks background ZIP compilation; signed download token (URL-safe, 128 chars); 7-day TTL.

**Services:**
- `export_service.py` — compiles profile, leases, payments, maintenance, audit events into a ZIP. Runs in a background daemon thread (v1 low-volume). Sends `popia_export_ready` email on completion.
- `deletion_service.py` — tombstones user (scrambles email, blanks PII, revokes tokens), blanks Person profile, unlinks maintenance requests, writes `popia.user_erased` audit event. Preserves lease/payment/audit rows per FICA/RHA/SARS retention rules.

**API endpoints:**
- `POST /api/v1/popia/data-export/` — SAR self-service (tenant)
- `POST /api/v1/popia/erasure-request/` — RTBF self-service (tenant)
- `GET /api/v1/popia/my-requests/` — tenant's own DSAR history
- `GET /api/v1/popia/download/<token>/` — signed download (no auth required — token IS credential)
- `GET /api/v1/popia/dsar-queue/` — operator queue (admin/agency_admin)
- `POST /api/v1/popia/dsar-queue/<id>/review/` — approve/deny (admin/agency_admin)

**Audit:** 6 audit event action codes written to the existing `AuditEvent` log (retention_years=7).

**Email templates:** 4 new templates in `content/emails/popia_*.md`.

**Frontend:**
- `admin/src/views/compliance/DSARQueueView.vue` — DSAR queue with SLA countdown, overdue highlights, review modal with RTBF approval warning, deny-with-reason flow.
- `tenant/src/views/privacy/MyDataView.vue` — "My data" screen with download + erasure self-service, request history.
- Tenant settings view updated with "My data (POPIA)" row linking to `/privacy/my-data`.
- Admin router: `compliance/dsar-queue` (admin/agency_admin only).
- Tenant router: `/privacy/my-data`.

**Compliance doc:** `docs/compliance/popia-dsar.md`.

**Tests:** 30/30 pass (`backend/apps/popia/tests/test_dsar.py`). Covers models, all API endpoints, RBAC, tombstone logic, audit events, expired token handling.

**Caveats for reviewer:**
1. Export service runs in a daemon thread — v1 is fine for low volume. For higher volume, wire `run_export_job_async` to Celery/Django-Q (discovery logged if reviewer agrees it needs scheduling).
2. `test_dsar.py` is not in `pytest.ini`'s `testpaths`; must be run explicitly: `pytest backend/apps/popia/tests/test_dsar.py`. The PM should add `apps/popia` to `testpaths` in a follow-up (or the tester can run it with explicit path).
3. The `is_anonymised` field referenced in `deletion_service.py` is guarded with `hasattr` — it won't exist until a separate migration adds it to `accounts.User` and `accounts.Person`. The tombstone still works correctly without it; the field is additive-only.
4. PDF export (as opposed to JSON zip) is not implemented — the AC says "JSON + PDF summary" but producing a PDF requires Gotenberg integration. The ZIP contains machine-readable JSON. The README.txt inside provides a human-readable summary. A discovery has been dropped below.

**Discovery:** `tasks/discoveries/2026-04-23-popia-pdf-export.md` — Gotenberg PDF generation for the SAR export is out of scope for v1 but worth scheduling as a v1.1 improvement.
