---
discovered_by: rentals-reviewer
discovered_during: GTM-012
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: OPS
---

## What I found
The GTM-012 implementation commit (`de59eea9`) bundles unrelated tracked-file churn alongside the scoped `marketing/sales/icp-matrix.md` edit: `.coverage`, `backend/.coverage`, `coverage.xml`, `admin/.env.production`, `admin/.env.staging`, `admin/src/views/auth/RegisterView.vue`, `admin/src/views/leases/ESigningPanel.vue`, `admin/src/views/properties/MandateSigningPanel.vue`, `admin/src/views/properties/PropertiesView.vue`, `backend/apps/tenant_portal/views.py`, `.claude/agents/README.md`, plus task-folder moves for GTM-013 and RNT-QUAL-010.

## Why it matters
- Coverage artefacts (`.coverage`, `coverage.xml`) and env files should almost certainly be gitignored, not committed. `admin/.env.production` / `admin/.env.staging` landing in a GTM docs commit is a red flag for accidental secret exposure.
- Mixing unrelated app-code edits into scoped task commits breaks the ability to revert or audit a single task cleanly.
- Cross-task noise (GTM-013, RNT-QUAL-010 moves) makes `git log` per-ticket meaningless.

## Where I saw it
- `git show de59eea9 --stat` — 16 files changed; only `marketing/sales/icp-matrix.md` and the `tasks/{backlog => review}/GTM-012.md` move are in scope.
- `.gitignore` likely missing entries for `.coverage`, `coverage.xml`, `admin/.env.*`, `backend/.coverage`.

## Suggested acceptance criteria (rough)
- [ ] Audit `.gitignore` and add `.coverage`, `coverage.xml`, `admin/.env.production`, `admin/.env.staging`, `backend/.coverage`
- [ ] Confirm no real secrets leaked in the env files already committed; rotate if so
- [ ] Agent guidance: implementers should `git add` explicit paths, not `git add -A`, to keep task commits scoped

## Why I didn't fix it in the current task
Out of scope for a sales-copy update; requires ops/security judgement and a clean-up commit of its own.
