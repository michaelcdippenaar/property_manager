---
id: RNT-SEC-038
stream: rentals
title: "Restrict AgentHealthCheckView to admin-only — strip infra details from non-admin response"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: testing
assigned_to: tester
depends_on: []
asana_gid: "1214231032547133"
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Lock down `GET /api/v1/maintenance/monitor/health/` so non-admin agents cannot enumerate backend infrastructure details (embedding model name, chat log path, MCP server paths, API key presence).

## Acceptance criteria
- [x] `AgentHealthCheckView` permission class changed to `IsAdmin` only, OR detail strings (paths, model names, API key boolean) stripped from response before returning to non-admin callers
- [x] Regression test: non-admin agent (estate_agent, agency_admin) receives 403 (or a redacted payload with no path/model fields)
- [x] Regression test: admin user receives full detail response

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

2026-04-23 (implementer): Changed `AgentHealthCheckView.permission_classes` from `[IsAuthenticated, IsAgentOrAdmin]` to `[IsAuthenticated, IsAdmin]` in `backend/apps/maintenance/monitor_views.py`. Also imported `IsAdmin` alongside the existing `IsAgentOrAdmin` import. Added 5 regression tests in `backend/apps/maintenance/tests/test_agent_health_check_rbac.py` — all pass. Tests cover: estate_agent 403, agency_admin 403, unauthenticated 401/403, admin 200 with checks list, admin response includes embedding model name in detail field.

2026-04-23 (reviewer): Review passed. Verified: (1) `IsAdmin` imported from `apps.accounts.permissions` and applied to `AgentHealthCheckView.permission_classes = [IsAuthenticated, IsAdmin]` at monitor_views.py:387 — minimal, targeted change matching pattern of RNT-SEC-019; (2) `IsAdmin` class exists at apps/accounts/permissions.py:9; (3) 5 regression tests in `test_agent_health_check_rbac.py` cover estate_agent 403, agency_admin 403, unauthenticated 401/403, admin 200 with checks list, and admin-only visibility of embedding model name in detail field — fixture-based with proper IO mocking (rag_collection_stats, get_embedding_function). Security & POPIA pass: no new endpoints, no PII or secrets logged, no raw SQL, stricter permission is a hardening change with no regression surface. Infra detail leak (RAG_EMBEDDING_MODEL, MAINTENANCE_CHAT_LOG, MCP paths, API key presence) now admin-only. Handing off to tester.
