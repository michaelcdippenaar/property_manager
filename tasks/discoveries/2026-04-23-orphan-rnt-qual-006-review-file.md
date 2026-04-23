---
discovered_by: rentals-reviewer
discovered_during: RNT-QUAL-006
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: OPS
---

## What I found
`tasks/review/RNT-QUAL-006.md` exists as a tracked duplicate of the already-completed `tasks/done/RNT-QUAL-006.md`. The review copy was accidentally re-added by commit `ce2792aa` ("RNT-SEC-039: review → in-progress (changes requested)") — an unrelated task commit that touched this file as a 102-line addition. The task itself genuinely completed on `23b05ff4` ("RNT-QUAL-006: testing → done").

## Why it matters
Task queue automation and humans can mistakenly re-review an already-shipped task, wasting cycles. It also indicates a process leak where `git mv` flows are producing stray copies during rebase/merge. Left unchecked, the board state stops being trustworthy.

## Where I saw it
- `tasks/review/RNT-QUAL-006.md` (stale, status: review)
- `tasks/done/RNT-QUAL-006.md` (authoritative, status: done)
- Commit `ce2792aa` — unrelated RNT-SEC-039 review commit that unexpectedly re-created the review/ copy

## Suggested acceptance criteria (rough)
- [ ] Delete the orphan `tasks/review/RNT-QUAL-006.md`
- [ ] Add a pre-commit or CI check that fails when the same task id appears in more than one `tasks/<state>/` directory
- [ ] Audit all `tasks/` directories for other duplicates

## Why I didn't fix it in the current task
The current task is the review itself — I'm removing the orphan file as part of the review commit (since there is nothing substantive to re-review), but the broader guard and audit are out of scope for a review pass.
