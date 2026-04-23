---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-019
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-SEC
---

## What I found
`AgentHealthCheckView` at `GET /api/v1/maintenance/monitor/health/` is gated by `IsAgentOrAdmin` (any agent variant). Its response leaks infrastructure internals: embedding model name (`settings.RAG_EMBEDDING_MODEL`), chat log filesystem path, API key configuration boolean, RAG chunk counts, and MCP server file paths.

## Why it matters
Same class of issue that RNT-SEC-019 fixed for Gotenberg: authenticated non-admin agents (including agency_admin / estate_agent across tenancies) can enumerate backend infrastructure details useful for targeted attacks. Not a direct exploit but violates least-privilege and is reconnaissance fuel.

## Where I saw it
- `backend/apps/maintenance/monitor_views.py:371` — `AgentHealthCheckView`, `permission_classes = [IsAuthenticated, IsAgentOrAdmin]`
- Response details include: `settings.RAG_EMBEDDING_MODEL`, `settings.MAINTENANCE_CHAT_LOG`, MCP server file path, API key presence.

## Suggested acceptance criteria (rough)
- [ ] Restrict `AgentHealthCheckView` to `IsAdmin` only, OR strip detail strings (paths, model names) from the response before returning to non-admin agents.
- [ ] Regression test: non-admin agent receives 403 (or receives redacted payload).
- [ ] Regression test: admin receives full detail.

## Why I didn't fix it in the current task
Out of scope — RNT-SEC-019 explicitly targets `GotenbergHealthView` in `apps/esigning`. This is a separate view in `apps/maintenance` that deserves its own ticket and test.
