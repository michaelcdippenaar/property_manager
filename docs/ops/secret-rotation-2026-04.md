# Secret Rotation — April 2026

**Status:** Partial (automated steps done; steps requiring production access require MC action)
**Initiated:** 2026-04-22
**Ticket:** RNT-SEC-001

---

## Scope

A gitleaks audit of the full git history revealed credentials committed to the repository.
This document records the inventory, the automated fixes already applied, and the manual steps
that require MC's production credentials to complete.

---

## 1. Secrets Inventory — What Was Committed

| Secret | Where committed | Risk level |
|--------|----------------|------------|
| `GOOGLE_MAPS_API_KEY=AIzaSyAKdTBybb8R0xC-NldeUsjgRve7kDs5RZY` | `backend/.env.{development,staging,production}`, `admin/.env.*` — multiple commits back to `b2ed3ab` | HIGH — live Maps billing key |
| `GOOGLE_OAUTH_CLIENT_ID=463351671420-...` | Same files + agent-app env files | MEDIUM — OAuth client ID is semi-public but still a credential |
| `VOLT_MCP=volt_owner_FslvHrwNvOjNU4RfCshcUUx0le6zRenxnu9CWJbPepM` | `backend/.env.staging` | HIGH — live Volt MCP owner API key |
| `VOLT_OWNER_API_KEY=volt_owner_FslvHrwNvOjNU4RfCshcUUx0le6zRenxnu9CWJbPepM` | `deploy/docker-compose.staging.yml` | HIGH — same key hardcoded in compose |
| `DB_PASSWORD=klikk_pass` | `backend/.env.development` — older commits (`c1d0e90`, `b2ed3ab`, etc.) | LOW — was a local dev password; production DB_PASSWORD lives in .env.secrets |
| Placeholder values in `.env.example` | Various | NONE — intentional placeholders |

**Not found in history:**
- Django `SECRET_KEY` (always in .env.secrets, never committed)
- `ANTHROPIC_API_KEY` (always in .env.secrets)
- `DB_PASSWORD` for staging/production (always in .env.secrets)
- `EMAIL_HOST_PASSWORD` (always in .env.secrets)
- Twilio, AWS credentials (never committed)
- Asana PAT (not committed)

---

## 2. Automated Fixes Applied (RNT-SEC-001)

The following changes have been committed:

### 2.1 Secrets removed from current working tree

All committed env files have been cleaned — real values replaced with comments pointing
to `.env.secrets`:

- `backend/.env.{development,staging,production}` — Google keys removed
- `admin/.env.{development,staging,production}` — Google keys removed
- `agent-app/.env.{development,staging,production}` — Google Client ID removed
- `backend/.env.staging` — `VOLT_MCP` line removed
- `deploy/docker-compose.staging.yml` — `VOLT_OWNER_API_KEY` hardcode removed

### 2.2 `.env.secrets.example` updated

`backend/.env.secrets.example` now lists all secrets that belong in `.env.secrets`:
`GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_MAPS_API_KEY`, `VOLT_MCP`, `VOLT_OWNER_API_KEY`.

### 2.3 `.gitignore` hardened

Added `*.secrets` glob and additional secret-file patterns.

### 2.4 Pre-commit hook added

`.pre-commit-config.yaml` added — gitleaks runs on every `git commit`, blocking any staged secret.

Activate on each developer machine:
```bash
pip install pre-commit
pre-commit install
```

### 2.5 `.gitleaks.toml` added

Allowlist configured for:
- Placeholder/example values
- CI test DB password (`klikk_pass` — only in GitHub Actions service container)
- Google OAuth Client IDs (public identifiers; not secrets per se)
- `volt_owner_…` string literals in code documentation

### 2.6 CI gitleaks job added

`.github/workflows/ci.yml` now runs `gitleaks/gitleaks-action@v2` on every PR and push to main,
scanning full history.

---

## 3. Manual Steps Required — MC Must Perform

The following steps require production access or external service credentials. They cannot be
performed autonomously.

### Step 1: Rotate Google Maps API key (HIGH — do immediately)

1. Go to [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials)
2. Find the key `AIzaSyAKdTBybb8R0xC-NldeUsjgRve7kDs5RZY`
3. Click **Regenerate** (or create a new key and restrict it to `backend.klikk.co.za`)
4. Update `backend/.env.secrets` on the staging server with the new key
5. Update `GOOGLE_MAPS_API_KEY` in the GitHub Actions repository secrets
6. Restart the backend container: `docker compose -f deploy/docker-compose.staging.yml restart backend`
7. Delete or restrict the old key in Google Cloud Console

**Restrict the key** to:
- Application restrictions: HTTP referrers → `*.klikk.co.za/*`
- API restrictions: Maps JavaScript API, Maps Geocoding API only

### Step 2: Review Google OAuth Client ID (MEDIUM)

The OAuth Client ID `463351671420-7hh3aln6nc6s5vi6ds9huka21cphp9h1.apps.googleusercontent.com`
is a *client ID* (not the client secret). Client IDs are intentionally public (they appear in
browser JavaScript). However:

1. Verify the associated **OAuth Client Secret** was never committed — it should be in `.env.secrets`
2. In Google Cloud Console → confirm the OAuth consent screen is configured correctly
3. Restrict authorized JavaScript origins to `https://app.klikk.co.za` and `https://backend.klikk.co.za`
4. If the client secret was ever exposed (check with MC), regenerate the client

### Step 3: Rotate Volt MCP Owner API key (HIGH — do immediately)

The key `volt_owner_FslvHrwNvOjNU4RfCshcUUx0le6zRenxnu9CWJbPepM` was committed.

1. SSH into staging server
2. Generate a new key:
   ```bash
   cd /opt/klikk
   docker compose -f deploy/docker-compose.staging.yml exec backend \
     python manage.py volt_create_owner_key
   ```
3. Update `VOLT_MCP` and `VOLT_OWNER_API_KEY` in `backend/.env.secrets`
4. Restart volt_mcp service:
   ```bash
   docker compose -f deploy/docker-compose.staging.yml restart volt_mcp
   ```
5. Update any Claude agent configs / `.mcp.json` that reference the old key

### Step 4: Purge secrets from git history (HIGH)

The secrets are still in git history even though the working tree is clean.
Run `git filter-repo` to rewrite history:

```bash
# Install: pip install git-filter-repo
# Run from repo root (make a backup first!)

git filter-repo --replace-text <(cat <<'EOF'
volt_owner_FslvHrwNvOjNU4RfCshcUUx0le6zRenxnu9CWJbPepM==>REDACTED_VOLT_KEY
AIzaSyAKdTBybb8R0xC-NldeUsjgRve7kDs5RZY==>REDACTED_GOOGLE_MAPS_KEY
EOF
) --force
```

Then force-push:
```bash
git push origin main --force
```

**After force-push:** every developer and CI runner must re-clone the repository.
The old remote tracking history is gone.

### Step 5: Rotate SIMPLE_JWT signing key (invalidates all existing JWTs)

1. Generate a new random value:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
2. Update `SIMPLE_JWT_SIGNING_KEY` in `backend/.env.secrets` (or ensure `SECRET_KEY` rotation
   covers it — check `backend/config/settings/base.py` for `SIGNING_KEY` config)
3. Restart backend container — all existing access tokens become invalid and users must re-login

### Step 6: Rotate Django SECRET_KEY (if key has been stable a long time)

1. Generate:
   ```bash
   python -c "from django.utils.crypto import get_random_string; print(get_random_string(50))"
   ```
2. Update `SECRET_KEY` in `backend/.env.secrets`
3. Restart backend — sessions and password-reset links are invalidated

---

## 4. Post-Rotation Verification

Run these after completing manual steps:

```bash
# 1. Full history scan — expect 0 findings (after git filter-repo)
gitleaks detect --source . --log-opts="--all" --verbose

# 2. Working-tree only scan
gitleaks detect --source . --no-git --verbose

# 3. Backend boots with new secrets
docker compose -f deploy/docker-compose.staging.yml up -d
curl -s https://backend.klikk.co.za/api/v1/health/ | jq .

# 4. Login flow works with new JWT signing key
# (visit https://app.klikk.co.za — should get login screen, old tokens rejected)
```

---

## 5. Ongoing Prevention

| Control | Status |
|---------|--------|
| `.gitignore` covers `*.secrets`, `.env.secrets`, `.env.local` | Done (RNT-SEC-001) |
| Pre-commit gitleaks hook | Done (RNT-SEC-001) — run `pre-commit install` on each dev machine |
| CI gitleaks on every PR | Done (RNT-SEC-001) |
| All secrets in `.env.secrets` (server-only) | Pattern established — verify on each new service |
| GitHub repository secret scanning alerts | Enable in GitHub → Settings → Security → Secret scanning |

---

*Last updated: 2026-04-22 by rentals-implementer (RNT-SEC-001)*
