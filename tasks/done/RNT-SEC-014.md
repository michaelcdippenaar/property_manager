---
id: RNT-SEC-014
stream: rentals
title: "Restrict GotenbergHealthView to admin-only or strip version/engine fields from response"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: done
assigned_to: null
depends_on: []
asana_gid: "1214235733132846"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Prevent authenticated agents from using the Gotenberg health endpoint to enumerate internal infrastructure (Chromium/LibreOffice versions, engine names).

## Acceptance criteria
- [ ] `GotenbergHealthView` is restricted to `IsAdminUser` only (not agents), OR gated behind `ENABLE_TEST_ENDPOINTS`, OR strips version/engine fields from the proxied response before returning to the client
- [ ] A test asserts that an agent (non-admin) user receives HTTP 403 on `GET /api/v1/esigning/gotenberg/health/`
- [ ] Admin users can still reach the endpoint for operational monitoring

## Files likely touched
- `backend/apps/esigning/views.py` (`GotenbergHealthView`, ~line 387)
- `backend/apps/esigning/urls.py` (route at `gotenberg/health/`)
- `backend/apps/test_hub/esigning/` (new test)

## Test plan
**Manual:**
- Log in as agent role → `GET /api/v1/esigning/gotenberg/health/` → expect 403
- Log in as admin → same endpoint → expect 200 with health response

**Automated:**
- `cd backend && pytest apps/test_hub/esigning/ -k gotenberg_health -v`

## Handoff notes
Promoted from discovery: `2026-04-22-gotenberg-health-endpoint-recon.md` (RNT-SEC-004). Information-disclosure vector; not a direct exploit but useful in a targeted attack.

### 2026-04-23 — rentals-pm

Duplicate of RNT-SEC-028, already shipped. `GotenbergHealthView.permission_classes = [IsAdmin]` confirmed live; 13 tests pass. Closing as duplicate.
