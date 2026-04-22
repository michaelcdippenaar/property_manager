---
discovered_by: rentals-tester
discovered_during: RNT-001
discovered_at: 2026-04-22
priority_hint: P1
suggested_prefix: QA
---

## What I found
`esigning_native_signing_test` in `services/tremly-mcp/lib/tools/esigning.mjs` (line 160-163) calls `esigning/submissions/<id>/public-link/` with `{ submitter_id: ... }` but the backend `ESigningCreatePublicLinkView` (line 756-758 in `apps/esigning/views.py`) requires `{ signer_role: ... }` and returns HTTP 400 `"signer_role required"` when given `submitter_id`. The tool always fails at step `create_public_link`.

## Why it matters
The `esigning_native_signing_test` MCP E2E tool is unusable — it cannot complete any native signing round-trip test. Any task that relies on this tool as an acceptance gate will be blocked (as RNT-001 was).

## Where I saw it
- `services/tremly-mcp/lib/tools/esigning.mjs:160-162` — posts `{ submitter_id: submission.signers?.[0]?.id || 1 }` 
- `backend/apps/esigning/views.py:756-758` — expects `signer_role`, not `submitter_id`

## Suggested acceptance criteria (rough)
- [ ] `esigning_native_signing_test` updated to send `{ signer_role: submission.signers[0].role }` instead of `{ submitter_id: ... }`
- [ ] Tool passes all steps end-to-end against a local lease with a native signing template
- [ ] Also audit `esigning_public_link` standalone tool (line 74-76) which also only sends `submitter_id`

## Why I didn't fix it in the current task
Test runner — not permitted to edit code.
