---
discovered_by: rentals-reviewer
discovered_during: QA-017
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: QA
---

## What I found
`services/tremly-mcp/PLAN.md:153` still documents `esigning_public_link` with the old `{id: number, submitter_id: number}` contract. The code itself was updated in QA-017, but the plan doc is stale.

## Why it matters
Low-impact doc drift. If someone reads PLAN.md to understand the tool surface they'll see the wrong schema and may try to call it with `submitter_id`, which will now fail schema validation.

## Where I saw it
- `services/tremly-mcp/PLAN.md:153`

## Suggested acceptance criteria (rough)
- [ ] Update PLAN.md row for `esigning_public_link` to `{id: number, signer_role: string}`
- [ ] Scan PLAN.md for any other stale esigning contract references

## Why I didn't fix it in the current task
Doc-only; out of QA-017 scope (which is limited to the MCP tool code behaviour). Trivial follow-up.
