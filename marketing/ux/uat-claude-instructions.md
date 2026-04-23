# UAT Findings Processing Instructions — Claude / Autopilot

**Related task:** UX-006 — First-tester UAT harness: session replay + scenario protocol
**Referenced documents:** `uat-protocol-v1.md`, `uat-mc-instructions.md`, `uat-runbook.md` (all produced by UX-006)
**Triggering condition:** A new `marketing/ux/uat-findings-<YYYY-MM-DD>.md` file is committed to the repo

---

## Overview

After each UAT session MC completes, he saves and commits a findings file at `marketing/ux/uat-findings-<date>.md`. Claude (operating as the rentals-pm or autopilot agent) monitors for these files and is responsible for converting every finding into a tracked, prioritised task — then reporting back to the UX-006 Asana task.

Claude does NOT wait for MC to triage findings manually. The moment the findings file appears, Claude processes it end-to-end.

---

## Step 1 — Detect and read the findings file

When a `marketing/ux/uat-findings-*.md` file is new or modified:

1. Read the full file.
2. Note the session date from the filename.
3. Extract every `## Finding UAT-<n>` block. Each block contains: scenario, screen/component, observation, Clarity timestamp, severity (H/M/L), and optional suggested fix.
4. Note the SUS score if MC recorded it at the top of the file.

---

## Step 2 — Severity-to-priority mapping

Map each finding to a task priority and stream using these rules:

| Condition | Priority | Stream |
|-----------|----------|--------|
| Tester failed the task entirely | P0 | `RNT-QUAL-NNN` |
| Rage clicks (Clarity shows 3+ rapid clicks on same element) | P0 | `RNT-QUAL-NNN` |
| Task required >2 attempts to complete | P1 | `RNT-QUAL-NNN` or `UX-NNN` |
| SUS score <68 overall | P1 — create one umbrella UX improvement task | `UX-NNN` |
| Tester hesitated >15s, verbally expressed confusion | P1 | `UX-NNN` |
| Minor verbal comment, cosmetic confusion | P2 | `UX-NNN` |
| Observer marked severity H | P0 or P1 (use task-failure rule above) |
| Observer marked severity M | P1 |
| Observer marked severity L | P2 |

When a finding clearly points to a code defect (broken button, wrong data shown, flow doesn't complete), use `RNT-QUAL-NNN`. When the finding is a design or copy confusion with no underlying bug, use `UX-NNN`.

---

## Step 3 — Author a task per finding

For each finding that warrants a new task (i.e., is not a duplicate of an existing open task):

1. Pick the next free ID in the relevant namespace by scanning `tasks/*/` for the highest existing number in that prefix.
2. Copy `tasks/_templates/task.md` to `tasks/backlog/<ID>.md`.
3. Fill in:
   - **title:** short, imperative — e.g. "Fix Save button label ambiguity on Add Property form"
   - **priority:** per mapping above
   - **effort:** S for cosmetic/copy changes, M for interaction redesigns, L for flow-level restructuring
   - **acceptance criteria:** written from the tester's point of view — "Tester can complete [scenario] without hesitation on [screen]"
   - **repro steps:** lifted verbatim from the finding block, including Clarity timestamp
   - **files likely touched:** best-effort inference from the screen/component name
   - **test plan:** "Run scenario [N] from `uat-protocol-v1.md` with a fresh tester or facilitator; confirm no hesitation on [screen]"
4. Mirror to Asana: call `create_tasks` with project GID `1214176966314177`, section Backlog GID `1214176854548795`. Use the task title as name. Paste the full markdown body as notes.
5. Capture the returned Asana GID, write it into the task file's `asana_gid:` frontmatter.
6. Commit: `<ID>: promoted from UAT findings <date> (Finding UAT-<n>)`

---

## Step 4 — Handle duplicates

Before creating a new task, search `tasks/backlog/`, `tasks/in-progress/`, and `tasks/review/` for existing tasks whose title or acceptance criteria overlap with the finding. If a match exists:

- Open the existing task file.
- Append a `## Notes from UAT <date> — Finding UAT-<n>` section with the new observation and Clarity timestamp.
- Update the task's `updated:` date in frontmatter.
- Commit: `<ID>: UAT reinforcement — Finding UAT-<n> adds evidence`
- Do NOT create a duplicate Asana task; instead call `update_tasks` on the existing GID to append the same note to the Asana task description.

---

## Step 5 — Post summary to UX-006

After all findings in the session file are processed:

1. Compose a session summary:

```
UAT session <date> — <N> findings processed

SUS score: <score> (<interpretation: Excellent/Good/OK/Poor/Awful>)

Tasks created:
- <ID>: <title> (P<n>)
- ...

Tasks updated (reinforced):
- <ID>: <title> (added Finding UAT-<n>)

Highest-priority items:
- <ID>: <title> — <one-line reason>
```

2. Post this summary as a comment on the UX-006 Asana task (GID `1214235754892103`) using the Asana MCP `create_task_comment` tool (or equivalent comment endpoint).

3. If any P0 tasks were created, also comment: "P0 issue raised — recommend blocking next tester outreach (Irma Knipe Properties) until resolved."

---

## Step 6 — Archive the findings file

After all tasks are created and the Asana summary is posted, move the findings file from `marketing/ux/uat-findings-<date>.md` to `marketing/ux/archive/uat-findings-<date>.md`. Commit: `UX-006: archive UAT findings <date> (<N> tasks promoted)`.

---

## Rules

- Never alter the findings file content — treat it as immutable source data.
- Never assign tasks to a specific implementer automatically — leave `assigned_to: null`. MC will assign during sprint planning.
- Never create a task for a finding marked "won't fix" or "by design" by MC (MC may annotate findings with these notes before committing).
- If the SUS score is missing from the findings file, do not infer it — note "SUS score: not recorded" in the Asana summary.
- Rage-click detection: if the Clarity timestamp column contains a note about rage clicks, treat it as confirmed. Claude does not access Clarity directly — rely on MC's observation notes.
