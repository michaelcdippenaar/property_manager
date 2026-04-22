---
id: RNT-SEC-001
stream: rentals
title: "Rotate all production secrets and purge them from git history"
feature: ""
lifecycle_stage: null
priority: P0
effort: M
v1_phase: "1.0"
status: review
asana_gid: "1214177379577862"
assigned_to: reviewer
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Rotate every production credential that has ever been committed to the repo and purge the secrets from git history so the bare repo no longer leaks them.

## Acceptance criteria
- [x] Inventory of every secret ever committed (scan with `gitleaks` / `trufflehog` across full history)
- [ ] Every exposed secret rotated at source (DB, JWT signing key, SECRET_KEY, VAULT_ENCRYPTION_SALT, email SMTP, Twilio, AWS, Gotenberg API key, any third-party API key, Asana PAT if committed) — **BLOCKED: requires MC to perform in production (see Handoff notes)**
- [ ] Secrets removed from history via `git filter-repo` or BFG Repo-Cleaner; force-pushed to origin; team re-clones — **BLOCKED: requires MC (see Handoff notes)**
- [x] `.env.secrets` and any `*.secrets` files in `.gitignore`; pre-commit hook blocking future leaks (gitleaks pre-commit)
- [ ] Old JWTs invalidated (rotate SIMPLE_JWT signing key → forces re-login) — **BLOCKED: requires MC to rotate SECRET_KEY in .env.secrets on server**
- [x] Document the rotation + purge in `docs/ops/secret-rotation-2026-04.md`

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

### 2026-04-22 — rentals-implementer

**What was done (autonomous):**

Secret inventory scanned via manual git log analysis (gitleaks was not installed; used grep patterns across all commits). Full inventory is in `docs/ops/secret-rotation-2026-04.md`.

**Secrets found committed:**
1. `GOOGLE_MAPS_API_KEY=AIzaSyAKdTBybb8R0xC-NldeUsjgRve7kDs5RZY` — in `backend/.env.{development,staging,production}` and `admin/.env.*` across ~10 commits back to `b2ed3ab`
2. `GOOGLE_OAUTH_CLIENT_ID=463351671420-...` — same files plus agent-app env files
3. `VOLT_MCP=volt_owner_FslvHrwNvOjNU4RfCshcUUx0le6zRenxnu9CWJbPepM` — in `backend/.env.staging`
4. `VOLT_OWNER_API_KEY=volt_owner_FslvHrwNvOjNU4RfCshcUUx0le6zRenxnu9CWJbPepM` — hardcoded in `deploy/docker-compose.staging.yml`
5. `DB_PASSWORD=klikk_pass` — in `backend/.env.development` in older commits (local dev only, not a production credential)

**Not found:** Django SECRET_KEY, ANTHROPIC_API_KEY, EMAIL_HOST_PASSWORD, Twilio, AWS, Asana PAT — all correctly kept in .env.secrets.

**Code changes applied:**
- Removed all real Google API keys from all committed `.env.*` files (replaced with comment pointing to `.env.secrets`)
- Removed `VOLT_MCP` from `backend/.env.staging`
- Replaced `VOLT_OWNER_API_KEY: volt_owner_...` in `deploy/docker-compose.staging.yml` with a comment
- Updated `backend/.env.secrets.example` to include all four keys that should now live there
- Updated `.gitignore` to cover `*.secrets` glob and additional patterns
- Added `.pre-commit-config.yaml` with gitleaks + pre-commit-hooks
- Added `.gitleaks.toml` with appropriate allowlist (CI test DB password, placeholder values, public OAuth client IDs)
- Added gitleaks CI job to `.github/workflows/ci.yml` (runs on every PR, full history scan)
- Wrote `docs/ops/secret-rotation-2026-04.md` with full runbook

**Steps MC must complete manually (before this task can be marked done):**

1. **Rotate Google Maps API key** in Google Cloud Console — see Runbook Step 1
2. **Review Google OAuth client** — verify client secret was never exposed — see Runbook Step 2
3. **Rotate Volt MCP owner key** on staging server — see Runbook Step 3
4. **Purge git history** with `git filter-repo --replace-text` then `git push --force` — see Runbook Step 4
5. **Rotate SIMPLE_JWT signing key** (forces all users to re-login) — see Runbook Step 5
6. **Run `pre-commit install`** on local dev machine
7. **Enable GitHub Secret Scanning** in repo Settings → Security

The runbook at `docs/ops/secret-rotation-2026-04.md` has exact commands for each step.

**Caveats for reviewer:**
- The `DB_PASSWORD=klikk_pass` in CI (`.github/workflows/ci.yml`) is intentional — it's a throwaway GitHub Actions postgres service container, not connected to production. The gitleaks allowlist permits it.
- Google OAuth Client IDs are intentionally public (they appear in browser JS). They are in the allowlist. The associated OAuth *Client Secret* must stay in `.env.secrets`.
- After MC runs `git filter-repo` + force-push, all local clones will need `git fetch --all && git reset --hard origin/main`.
