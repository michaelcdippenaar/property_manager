---
discovered_by: rentals-reviewer
discovered_during: OPS-015
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: OPS
---

## What I found
The `email-templates` CI job (`.github/workflows/ci.yml`) installs Node 22 but has no npm/npx cache configured. `npx mjml` re-downloads MJML on every run, adding ~10-20s network overhead per CI execution.

## Why it matters
Slows every PR's CI pipeline unnecessarily. As MJML download frequency increases (every push), cumulative cost in CI minutes and developer wait time compounds.

## Where I saw it
- `.github/workflows/ci.yml` — `email-templates` job, `Set up Node.js` step has no `cache:` key

## Suggested acceptance criteria (rough)
- [ ] Add `cache: 'npm'` (or `cache: 'npx'`) to the `actions/setup-node@v4` step in the `email-templates` job
- [ ] Alternatively: pin `mjml` as a dev dependency in a top-level `package.json` so `npm ci` caches it with the rest of the project

## Why I didn't fix it in the current task
Out of scope for OPS-015; purely an optimisation, not a correctness issue.
