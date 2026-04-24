---
discovered_by: rentals-reviewer
discovered_during: OPS-025
discovered_at: 2026-04-24
priority_hint: P2
suggested_prefix: OPS
---

## What I found
Commit `3be21509` is titled "RNT-SEC-030: review → testing (approved)" but actually bundles three unrelated changes:
1. RNT-SEC-030 handoff (review → testing)
2. The entire OPS-025 deliverable (scripts/check_task_board_integrity.sh, CI, pre-commit, doc, task file move, 4 cleanup deletions)
3. An unrelated RNT-QUAL-053 move (backlog → in-progress)

The commit message mentions only RNT-SEC-030. OPS-025 never got its own `implement → review` commit — the task simply appeared in `tasks/review/` via this conflated commit.

## Why it matters
Git blame/bisect becomes unreliable. Task-board reviewers cannot isolate a single task's diff via `git show <sha>`. PM handoff protocol (`RNT-NNN: implement → review`) relies on one-task-per-commit convention. Ironically, OPS-025 itself exists to prevent board-state drift — it deserves a clean commit.

## Where I saw it
- `git show 3be21509` — 11 files touched across three task streams

## Suggested acceptance criteria (rough)
- [ ] Add a pre-commit or CI guard that warns when a single commit touches more than one `tasks/<state>/<ID>.md` handoff transition
- [ ] Or: document in `docs/ops/task-board-guard.md` that each implementer commit should correspond to exactly one task transition
- [ ] Revisit agent instructions (rentals-implementer, rentals-reviewer) to reinforce one-task-per-commit

## Why I didn't fix it in the current task
Fixing the commit would require history rewrite (unsafe, shared branch). The substantive OPS-025 deliverable is correct and working; the hygiene issue is a recurrence-prevention problem, not a rework problem.

## PM decision — 2026-04-24 — deferred (won't track as task)
History rewrite is off the table. The one-task-per-commit convention is already documented in `docs/ops/task-board-guard.md` as part of OPS-025. Promoting this as a separate task would only duplicate that doc guidance. Agent instructions already specify one-task-per-commit; the violation was a stash-cycle artifact during parallel agent work. No actionable code fix needed. Closing as informational.
