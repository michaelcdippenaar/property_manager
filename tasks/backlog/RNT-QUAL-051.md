---
id: RNT-QUAL-051
stream: rentals
title: "Fix health monitor endpoint: return 200 + overall/checks payload to admin users"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214246576345008"
created: 2026-04-24
updated: 2026-04-24
---

## Goal
The maintenance health monitor endpoint (`/api/v1/maintenance/monitor/health/`) currently returns 403 to admin users instead of the expected monitoring payload. Admin users must be permitted to call this endpoint and receive a response with `overall` and `checks` keys.

## Acceptance criteria
- [ ] `GET /api/v1/maintenance/monitor/health/` authenticated as an admin user returns HTTP 200
- [ ] Response body contains `overall` key and `checks` key
- [ ] `apps/test_hub/maintenance/integration/test_monitor.py::AgentHealthCheckTests` (all 3 tests) pass
- [ ] Permission check correctly gates non-admin callers (403 behaviour for non-admins remains)

## Files likely touched
- `backend/apps/maintenance/views.py` (health monitor view — permission class)
- `backend/apps/maintenance/urls.py` (if route is mismapped)
- `backend/apps/test_hub/maintenance/integration/test_monitor.py`

## Test plan
**Automated:**
- `cd backend && pytest apps/test_hub/maintenance/integration/test_monitor.py::AgentHealthCheckTests -v`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-24 — rentals-pm: Promoted from discovery `2026-04-23-test-hub-remaining-regressions-post-infra-fix.md`. One of four regression tasks split from that discovery. Three tests in this class are currently failing with 403.
