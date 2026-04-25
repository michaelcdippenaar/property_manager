---
discovered_by: rentals-reviewer
discovered_during: RNT-AI-001
discovered_at: 2026-04-25
priority_hint: P3
suggested_prefix: RNT
---

## What I found
Only the "Add Property" button currently carries a `data-guide="..."` attribute. The AI guide store (admin/src/stores/aiGuide.ts) and backend `guide_tools.py` reference selectors for several other actions (e.g. add tenant, add lease, add maintenance request) that have no corresponding DOM marker, so any "I've highlighted X for you" reply pointing at those will silently no-op.

## Why it matters
RNT-AI-001 fixed the create_property repro but the same class of bug will recur the moment the guide tries to highlight any other primary action. AC #3 of RNT-AI-001 ("works across all major admin SPA buttons") is only partially satisfied.

## Where I saw it
- `admin/src/stores/aiGuide.ts` — selectors registered in MOCK_INTENTS / TOOL_ACTION_MAP
- `backend/apps/ai/guide_tools.py` — TOOL_ACTION_MAP entries with `elementSelector`
- Compare against `grep -rn 'data-guide=' admin/src` (currently 1 hit)

## Suggested acceptance criteria (rough)
- [ ] Audit every selector referenced in `aiGuide.ts` and `guide_tools.py`; for each, either add the matching `data-guide` attribute to the corresponding view or remove the selector.
- [ ] Add a unit test (or simple Vitest) that fails if any registered selector has no DOM target on a fresh app mount of the relevant route.

## Why I didn't fix it in the current task
Out of scope — RNT-AI-001 was filed against the create_property repro specifically, and expanding to a full selector audit would double the diff.
