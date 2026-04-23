---
id: RNT-SEC-038
stream: rentals
title: "Restrict AgentHealthCheckView to admin-only — strip infra details from non-admin response"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214231032547133"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Lock down `GET /api/v1/maintenance/monitor/health/` so non-admin agents cannot enumerate backend infrastructure details (embedding model name, chat log path, MCP server paths, API key presence).

## Acceptance criteria
- [ ] `AgentHealthCheckView` permission class changed to `IsAdmin` only, OR detail strings (paths, model names, API key boolean) stripped from response before returning to non-admin callers
- [ ] Regression test: non-admin agent (estate_agent, agency_admin) receives 403 (or a redacted payload with no path/model fields)
- [ ] Regression test: admin user receives full detail response

## Files likely touched
- `backend/apps/maintenance/monitor_views.py` (line 371 — `AgentHealthCheckView`)
- `backend/apps/maintenance/tests/` (new regression tests)

## Test plan
**Manual:**
- Authenticate as `estate_agent` → `GET /api/v1/maintenance/monitor/health/` — expect 403 or redacted payload
- Authenticate as `admin` → same endpoint — expect full payload

**Automated:**
- `cd backend && pytest apps/maintenance/tests/ -v`

## Handoff notes
2026-04-23: Promoted from discovery `2026-04-23-agent-health-check-infra-leak.md` (found during RNT-SEC-019). Same class as the Gotenberg health-check leak fixed in RNT-SEC-019 — separate view in `apps/maintenance`. Response leaks `settings.RAG_EMBEDDING_MODEL`, `settings.MAINTENANCE_CHAT_LOG`, MCP server file paths, and API key presence to any `IsAgentOrAdmin` user.
