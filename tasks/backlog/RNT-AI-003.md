---
id: RNT-AI-003
stream: rentals-ai
title: "AI guide endpoint returns 500 on retry — exception not captured"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214277801373363"
created: 2026-04-25
updated: 2026-04-25
---

## Goal
The `POST /api/v1/ai/guide/` endpoint never returns a 500 to the client; all exceptions are caught, logged with a structured stack trace, and return a graceful 200/error payload or a well-formed 4xx/5xx with a user-friendly message.

## Acceptance criteria
- [ ] Reproduce the 500 via the exact sequence below; confirm a structured exception log entry appears in the backend logs (exception type, message, stack trace, request body).
- [ ] The endpoint wraps its main handler body in a try/except that catches all unhandled exceptions, logs them via Django's structured logger, and returns a 200 with `{ "error": true, "message": "..." }` rather than an unhandled 500.
- [ ] Sentry (or equivalent) receives an event for the caught exception so it can be monitored in production.
- [ ] The repro sequence (three consecutive identical/similar POSTs) no longer results in a 500 after the fix.
- [ ] Unit test added that mocks the failure path and asserts the endpoint returns a non-500 status with an `error` key in the JSON body.

## Repro steps
1. Open admin SPA → AI chat widget.
2. Send "Create a new property".
3. Send "Create new property for me with the name 18 Doctor Malan Road".
4. Wait for response.
5. Press send again on the same or similar message (retry).
6. Observe 500 error in the UI: "Sorry, I hit an error: Request failed with status code 500."

Backend context: `POST /api/v1/ai/guide/` returned 200 twice in a row, then 500 on the third request.

## Files likely touched
- `backend/apps/ai/views.py` (guide endpoint handler — add try/except + structured logging)
- `backend/apps/ai/tests/test_guide_view.py` (new unit test for failure path)
- `backend/settings/base.py` or `logging.py` (ensure structured logger is configured for `apps.ai`)

## Test plan
**Manual:**
- Repro steps above; confirm 500 no longer returned.
- Check Django logs for structured exception entry.

**Automated:**
- `cd backend && pytest apps/ai/tests/test_guide_view.py -k "test_guide_500_handled"`

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-25 — rentals-pm: Filed from MC's direct repro. P1 because 500 is user-visible and reproducible in dev. Need to capture the actual exception first before patching.
