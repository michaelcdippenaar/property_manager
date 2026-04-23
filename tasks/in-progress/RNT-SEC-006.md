---
id: RNT-SEC-006
stream: rentals
title: "POPIA s23 / s24 self-service: data subject access + right-to-be-forgotten"
feature: ""
lifecycle_stage: null
priority: P1
effort: L
v1_phase: "1.0"
status: backlog
asana_gid: "1214177462154266"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Give tenants, owners, and prospects a self-service way to request a copy of their personal information (POPIA s23) and to request deletion (s24), and give operators an audited workflow to fulfil those requests inside statutory timelines.

## Acceptance criteria
- [ ] Tenant web app + mobile: "My data" screen → "Download my data" + "Delete my account" buttons
- [ ] Data export: JSON + PDF summary of all personal info held across profile, leases, maintenance, payments, comms (attachments bundled as zip)
- [ ] Deletion request: 30-day review window (operator can block if legal retention applies), then hard-delete or anonymise per retention rules
- [ ] Retention rules respected: FICA 5-year, lease records 5-year post-termination, tax 7-year — deletion anonymises but preserves structural records
- [ ] Operator admin screen: `DSAR queue` showing pending requests with SLA countdown (30 days default)
- [ ] Audit log entry for every access/export/deletion
- [ ] SAR response within 30 days (timer visible); RTBF reviewed within 30 days
- [ ] POPIA compliance: documented in `docs/compliance/popia-dsar.md`

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
