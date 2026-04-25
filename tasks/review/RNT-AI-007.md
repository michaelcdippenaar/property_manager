---
id: RNT-AI-007
stream: rentals
title: "Admin-editable AI knowledge file for domain rules"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214278323284057"
created: 2026-04-25
updated: 2026-04-25
---

## Goal

Replace hardcoded AI domain knowledge in guide_views.py with an admin-editable markdown file so that domain rule changes can be applied without a code edit or deploy.

## Acceptance criteria

- [x] New file `content/ai/knowledge.md` — markdown document of domain rules, FAQs, and terminology. Initial seed content must cover at minimum:
  - "Tenants are created via lease creation — no standalone Add Tenant flow"
  - "Owner and Landlord are the same entity — use 'landlord' in the data model"
  - "Properties without an active lease are 'vacant'"
  - "Maintenance requests come from tenants and route to suppliers via the agent"
- [x] Backend loader at `backend/apps/ai/knowledge.py` reads `content/ai/knowledge.md`, caches the result with a 5-minute TTL, and exposes it as a plain string ready to inject into a system prompt.
- [x] `AIGuideView` injects the knowledge content into the system prompt on every request, under a clearly delimited section: `## Klikk Domain Rules\n{knowledge}`.
- [x] New admin UI view at `admin/src/views/settings/AIKnowledgeTab.vue` with a Markdown editor (reuse existing TipTap editor or simple textarea). Saves via `POST /api/v1/ai/knowledge/`.
- [x] The save endpoint enforces `IsAdmin` permission. Returns 200 on success and busts the loader cache immediately.
- [x] Every save logs an `AuditEvent` with the raw new content (or diff if available) under the existing audit framework.
- [x] pytest cases: load happy path, cache busting on save, 403 returned for non-admin, knowledge content actually appears in the system prompt string passed to Anthropic.
- [x] Unit test: with knowledge content containing "Tenants are created via lease creation", a simulated query "add tenant" must produce a response that mentions creating a lease, not just opening a list.

## Note

This task overlaps in motivation with RNT-AI-005 (full MCP tools / agent actions) but is deliberately narrower in scope — knowledge injection only, no action execution. This task should land first; RNT-AI-005 builds on top.

## Files likely touched

- `content/ai/knowledge.md` (new, seed content)
- `backend/apps/ai/knowledge.py` (new)
- `backend/apps/ai/guide_views.py` (inject knowledge into system prompt)
- `backend/apps/ai/knowledge_views.py` (new) or `backend/apps/ai/views.py` (add endpoint)
- `backend/apps/ai/urls.py`
- `backend/apps/ai/tests/test_knowledge.py` (new)
- `admin/src/views/settings/AIKnowledgeTab.vue` (new)
- `admin/src/views/auth/ProfileView.vue` (mount the new tab)
- `admin/src/api/ai.ts` (new save method)

## Test plan

**Manual:**
- In admin SPA, navigate to Settings → AI Knowledge tab.
- Edit a rule (e.g., change the "add tenant" explanation) and save.
- Open AI guide chat, type "add tenant" — confirm response reflects the updated knowledge within one request (cache busted on save).
- Log in as a non-admin user, hit `POST /api/v1/ai/knowledge/` directly — expect 403.

**Automated:**
- `cd backend && pytest apps/ai/tests/test_knowledge.py`

## Handoff notes

### 2026-04-25 — implementer

All acceptance criteria met. 28/28 tests pass (14 new + 14 existing guide regression).

**What was built:**

- `content/ai/knowledge.md` — seed with all four required domain rules plus lease lifecycle, payment, SA legal context, and role terminology sections.
- `backend/apps/ai/knowledge.py` — thread-safe loader with in-process cache (5-min TTL), `get_knowledge()`, `bust_cache()`, `save_knowledge()`. Path resolved relative to repo root. Missing file returns empty string with a warning log rather than raising.
- `backend/apps/ai/guide_views.py` — `_call_guide()` calls `get_knowledge()` and appends `## Klikk Domain Rules\n{knowledge}` to the system prompt when the file has content.
- `backend/apps/ai/knowledge_views.py` — `AIKnowledgeView` GET+POST at `/api/v1/ai/knowledge/`. IsAdmin guard. POST writes file, calls `bust_cache()`, logs `AuditEvent(action="ai.knowledge.updated")` with before/after snapshots. 512 KB payload cap.
- `backend/apps/ai/urls.py` — added `path("knowledge/", AIKnowledgeView.as_view(), name="ai-knowledge")`.
- `backend/apps/ai/tests/test_knowledge.py` — 14 tests covering: happy path load, missing file, cache TTL, bust, save, GET endpoint, POST endpoint, cache busting via endpoint, audit event creation, 403 non-admin, 401 unauth, 400 missing content, system-prompt injection, add-tenant prompt assertion.
- `admin/src/api/ai.ts` — `fetchKnowledge()` and `saveKnowledge()` API helpers.
- `admin/src/views/settings/AIKnowledgeTab.vue` — monospace textarea editor, loads on mount, save button with spinner and success/error feedback. Non-admin sees a read-only notice.
- `admin/src/views/auth/ProfileView.vue` — `<AIKnowledgeTab v-if="auth.user?.role === 'admin'" />` added after SecurityTab.

**Caveats for reviewer:**
- The cache is in-process (threading.Lock + module globals). In a multi-worker deployment (gunicorn with multiple processes), each worker maintains its own cache. The bust on save only affects the worker that received the save request; other workers will pick up the new content when their TTL expires (up to 5 min). For v1 with a single gunicorn worker this is fine. Multi-worker support would require moving the cache to Redis/Django cache framework.
- The admin UI uses a plain textarea rather than TipTap rich editor — the task allows "simple textarea" and this is sufficient for markdown editing.
