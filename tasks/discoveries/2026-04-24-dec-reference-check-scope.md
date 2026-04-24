---
discovered_by: rentals-reviewer
discovered_during: OPS-025
discovered_at: 2026-04-24
priority_hint: P2
suggested_prefix: OPS
---

## What I found
`scripts/check_task_board_integrity.sh` runs its DEC-reference validity check by grepping `DEC-[0-9]+` across the entire task file, including prose handoff notes. This means writing a review/handoff note that mentions a hypothetical or example DEC ID (e.g. "I inserted a bogus DEC-9999 to test the guard") will make the script fail on the very file describing the guard.

## Why it matters
False positives on narrative text. A reviewer writing "if you insert DEC-9999 as a test..." trips the guard. The AC says only `depends_on:` entries should be checked — the current implementation is broader than that.

## Where I saw it
- `scripts/check_task_board_integrity.sh:201` — `grep -oE 'DEC-[0-9]+' "$filepath"` scans the whole file, not just frontmatter.
- OPS-025 AC #4: "`depends_on:` list contains DEC-NNN entries" — implementation is broader than spec.

## Suggested acceptance criteria (rough)
- [ ] Restrict DEC reference scanning to the `depends_on:` frontmatter line (or the frontmatter block only)
- [ ] Re-run on current tree; verify no regression in catching actually dangling depends_on values

## Why I didn't fix it in the current task
OPS-025 is in testing handoff; expanding scope now would push review back through another round. Behaviour is "stricter than spec" not "wrong", and easy to work around in prose. Better as its own small task.
