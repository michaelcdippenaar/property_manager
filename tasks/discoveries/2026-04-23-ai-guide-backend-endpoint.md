---
discovered_by: rentals-implementer
discovered_during: RNT-020
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: RNT
---

## What I found

RNT-020 was scoped frontend-only (constraint: no backend changes during parallel sprint). The `AIGuide.vue` component currently uses an in-process mock intent mapper (`_mockIntentMapper` in `stores/aiGuide.ts`) instead of calling the real `/api/v1/ai/guide/` endpoint.

## Why it matters

The mock covers ~7 common intents with regex matching and has no persistence or telemetry. The `GuideInteraction` model, tool-use loop, role-scoped allowlist, and Anthropic API calls all still need to be built in Django before the widget can provide real AI responses.

## Where I saw it

- `admin/src/stores/aiGuide.ts` — `sendMessage()` method, mock section starting at "When backend ships, swap this for..."
- Task spec: `backend/apps/ai/guide_views.py`, `guide_tools.py`, `models.py` (GuideInteraction), `backend/config/urls.py`

## Suggested acceptance criteria (rough)

- [ ] `backend/apps/ai/guide_views.py` — POST `/api/v1/ai/guide/` accepts `{message, portal}`, calls Anthropic claude-3-5-haiku with tool-use, returns `{reply, action}` structured payload
- [ ] `backend/apps/ai/guide_tools.py` — allowlisted actions (create_property, list_leases, go_to_dashboard, view_maintenance, etc.) scoped by portal role
- [ ] `backend/apps/ai/models.py` — `GuideInteraction` model (user, portal, intent, action_taken, completed, created_at)
- [ ] `backend/config/settings/base.py` — `ANTHROPIC_API_KEY`, `ENABLE_AI_GUIDE` env vars
- [ ] `backend/config/urls.py` — wire `/api/v1/ai/guide/`
- [ ] Swap frontend mock: replace `_mockIntentMapper` call in `stores/aiGuide.ts` with `api.post('/ai/guide/', ...)` (one-line change, comment already in place)
- [ ] Unit tests: `backend/apps/ai/tests/test_guide.py`

## Why I didn't fix it in the current task

Frontend-only sprint constraint: "Do NOT modify backend/ — if you need a backend endpoint, add it to the task file as a follow-up and stub the frontend with a mock for now."
