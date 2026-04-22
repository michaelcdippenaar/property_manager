---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-011
discovered_at: 2026-04-22
priority_hint: P1
suggested_prefix: RNT-SEC
---

## What I found

The `.gitleaks.toml` path allowlist entries `backend/\.env` and `admin/\.env` use unanchored/unterminated regexes that match not just the gitignored on-disk env files but also every committed env variant: `backend/.env.development`, `backend/.env.staging`, `backend/.env.production`, `admin/.env.development`, `admin/.env.staging`, `admin/.env.production`. These committed files are the ones most likely to accidentally receive a real secret in future changes.

## Why it matters

The intent is to exclude only the gitignored `backend/.env` and `backend/.env.secrets` (and `admin/.env`) which are never committed. Instead, the current regex silently suppresses gitleaks findings on all committed `.env.*` files. A future developer who accidentally writes a real key into `backend/.env.staging` (a committed file) would not see a CI or pre-commit alert.

## Where I saw it

- `.gitleaks.toml` lines 79–83 (path entries `'''backend/\.env'''` and `'''admin/\.env'''`)
- Confirmed by `git ls-files backend/.env*`: `backend/.env.development`, `.env.staging`, `.env.production`, `.env.secrets.example` are all tracked.

## Suggested acceptance criteria (rough)

- [ ] `backend/\.env` path entry anchored/terminated so it matches only `backend/.env` — e.g. `'''backend/\.env$'''` or `'''backend/\.env[^.]'''`
- [ ] `backend/\.env\.secrets` similarly anchored: `'''backend/\.env\.secrets$'''`
- [ ] `admin/\.env` anchored: `'''admin/\.env$'''`
- [ ] Verify that after anchoring, `gitleaks detect --source . --no-git` still exits 0 on a dev machine
- [ ] Verify that `backend/.env.development`, `backend/.env.staging`, `backend/.env.production`, `admin/.env.*` are NOT in the allowlist and are scanned normally

## Why I didn't fix it in the current task

Out of scope for the reviewer role; this is a new correctness/security gap found during review, not a pre-existing task requirement.
