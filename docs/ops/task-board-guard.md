# Task Board Integrity Guard

**Implemented by:** OPS-025  
**Script:** `scripts/check_task_board_integrity.sh`

## What it checks

The script validates four properties of the `tasks/` directory tree:

| Check | Severity | Description |
|-------|----------|-------------|
| Duplicate IDs | ERROR (fatal) | A task ID (e.g. `OPS-025`) must exist in exactly one state folder. |
| Orphan IDs | ERROR (fatal) | A file's `id:` frontmatter must match its filename stem. |
| Frontmatter schema | WARNING (non-fatal) | Required keys must be present: `id`, `stream`, `title`, `priority`, `effort`, `status`, `created`, `updated`. |
| DEC references | ERROR (fatal) | Any `DEC-NNN` value in the `depends_on:` YAML frontmatter field must resolve to a file in `tasks/done/` or `tasks/backlog/`. Prose or handoff notes mentioning `DEC-NNN` as examples are ignored — only the frontmatter block is scanned. |

Files in `tasks/done/` that use a date-slug naming convention (e.g. `2026-04-22-some-fix.md`) are silently skipped — they don't carry a structured task ID.

## How to run manually

```bash
bash scripts/check_task_board_integrity.sh
```

Exit code 0 = clean. Exit code 1 = one or more errors found.

## Where it runs automatically

- **Pre-commit hook** (`.pre-commit-config.yaml`): fires whenever any file under `tasks/` is staged.  
  Install once per machine: `pip install pre-commit && pre-commit install`
- **CI** (`.github/workflows/ci.yml`, job `task-board-guard`): runs on every pull request and push to `main`.

## How to resolve a duplicate ID

A duplicate arises when the same task ID exists in two (or more) `tasks/<state>/` folders simultaneously. This happens when:

- An agent runs `git mv` to advance a task but a stale copy remains behind (e.g. from a rebase or merge).
- A file is manually copied rather than moved.

**Fix:**

1. Identify which copy is authoritative — it's the one in the more advanced state folder (e.g. `testing/` beats `backlog/`).
2. Delete the stale copy with `git rm tasks/<stale-state>/<ID>.md`.
3. Commit: `git commit -m "<ID>: remove stale duplicate from <stale-state>/"`.
4. Re-run the script to confirm `Exit: 0`.

## How to resolve an orphan ID

An orphan occurs when a file's `id:` frontmatter does not match its filename. Fix by correcting the frontmatter `id:` field (or rename the file) so they agree.

## How to resolve a missing DEC reference

If `depends_on:` lists a `DEC-NNN` that doesn't exist as a file in `tasks/done/` or `tasks/backlog/`, either:

- Add the missing `DEC-NNN.md` file to `tasks/backlog/` (if the decision hasn't been made yet), or
- Remove the dangling reference if it was entered in error.

**Note on prose mentions:** The check reads only the YAML frontmatter block (delimited by the opening and closing `---`). A handoff note or description that mentions `DEC-NNN` as an example string is never flagged. Only entries in `depends_on:` are validated.
