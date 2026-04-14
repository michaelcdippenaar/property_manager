# Klikk DevOps Runbook

> AI-readable runbook for Claude (Haiku / Sonnet) in VS Code or Cursor.
> Run all `make` commands from the **repo root**: `make -f deploy/Makefile <target>`

---

## 1. Environment Overview

| Environment | Machine | Compose file | Django settings |
|-------------|---------|--------------|-----------------|
| **development** | Local Mac | `docker-compose.yml` | `config.settings.local` |
| **staging** | Ubuntu home-server `192.168.1.235` | `deploy/docker-compose.staging.yml` | `config.settings.staging` |
| **production** | ISP-hosted VM (TBD) | `deploy/docker-compose.prod.yml` | `config.settings.production` |

`DJANGO_SETTINGS_MODULE` is set in the compose file `environment:` block — never hardcoded.

---

## 2. Environment File Structure

### The two-file pattern (backend only)

The backend uses **two stacked env files** on every server:

```
backend/.env.staging      ← committed to git  — non-secret config (URLs, flags, service names)
backend/.env.secrets      ← server-only       — real passwords and API keys (gitignored)
```

Docker Compose loads both. Variables in `.env.secrets` win if there is any overlap:

```yaml
# docker-compose.staging.yml — backend service
env_file:
  - ../backend/.env.staging    # from git
  - ../backend/.env.secrets    # from server
```

The **Postgres** container only needs `POSTGRES_PASSWORD`, so it loads only:

```yaml
# docker-compose.staging.yml — db service
env_file:
  - ../backend/.env.secrets    # provides POSTGRES_PASSWORD directly
```

### Frontend apps (website / admin / agent-app)

Frontends only have **public** variables (`VITE_*`, `PUBLIC_*`), so they are safe to commit.
They each have committed files per environment and no `.env.secrets`:

```
admin/.env.development
admin/.env.staging
admin/.env.production

website/.env.development
website/.env.staging

agent-app/.env.development
agent-app/.env.staging
agent-app/.env.production
```

### Full file map

| File | Committed | Contains |
|------|-----------|----------|
| `backend/.env.development` | ✅ Yes | Dev config, no secrets |
| `backend/.env.staging` | ✅ Yes | Staging config, no secrets |
| `backend/.env.production` | ✅ Yes | Production config, no secrets |
| `backend/.env.secrets.example` | ✅ Yes | Template — lists every secret key, values blank |
| `backend/.env.secrets` | ❌ No (gitignored) | Real values — store in Bitwarden |
| `backend/.env` | ❌ No (gitignored) | Legacy catch-all — no longer used |
| `admin/.env.*` | ✅ Yes | Public Vite vars only |
| `website/.env.*` | ✅ Yes | Public Astro vars only |
| `agent-app/.env.*` | ✅ Yes | Public Quasar vars only |

---

## 3. Secrets Reference

### What goes in `backend/.env.secrets`

```bash
# Generate SECRET_KEY:
# python -c "from django.utils.crypto import get_random_string; print(get_random_string(50))"

SECRET_KEY=<50-char random string>
DB_PASSWORD=<postgres password>
POSTGRES_PASSWORD=<must match DB_PASSWORD — used by the Postgres container>
ANTHROPIC_API_KEY=<sk-ant-api03-...>
EMAIL_HOST_PASSWORD=<gmail app password>

# Optional
# TWILIO_ACCOUNT_SID=
# TWILIO_AUTH_TOKEN=
# TWILIO_SMS_FROM=
# BASIC_AUTH_USER=        # Caddy basic-auth (lock down staging from public)
# BASIC_AUTH_HASH=        # bcrypt hash — generate with command below
```

### Bitwarden storage convention

- **Staging secrets** → Secure note: `Klikk → Staging secrets`
- **Production secrets** → Secure note: `Klikk → Production secrets`

When setting up a new server, copy from Bitwarden → paste into `backend/.env.secrets`.

---

## 4. Domain Routing (Caddy)

All subdomains point to the server's public IP. Caddy terminates TLS and proxies by `Host:` header.

| Domain | Container | Purpose |
|--------|-----------|---------|
| `www.klikk.co.za` | `website_web:80` | Astro marketing site |
| `app.klikk.co.za` | `admin_web:80` | Vue 3 admin SPA (login / dashboard) |
| `register.klikk.co.za` | `admin_web:80` | Vue 3 admin SPA (register route) |
| `backend.klikk.co.za` | `backend:8000` | Django REST API + WebSocket |
| `mobile-agent.klikk.co.za` | `agent_app_web:80` | Quasar agent mobile web |

Caddy config: `deploy/Caddyfile`

Generate Caddy basic-auth hash:
```bash
docker run --rm caddy:2.8-alpine caddy hash-password --plaintext 'yourpassword'
```

---

## 5. Network Architecture

```
Internet → Caddy (ports 80 / 443)
              ├─ www.klikk.co.za           → website_web   [edge]
              ├─ app.klikk.co.za           → admin_web     [edge]
              ├─ register.klikk.co.za      → admin_web     [edge]
              ├─ backend.klikk.co.za       → backend       [edge]
              └─ mobile-agent.klikk.co.za  → agent_app_web [edge]

backend (also on internal network)
  ├─ → db:5432          PostgreSQL
  └─ → gotenberg:3000   PDF generation
```

- `internal` network — backend, db, gotenberg. Not reachable from Caddy or the internet.
- `edge` network — Caddy + all frontend containers + backend.

---

## 6. Backend Config Reference

### Django settings modules

| Module | When | Key differences |
|--------|------|-----------------|
| `config.settings.local` | dev | `DEBUG=True`, `CORS_ALLOW_ALL_ORIGINS=True` |
| `config.settings.staging` | staging | `DEBUG=False`, secure cookies, HTTPS headers |
| `config.settings.production` | production | staging + HSTS enabled |

### Backend environment variables

| Variable | Dev value | Staging/Prod value | Secret? |
|----------|-----------|--------------------|---------|
| `SECRET_KEY` | generate | generate | **Yes — `.env.secrets`** |
| `DEBUG` | `True` | `False` | No |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | `backend.klikk.co.za` | No |
| `DB_NAME` | `klikk_db` | `klikk_db` | No |
| `DB_USER` | `klikk_user` | `klikk_user` | No |
| `DB_PASSWORD` | `klikk_pass` | strong password | **Yes — `.env.secrets`** |
| `POSTGRES_PASSWORD` | same as DB_PASSWORD | same as DB_PASSWORD | **Yes — `.env.secrets`** |
| `DB_HOST` | `localhost` | `db` | No |
| `DB_PORT` | `5432` | `5432` | No |
| `GOTENBERG_URL` | `http://localhost:3000` | `http://gotenberg:3000` | No |
| `ANTHROPIC_API_KEY` | your key | your key | **Yes — `.env.secrets`** |
| `SIGNING_PUBLIC_APP_BASE_URL` | `http://localhost:5173` | `https://app.klikk.co.za` | No |
| `ESIGNING_WEBHOOK_PUBLIC_URL` | `http://localhost:8000` | `https://backend.klikk.co.za` | No |
| `EMAIL_BACKEND` | `console.EmailBackend` | `smtp.EmailBackend` | No |
| `EMAIL_HOST_PASSWORD` | — | gmail app password | **Yes — `.env.secrets`** |

---

## 7. Make Commands

```bash
# ── Development ────────────────────────────────────────────────────────────
make -f deploy/Makefile dev-up
make -f deploy/Makefile dev-down
make -f deploy/Makefile dev-logs

# ── Staging ────────────────────────────────────────────────────────────────
make -f deploy/Makefile staging-build       # build all images
make -f deploy/Makefile staging-up          # start all containers
make -f deploy/Makefile staging-down        # stop all containers
make -f deploy/Makefile staging-logs        # tail all logs
make -f deploy/Makefile staging-restart     # rebuild + restart

# ── Production ─────────────────────────────────────────────────────────────
make -f deploy/Makefile prod-build
make -f deploy/Makefile prod-up
make -f deploy/Makefile prod-down
make -f deploy/Makefile prod-restart

# ── Per-service image builds ───────────────────────────────────────────────
make -f deploy/Makefile website-build ENV=staging
make -f deploy/Makefile admin-build   ENV=staging
make -f deploy/Makefile agent-build   ENV=staging

# ── Django management (STACK=staging|production) ───────────────────────────
make -f deploy/Makefile backend-migrate         STACK=staging
make -f deploy/Makefile backend-createsuperuser STACK=staging
make -f deploy/Makefile backend-shell           STACK=staging
make -f deploy/Makefile backend-logs            STACK=staging

# ── Single-service control (STACK=staging|production, SERVICE=<name>) ─────
make -f deploy/Makefile ps      STACK=staging
make -f deploy/Makefile logs    STACK=staging SERVICE=caddy
make -f deploy/Makefile restart STACK=staging SERVICE=backend
```

---

## 8. First-Time Server Setup

```bash
# 1. SSH into the server
ssh mc@192.168.1.235          # staging
# or your production IP

# 2. Clone the repo
git clone git@github.com:michaelcdippenaar/property_manager.git ~/apps/property_manager
cd ~/apps/property_manager

# 3. Create .env.secrets from Bitwarden
#    Copy the "Klikk → Staging secrets" note and paste into:
nano backend/.env.secrets
# Must contain: SECRET_KEY, DB_PASSWORD, POSTGRES_PASSWORD, ANTHROPIC_API_KEY, EMAIL_HOST_PASSWORD

# 4. Build all Docker images
make -f deploy/Makefile staging-build        # or prod-build

# 5. Start all containers
make -f deploy/Makefile staging-up

# 6. Run database migrations
make -f deploy/Makefile backend-migrate STACK=staging

# 7. Create Django superuser
make -f deploy/Makefile backend-createsuperuser STACK=staging

# 8. Verify everything is healthy
make -f deploy/Makefile ps STACK=staging
```

---

## 9. Git Workflow

### Why `git pull origin main` shows no output

`git pull` only downloads commits the server does not have yet.
**"Already up to date"** is the correct, expected output when the server is already at the
latest commit. It is not an error — it means nothing to pull.

### How to check what the server actually has

```bash
# Where is the server right now?
git log --oneline -5

# What is on GitHub that the server does not have yet?
git fetch origin
git log HEAD..origin/main --oneline
# Empty output = server is up to date. Lines = commits waiting to be pulled.

# Check for any local modifications on the server (should always be clean)
git status
```

### The normal deploy loop (Mac → GitHub → server)

```
Mac                      GitHub                   Server (staging)
───                      ──────                   ────────────────
edit code
git add <files>
git commit -m "..."  →  git push origin main  →  git pull origin main
                                                  make -f deploy/Makefile staging-build
                                                  make -f deploy/Makefile staging-up
                                                  make -f deploy/Makefile backend-migrate STACK=staging
```

### The server must never have local edits

If `git status` shows modified files on the server, the pull will be blocked.
The server should be **read-only** — all edits happen on the Mac.

```bash
# If the server has accidental local changes, stash them:
git stash
git pull origin main

# Then inspect what was stashed (and discard if it was junk):
git stash show -p
git stash drop
```

### SSH into the staging server

```bash
ssh mc@192.168.1.235        # password: pass
cd ~/apps/property_manager
```

---

## 10. Deploying an Update

```bash
# 1. SSH into the server
ssh mc@192.168.1.235
cd ~/apps/property_manager

# 2. Check what is coming before pulling (optional but good practice)
git fetch origin
git log HEAD..origin/main --oneline

# 3. Pull
git pull origin main
# "Already up to date" → nothing to do. Lines of commits → continue below.

# 4. Rebuild changed images (Docker caches unchanged layers — fast)
make -f deploy/Makefile staging-build

# 5. Restart with new images
make -f deploy/Makefile staging-up

# 6. Apply any new database migrations
make -f deploy/Makefile backend-migrate STACK=staging

# 7. Confirm all containers are healthy
make -f deploy/Makefile ps STACK=staging
```

---

## 11. Security Notes

| Topic | Detail |
|-------|--------|
| TLS termination | Caddy handles it. Django does **not** do HTTP→HTTPS redirect (would double-redirect). |
| Proxy headers | `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` trusts Caddy's header. |
| HSTS | Enabled in `production.py` at 5 min (`300s`) — increase to `31536000` after confirming HTTPS works. |
| Cookies | `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` are `True` in staging and production. |
| Backend user | Container runs as non-root `appuser` (set in `backend/Dockerfile`). |
| Secrets | Never in git. Always in `backend/.env.secrets`. Backed up in Bitwarden. |
