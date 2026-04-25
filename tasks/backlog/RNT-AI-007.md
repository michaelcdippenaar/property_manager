---
id: RNT-AI-007
stream: rentals
title: "Admin-editable AI knowledge file for domain rules"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214278323284057"
created: 2026-04-25
updated: 2026-04-25
---

## Goal

Replace hardcoded AI domain knowledge in guide_views.py with an admin-editable markdown file so that domain rule changes can be applied without a code edit or deploy.

## Acceptance criteria

- [ ] New file `content/ai/knowledge.md` — markdown document of domain rules, FAQs, and terminology. Initial seed content must cover at minimum:
  - "Tenants are created via lease creation — no standalone Add Tenant flow"
  - "Owner and Landlord are the same entity — use 'landlord' in the data model"
  - "Properties without an active lease are 'vacant'"
  - "Maintenance requests come from tenants and route to suppliers via the agent"
- [ ] Backend loader at `backend/apps/ai/knowledge.py` reads `content/ai/knowledge.md`, caches the result with a 5-minute TTL, and exposes it as a plain string ready to inject into a system prompt.
- [ ] `AIGuideView` injects the knowledge content into the system prompt on every request, under a clearly delimited section: `## Klikk Domain Rules\n{knowledge}`.
- [ ] New admin UI view at `admin/src/views/settings/AIKnowledgeTab.vue` with a Markdown editor (reuse existing TipTap editor or simple textarea). Saves via `POST /api/v1/ai/knowledge/`.
- [ ] The save endpoint enforces `IsAdmin` permission. Returns 200 on success and busts the loader cache immediately.
- [ ] Every save logs an `AuditEvent` with the raw new content (or diff if available) under the existing audit framework.
- [ ] pytest cases: load happy path, cache busting on save, 403 returned for non-admin, knowledge content actually appears in the system prompt string passed to Anthropic.
- [ ] Unit test: with knowledge content containing "Tenants are created via lease creation", a simulated query "add tenant" must produce a response that mentions creating a lease, not just opening a list.

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

(Each agent appends a dated entry here on handoff. Do not edit prior entries.)
