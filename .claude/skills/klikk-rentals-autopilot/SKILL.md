---
name: klikk-rentals-autopilot
description: >
  Drive the Klikk Rentals v1 task queue autonomously. Load this skill whenever MC says
  "work the backlog", "run the pipeline", "auto-run tasks", "keep the queue moving",
  "run autopilot", "chew through the backlog", "overnight run", or any variant of
  "make progress on Klikk v1 without me micromanaging." This is the orchestrator skill
  for the top-level Claude Code session — it decides what to dispatch next, launches
  subagents (rentals-implementer, rentals-reviewer, rentals-tester, rentals-pm,
  gtm-marketer, ux-onboarding) in safe parallel batches, and stops when nothing is
  actionable. Also trigger on "status of the pipeline", "what's the queue doing",
  "morning summary", or when MC opens a fresh session in this repo — the autopilot's
  first action is always a status scan. Use this skill for any phrase that implies
  "move tasks forward without me choosing one manually." Even a terse "go" in this
  repo should trigger it.
---

# Klikk Rentals v1 — Autopilot

You are orchestrating the file-based task queue at `tasks/` for the Klikk Rentals v1 launch. Your job is to **keep tasks moving** with minimal MC input, while respecting safety rules that prevent merge conflicts, scope creep, and wasted work.

## The loop

Run this loop. Stop only when nothing is actionable — do not ask MC what to do next mid-loop.

### 1. Status scan (always start here)

```bash
for d in tasks/backlog tasks/in-progress tasks/review tasks/testing tasks/blocked tasks/done tasks/discoveries; do
  echo "$d: $(ls "$d" 2>/dev/null | grep -c '\.md$')"
done
```

If this is the first action of a new session, also run:
```bash
git log --since="24 hours ago" --oneline
```
and produce a one-paragraph **morning summary** before proceeding: what moved overnight, what's blocked, what decisions are still open.

### 2. Process queues in this order

Priority is **right-to-left** — finish late-stage work before starting new work. A task already in `testing/` is 90% of the way to done; a task in `backlog/` is 0%.

1. **`blocked/`** — invoke `rentals-pm` to triage each. Skip items blocked on an open `DEC-NNN` (they stay blocked until MC answers in Asana).
2. **`testing/`** — invoke `rentals-tester` on the oldest item.
3. **`review/`** — invoke `rentals-reviewer` on the oldest item.
4. **`in-progress/`** — check `updated:` frontmatter; if > 2 hrs stale, append a note and move back to `backlog/` for re-pickup.
5. **`discoveries/`** — if non-empty, invoke `rentals-pm` to promote/merge/defer.
6. **`backlog/`** — pick next tasks for implementer dispatch (see selection rules below).

### 3. Backlog selection rules

A task is **eligible** if:
- Every `depends_on:` task is in `tasks/done/`
- It is not blocked on an open `DEC-NNN`

Sort eligible tasks by:
1. Priority: P0 > P1 > P2
2. Effort: S > M > L (prefer quick wins to build momentum and free up reviewer capacity)
3. Stream variety: prefer spreading across streams (don't stack 3 OPS tasks in parallel if an RNT + GTM are waiting)

### 4. Parallel dispatch

**Cap:** 3 implementers + 1 reviewer + 1 tester in flight at any moment.

**File-overlap check before launching parallel implementers:** read each candidate's `## Files likely touched` list. If any two tasks share a path (or a parent dir both would likely modify), launch them sequentially, not in parallel. Otherwise, send all implementer dispatches in **one message with multiple `Agent` tool calls** so they run concurrently.

Dispatch prompt to each:
```
Work task tasks/backlog/<ID>.md
```

The subagent handles the `git mv`, the work, the commit, and the handoff. You do not commit anything directly — autopilot's one job that touches the repo is reading status. All writes go through subagents.

### 5. Between ticks

After each dispatch round completes:
- Emit a one-line status: `Tick N: 3 implementers launched (RNT-SEC-001, OPS-001, GTM-007). 1 in review. 0 blocked on DEC.`
- Loop back to step 1.

### 6. Stop condition

Stop when:
- `backlog/` has zero eligible tasks (all remaining are blocked on deps or DECs), AND
- `review/`, `testing/`, `in-progress/`, `blocked/`, `discoveries/` are all empty, OR contain only items waiting on MC.

Emit a final summary: tasks moved to `done/` this session, tasks still blocked on MC, open `DEC-NNN` list, recommended next MC action.

## Safety rails

- **Never edit task files directly.** Subagents own the frontmatter and handoff notes.
- **Never commit.** Every commit comes from a subagent after its handoff.
- **Never launch > 3 implementers.** Context + git contention grows non-linearly.
- **Never fan out on file overlap.** Better to run serially than lose work to merge conflicts.
- **Never push to a remote.** Local commits only; MC pushes manually when ready.
- **Never mark a DEC-NNN answered.** Only MC answers decisions (via Asana comment → PM sync).
- **Pause and ask MC** only if: every task in the backlog is blocked on decisions, AND the decisions have been open > 48 hrs. Otherwise, keep looping silently.

## Autonomy dials

MC can override at the start of a session:
- `max_implementers: N` — default 3, range 1–5
- `stop_on_first_blocked: true` — stop the loop if any task hits `blocked/`. Default off.
- `auto_promote_discoveries: false` — require manual review before PM promotes. Default on.
- `asana_sync: end_of_session` — don't sync every tick. Default: every tick.

If MC doesn't override, defaults apply.

## When to bail out of the loop entirely

- Merge conflict detected in `git status` → stop, report, let MC resolve.
- A subagent crashes or returns an error you can't interpret → stop, surface the raw output.
- `CLAUDE.md`, `tasks/README.md`, or `.claude/agents/*.md` have uncommitted changes → stop (someone is mid-edit).
- More than 5 consecutive ticks produced zero state change → stop (you're spinning).

## First-tick behaviour in a fresh session

1. Run status scan + morning summary.
2. Read `.claude/projects/klikk-rentals-v1/README.md` once to refresh deploy-recommendation context.
3. Announce plan: "Autopilot on. Queue state: X backlog / Y in-flight / Z blocked. Starting tick 1."
4. Enter the loop.
