---
id: RNT-SEC-001
stream: rentals
title: "Rotate all production secrets and purge them from git history"
feature: ""
lifecycle_stage: null
priority: P0
effort: M
v1_phase: "1.0"
status: backlog
asana_gid: "1214177379577862"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Rotate every production credential that has ever been committed to the repo and purge the secrets from git history so the bare repo no longer leaks them.

## Acceptance criteria
- [ ] Inventory of every secret ever committed (scan with `gitleaks` / `trufflehog` across full history)
- [ ] Every exposed secret rotated at source (DB, JWT signing key, SECRET_KEY, VAULT_ENCRYPTION_SALT, email SMTP, Twilio, AWS, Gotenberg API key, any third-party API key, Asana PAT if committed)
- [ ] Secrets removed from history via `git filter-repo` or BFG Repo-Cleaner; force-pushed to origin; team re-clones
- [ ] `.env.secrets` and any `*.secrets` files in `.gitignore`; pre-commit hook blocking future leaks (gitleaks pre-commit)
- [ ] Old JWTs invalidated (rotate SIMPLE_JWT signing key → forces re-login)
- [ ] Document the rotation + purge in `docs/ops/secret-rotation-2026-04.md`

## Files likely touched
- `.gitignore`
- `.pre-commit-config.yaml` (add gitleaks)
- `backend/config/settings.py` (re-read new env vars)
- `deploy/*.yml` (updated secret references)
- `docs/ops/secret-rotation-2026-04.md` (new)

## Test plan
**Manual:**
- `gitleaks detect --source . --no-git --verbose` → 0 findings
- `gitleaks detect --source .` (full history scan) → 0 findings
- Deploy with rotated secrets; app boots; login still works post-rotation
- Old JWTs rejected

**Automated:**
- CI job runs `gitleaks detect` on every PR

## Handoff notes
