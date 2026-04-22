# Klikk Rentals v1 — Launch Task Queue

File-based task queue for shipping **Klikk Rentals v1** to market.
Each task is a markdown file with frontmatter. Folder = status. Handoffs are `git mv` + commit.

## Scope — three streams

Launching a product isn't just shipping code. This queue runs three streams in parallel:

| Prefix | Stream | Owner agents |
|--------|--------|--------------|
| `RNT-NNN` | **Rentals code** — hardening the 13 BUILT features for market | `rentals-implementer` → `rentals-reviewer` → `rentals-tester` |
| `GTM-NNN` | **Go-to-market** — target market, positioning, marketing content, launch campaigns | `gtm-marketer` → `rentals-reviewer` |
| `UX-NNN` | **UX & onboarding** — app ease-of-use audits, first-run flows, tutorial videos, in-app guides, help content | `ux-onboarding` → `rentals-reviewer` |

All three streams use the same folders, the same workflow, and the same commit discipline. The `rentals-pm` agent triages blockers and syncs to Asana across all three.

**v1.0 scope (this project):**
- RNT: hardening pass on 13 BUILT rentals features
- GTM: target market → positioning → launch content → campaign plan
- UX: audit all core flows → first-rental-cycle onboarding → training videos + guides

**v2 (not in scope here):** 7 PLANNED features — tenant screening, vacancy advertising, notice management, inspections (incoming + outgoing), deposit management, deposit refund.

## Folders = status

```
backlog/       Unclaimed, ready to pick up
in-progress/   Claimed by an implementing agent
review/        Awaiting review
testing/       Awaiting test / validation
blocked/       Needs PM attention (see Handoff notes for reason)
done/          Completed, kept for audit
```

A task's **folder IS its status.** The `status:` frontmatter must match the folder — agents update both together.

## Workflow

```
backlog → in-progress → review → testing → done
                ↑          │         │
                └──────────┴─────────┘
                  sent back with notes

  any → blocked (PM triages)
```

1. **Implementer** (one of `rentals-implementer` / `gtm-marketer` / `ux-onboarding`) picks oldest task from `backlog/` by priority → `git mv` to `in-progress/` → does the work → `git mv` to `review/` → commits `<ID>: implement → review`.
2. **Reviewer** (`rentals-reviewer`) reads diff + acceptance criteria → pass (`testing/`) or send back (`in-progress/`).
3. **Tester** (`rentals-tester`) runs the `## Test plan` → `done/` (pass) or `blocked/` (fail). For GTM and UX tasks, the "test" is typically an approval check against acceptance criteria rather than pytest — the tester still runs the task through and signs off.
4. **PM** (`rentals-pm`) triages `blocked/`, writes new tasks, syncs to Asana.

**Commit on every handoff.** Format:
`<ID>: <from> → <to> (<one-line summary>)`

## Task IDs

- `RNT-NNN` — zero-padded, monotonic
- `GTM-NNN` — zero-padded, monotonic
- `UX-NNN` — zero-padded, monotonic

Reserve the next free ID (per prefix) when creating a new task.

## Asana sync

Each task has an `asana_gid` field linking to its Asana counterpart in the **Klikk Rentals v1** project. The `rentals-pm` agent keeps Asana in sync with the filesystem (one-way: markdown → Asana on status changes).

## Subagents

Six Claude Code subagents live in `.claude/agents/`:

- `rentals-implementer` — writes code for `RNT-NNN`
- `rentals-reviewer` — reviews all streams (code, GTM, UX)
- `rentals-tester` — runs test plans / validation
- `rentals-pm` — PM, triage, Asana sync, new task authoring
- `gtm-marketer` — works `GTM-NNN`, authors marketing content in `content/`
- `ux-onboarding` — works `UX-NNN`, authors UX audits + onboarding content in `content/onboarding/`

Invoke with `Agent(subagent_type="<name>", prompt="Work task tasks/backlog/<ID>.md")`.
Run multiple tasks in parallel by issuing multiple `Agent` calls in one message.

## Templates

See `_templates/task.md` for the task file schema.
