# Discoveries inbox

When an agent finds something worth fixing that is **out of scope** for the task they're working on, they drop a markdown file here instead of expanding their current task.

## Rules for discovering agents

- **One discovery = one file.** Filename: `YYYY-MM-DD-short-slug.md` (e.g. `2026-04-22-owner-dashboard-cache-leak.md`).
- Use the template at `../_templates/discovery.md`.
- **Do NOT assign a real task ID** (`RNT-NNN`, `OPS-NNN`, etc.). IDs and Asana mirroring are the PM's job.
- Reference the discovery file in your current task's `## Handoff notes` so the reviewer and PM see it.
- Commit the discovery along with your handoff commit.

## Rules for the PM

- Process the inbox periodically (daily at minimum).
- For each discovery:
  1. Decide: promote, merge into an existing task, defer (move to `done/` with a "won't fix" note in that folder), or kill (delete).
  2. If promoting: pick the next free ID in the suggested prefix, copy `_templates/task.md` into `tasks/backlog/<ID>.md`, fill in acceptance criteria using the discovery's notes, mirror to Asana, write `asana_gid` back, delete the discovery file.
  3. Commit `<ID>: promoted from discovery <slug>`.

## When NOT to use this inbox

- **In-scope sub-issues**: if you found a bug in the exact thing you were fixing, just fix it in the current task and note it in Handoff. Don't split it out.
- **Current task is unworkable**: if the premise of the task is wrong (wrong file, wrong approach, missing dependency), move the task to `blocked/` with a Handoff note — don't create a new discovery for "this task is broken."
- **Trivial cleanup** (<5 min to fix inline): just fix it. If you're afraid to touch it because the diff is already big, that's the signal to use the inbox.

## Example discovery filename set

```
2026-04-22-owner-dashboard-cache-not-invalidated-on-rent.md
2026-04-22-cors-allows-wildcard-in-staging.md
2026-04-23-tenant-onboarding-email-missing-plaintext-fallback.md
```
