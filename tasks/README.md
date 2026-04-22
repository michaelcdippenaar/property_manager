# Klikk Rentals v1 — Launch Task Queue

File-based task queue for shipping **Klikk Rentals v1** to market.
Each task is a markdown file with frontmatter. Folder = status. Handoffs are `git mv` + commit.

## Scope — six streams

Launching a product isn't just shipping code. This queue runs six streams in parallel:

| Prefix | Stream | Owner agents |
|--------|--------|--------------|
| `RNT-NNN` / `RNT-SEC-NNN` / `RNT-QUAL-NNN` | **Rentals code** — hardening the 13 BUILT features; security/compliance fixes; quality & edge-cases | `rentals-implementer` → `rentals-reviewer` → `rentals-tester` |
| `GTM-NNN` | **Go-to-market** — target market, positioning, marketing content, launch campaigns, measurement | `gtm-marketer` → `rentals-reviewer` |
| `UX-NNN` | **UX & onboarding** — app ease-of-use audits, first-run flows, tutorial videos, in-app guides, help content | `ux-onboarding` → `rentals-reviewer` |
| `OPS-NNN` | **Ops & launch readiness** — CI/CD, observability, backups, secrets management, domain + email, legal pages, tier enforcement | `rentals-implementer` → `rentals-reviewer` → `rentals-tester` |
| `QA-NNN` | **QA & testing** — backend regression, FE E2E, mobile smoke matrix, RBAC matrix, a11y, perf, website QA, design-token audit | `rentals-tester` (or a qa-lead agent where we add one) → `rentals-reviewer` |
| `MIL-NNN` | **Milestones** — cross-stream launch gates (e.g. "first-client onboarding readiness") | `rentals-pm` |

All streams use the same folders, the same workflow, and the same commit discipline. The `rentals-pm` agent triages blockers and syncs to Asana across all streams.

**Substream prefixes** (e.g. `RNT-SEC-001`, `RNT-QUAL-001`) group related tasks for readability — they remain part of the `rentals` stream for routing/ownership.

**v1.0 scope (this project):**
- RNT: hardening pass on 13 BUILT rentals features (RNT-NNN), security/compliance fixes (RNT-SEC-NNN), quality + edge cases (RNT-QUAL-NNN)
- GTM: target market → positioning → launch content → campaign plan → measurement
- UX: audit all core flows → first-rental-cycle onboarding → training videos + guides
- OPS: CI/CD, Sentry, backups, domain/email/HTTPS, legal pages, secrets vault, uptime alerting, tier enforcement
- QA: backend regression baseline, E2E golden paths, mobile smoke matrix, RBAC matrix, a11y WCAG 2.1 AA, perf budget, website QA, design-token audit
- MIL: single launch gate (`MIL-001`) that blocks on all the above before first-client onboarding

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

Zero-padded, monotonic per prefix. Reserve the next free ID before creating a task.

- `RNT-NNN` — rentals code (hardening, feature work)
- `RNT-SEC-NNN` — rentals security/compliance substream
- `RNT-QUAL-NNN` — rentals quality & edge-case substream
- `GTM-NNN` — go-to-market
- `UX-NNN` — UX & onboarding
- `OPS-NNN` — ops & launch readiness
- `QA-NNN` — QA & testing
- `MIL-NNN` — cross-stream milestones / launch gates

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
