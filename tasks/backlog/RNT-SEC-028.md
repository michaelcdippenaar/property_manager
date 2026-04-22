---
id: RNT-SEC-028
stream: rentals
title: "Restrict GotenbergHealthView to admin-only to prevent infrastructure disclosure"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214200406225875"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Prevent any authenticated agent from mapping internal infrastructure (Chromium, LibreOffice versions) via `GET /api/v1/esigning/gotenberg/health/` by restricting access or stripping sensitive fields.

## Acceptance criteria
- [ ] `GotenbergHealthView` restricted to `IsAdminUser` only (not agents), OR response strips engine names and version strings before returning to client, OR endpoint gated behind `ENABLE_TEST_ENDPOINTS` setting
- [ ] Test asserts a non-admin agent user receives HTTP 403 on `GET /api/v1/esigning/gotenberg/health/`
- [ ] Admin users can still access the endpoint for operational monitoring

## Files likely touched
- `backend/apps/esigning/views.py`
- `backend/apps/test_hub/esigning/` (new test)

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/esigning/ -k gotenberg`

## Handoff notes
Promoted from discovery `2026-04-22-gotenberg-health-endpoint-recon.md` (found during RNT-SEC-004). Information-disclosure vector: agents can map internal service versions.
