---
id: RNT-AI-006
stream: rentals
title: "AI guide unaware of Owners/Landlords section"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214278063342425"
created: 2026-04-25
updated: 2026-04-25
---

## Goal

Patch the AI guide's action list, system prompt, and data-guide attributes so that owner/landlord queries resolve to the correct navigation action instead of a confused clarification question.

## Acceptance criteria

- [ ] Audit `backend/apps/ai/guide_tools.py` and the system prompt — list every navigation action and `data-guide` selector, and compare against actual SPA routes/sections.
- [ ] Add Owner/Landlord coverage: at minimum a `view_landlords` navigation action pointing to the verified route (check `admin/src/router/index.ts` for the exact path — likely `/landlords` or `/owners`).
- [ ] Add a `data-guide="add-landlord"` attribute (or equivalent) on the Add Landlord/Owner button in the admin SPA.
- [ ] Update the system prompt so the AI knows owners/landlords are a first-class entity, with a 1-line explanation: the human/entity who owns the property — called "owner" in casual SA usage but "landlord" in the data model.
- [ ] Add a unit test in `backend/apps/ai/tests/test_guide.py` asserting that "how do I create an owner", "create a landlord", and "add owner" all resolve to the landlord navigation action, not a clarification question.
- [ ] While auditing, file any other missing major SPA sections as a discovery in `tasks/discoveries/` — do not expand this task's scope.

## Repro

MC repro (2026-04-25):
> User: "how do I create an owner"
> AI: "I don't see a tool available to create an owner in this property management portal. The available functions are limited to managing properties, leases, tenants, maintenance, and payments. Could you clarify what you mean by 'owner'? ..."

## Files likely touched

- `backend/apps/ai/guide_tools.py`
- `backend/apps/ai/prompts/` (or wherever the guide system prompt lives)
- `admin/src/router/index.ts` (verify exact landlord/owner route path)
- `admin/src/views/landlords/` or `admin/src/views/owners/` (add `data-guide` attribute)
- `backend/apps/ai/tests/test_guide.py`

## Test plan

**Manual:**
- Open admin SPA, open AI guide chat, type "how do I create an owner" — expect navigation to the Landlords section, not a clarification question.
- Also test "add landlord" and "create owner" variants.

**Automated:**
- `cd backend && pytest apps/ai/tests/test_guide.py -k "owner or landlord"`

## Handoff notes

(Each agent appends a dated entry here on handoff. Do not edit prior entries.)
