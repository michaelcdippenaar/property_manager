---
discovered_by: rentals-reviewer
discovered_during: RNT-023
discovered_at: 2026-04-25
priority_hint: P2
suggested_prefix: OPS
---

## What I found
The bulk of the RNT-023 implementation (~45 lines in LeasesView.vue and ~38 lines in
ESigningPanel.vue) was committed under the wrong commit message
`aa074dad RNT-024: implement → review (fix badge count scoping mismatch)`.
The RNT-023 commit `7bf5d2fe` only contains the new test file plus a
4-line `defineExpose({ initView })` shim. The code is correct and present
in HEAD — only the commit hygiene is wrong.

## Why it matters
- Audit trail: searching `git log` for RNT-023 will not surface the actual
  fix; reverting RNT-023 alone would not undo the change.
- RNT-024 (already merged to done) carries unrelated frontend changes that
  belong to RNT-023; if RNT-024 is ever reverted those changes go with it.
- Future bisects will land on the wrong ticket when narrowing flash bugs.

## Where I saw it
- `git show aa074dad --stat` lists `admin/src/views/leases/LeasesView.vue`
  and `admin/src/views/leases/ESigningPanel.vue` despite RNT-024 being a
  pure backend (maintenance badge counts) ticket.
- `git show 7bf5d2fe --stat` shows only LeasesView.vue (4 lines), the new
  test file, and the task file move.

## Suggested acceptance criteria (rough)
- [ ] Document the split in a follow-up note on RNT-023 done file so future
      git archaeology has a pointer.
- [ ] Add a workflow reminder for implementers to verify `git status` is
      clean and scoped to a single ticket before each `implement → review`
      commit.
- [ ] Consider a pre-commit hook that warns when staged files cross app
      boundaries (e.g. backend-only ticket touches admin/).

## Why I didn't fix it in the current task
RNT-024 has already shipped to done; rewriting history would force-push
across multiple already-approved tickets. Cleanest option is forward
documentation, not a retroactive split.
