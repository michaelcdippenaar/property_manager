---
id: RNT-AI-002
stream: rentals-ai
title: "AI guide auto mode — action-execution layer (create/update via allowlisted tools)"
feature: ""
lifecycle_stage: null
priority: P2
effort: L
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: [DEC-025]
asana_gid: "1214277871317046"
created: 2026-04-25
updated: 2026-04-25
---

## Goal
When AI guide mode is set to "auto", the guide can execute allowlisted CRUD operations end-to-end on behalf of the user (e.g. create a property, update a lease field) rather than only navigating or highlighting UI elements.

## Blocker

**Blocked on DEC-025.** MC must decide: (a) whether action execution is permitted at all, (b) audit trail requirements, and (c) whether each write requires a confirmation step. Do not begin implementation until DEC-025 is answered and closed.

## Acceptance criteria
*(to be refined after DEC-025 is answered — these assume Option B: confirmation-gated)*

- [ ] In auto mode, asking "Create new property for me with the name 18 Doctor Malan Road" causes the AI to display a confirmation card: "I'm about to create a property named '18 Doctor Malan Road' — confirm?" before any write is executed.
- [ ] On user confirmation the AI calls `POST /api/v1/properties/` with the correct payload and returns the newly created resource ID/link in the chat.
- [ ] On user rejection the AI does nothing and acknowledges cancellation.
- [ ] All AI-initiated mutations are tagged with a source field (e.g. `created_by: "ai_guide"`) stored on the resource or in an audit log.
- [ ] The allowlist of callable tools/endpoints is explicit and reviewed by MC before release — the AI cannot call delete or sensitive endpoints unless explicitly allowlisted.
- [ ] In non-auto mode the guide continues to navigate + highlight only (no writes).
- [ ] Unit and integration tests cover: happy path create, user rejection, out-of-allowlist attempt.

## Repro / motivation

MC set AI guide to "auto" and asked "Create new property for me with the name 18 Doctor Malan Road". The AI only navigated to the Add Property page. Expected: property created end-to-end in the chat window.

## Files likely touched
- `backend/apps/ai/views.py` (guide endpoint — add tool dispatch layer)
- `backend/apps/ai/tools/` (new directory: one module per allowlisted action, e.g. `create_property.py`)
- `backend/apps/ai/serializers.py` (action request/response schemas)
- `admin/src/components/AiGuide/ConfirmationCard.vue` (new confirmation UI component)
- `admin/src/composables/useAiGuide.ts` (handle `action_required` response type)
- `backend/apps/properties/models.py` (add `created_by_source` field if audit trail decided)

## Test plan
**Manual:**
- Set AI to auto → ask "Create new property with name Test Property 1" → confirm on card → verify property appears in property list.
- Set AI to auto → ask "Create new property" → reject on confirmation card → verify nothing created.
- Set AI to non-auto → ask same → verify only navigation, no confirmation card shown.

**Automated:**
- `cd backend && pytest apps/ai/tests/test_action_execution.py`
- Include a test asserting an out-of-allowlist tool name returns a 400/permission error.

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-25 — rentals-pm: Filed from MC's finding. L effort — action-execution layer is non-trivial. Hard-blocked on DEC-025 until MC answers the scope/audit/confirmation questions. Do not dispatch to implementer until DEC-025 is closed.
