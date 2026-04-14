# Klikk DevOps Runbook

> AI-readable runbook for Claude (Haiku / Sonnet) in VS Code or Cursor.
> Run all `make` commands from the **repo root**: `make -f deploy/Makefile <target>`
> Run all `docker compose` commands from `~/apps/property_manager` on the server.

---

## 1. Environment Overview

| Environment | Machine | IP | Compose file | Django settings |
|-------------|---------|-------|--------------|-----------------|
| **development** | Local Mac | — | `docker-compose.yml` | `config.settings.local` |
| **staging** | Ubuntu home-server | `192.168.1.235` | `deploy/docker-compose.staging.yml` | `config.settings.staging` |
| **production** | ISP-hosted VM | TBD | `deploy/docker-compose.prod.yml` | `config.settings.production` |

SSH into staging:
```bash
ssh mc@192.168.1.235    # password: pass
cd ~/apps/property_manager
```

---

## 2. Services and Containers

| Service name | Image | Purpose | Networks |
|---|---|---|---|
| `backend` | built from `backend/Dockerfile` | Django API via Daphne ASGI | internal + edge |
| `db` | `postgres:16.3` | PostgreSQL database | internal only |
| `gotenberg` | `gotenberg/gotenberg:8.14` | HTML → PDF generation | internal only |
| `website_web` | built from `website/Dockerfile` | Astro marketing site (nginx) | edge |
| `admin_web` | built from `admin/Dockerfile` | Vue 3 admin SPA (nginx) | edge |
| `agent_app_web` | built from `agent-app/Dockerfile` | Quasar agent mobile web (nginx) | edge |
| `caddy` | `caddy:2.8-alpine` | TLS reverse proxy, routes by domain | edge |

Networks:
- `internal` — backend ↔ db ↔ gotenberg. Not exposed to the internet.
- `edge` — Caddy ↔ all frontends ↔ backend.

---

## 3. Domain Routing

| Domain | Container | Purpose |
|--------|-----------|---------|
| `www.klikk.co.za` | `website_web:80` | Marketing site |
| `app.klikk.co.za` | `admin_web:80` | Admin SPA (login / dashboard) |
| `register.klikk.co.za` | `admin_web:80` | Admin SPA (register route) |
| `backend.klikk.co.za` | `backend:8000` | REST API + WebSocket |
| `mobile-agent.klikk.co.za` | `agent_app_web:80` | Agent mobile web |

Caddy config: `deploy/Caddyfile`

---

## 4. Environment File Structure

### The two-file pattern (backend)

```
backend/.env.staging    ← committed to git  — non-secret config (URLs, flags, ports)
backend/.env.secrets    ← server-only       — real passwords and API keys (gitignored)
```

Docker Compose stacks them. Variables in `.env.secrets` override `.env.staging`:

```yaml
# backend service in docker-compose.staging.yml
env_file:
  - ../backend/.env.staging   # from git — loaded first
  - ../backend/.env.secrets   # from server — wins on any overlap
```

The Postgres container only needs `POSTGRES_PASSWORD`:

```yaml
# db service
env_file:
  - ../backend/.env.secrets   # provides POSTGRES_PASSWORD
```

### Frontend files (safe to commit — public vars only)

```
admin/.env.development / .env.staging / .env.production
website/.env.development / .env.staging
agent-app/.env.development / .env.staging / .env.production
```

### Full file map

| File | Committed | Contains |
|------|-----------|----------|
| `backend/.env.development` | ✅ | Dev config, no secrets |
| `backend/.env.staging` | ✅ | Staging config, no secrets |
| `backend/.env.production` | ✅ | Production config, no secrets |
| `backend/.env.secrets.example` | ✅ | Template — keys listed, values blank |
| `backend/.env.secrets` | ❌ gitignored | Real secrets — store in Bitwarden |
| `backend/.env` | ❌ gitignored | Legacy — no longer used |
| `admin/.env.*` | ✅ | Public Vite vars |
| `website/.env.*` | ✅ | Public Astro vars |
| `agent-app/.env.*` | ✅ | Public Quasar vars |

---

## 5. Secrets

> ⚠️ **BEFORE GOING TO PRODUCTION — move secrets out of the repo:**
> Currently secrets live only on the server in `backend/.env.secrets` (gitignored).
> GitHub push protection will block any attempt to commit real API keys even to a private repo.
> Before launch, save the filled `.env.secrets` file in Bitwarden so you never lose it
> and can recreate any server in minutes. See Bitwarden convention below.

### What goes in `backend/.env.secrets`

```bash
# Generate SECRET_KEY:
# python -c "from django.utils.crypto import get_random_string; print(get_random_string(50))"

SECRET_KEY=<50-char random string>
DB_PASSWORD=<postgres password>
POSTGRES_PASSWORD=<must match DB_PASSWORD — used by the Postgres container itself>
ANTHROPIC_API_KEY=<sk-ant-api03-...>
EMAIL_HOST_PASSWORD=<gmail app password>

# Optional
# TWILIO_ACCOUNT_SID=
# TWILIO_AUTH_TOKEN=
# TWILIO_SMS_FROM=
# BASIC_AUTH_USER=     # Caddy basic-auth to lock down staging from public
# BASIC_AUTH_HASH=     # bcrypt hash — generate: docker run --rm caddy:2.8-alpine caddy hash-password --plaintext 'pw'
```

### Create the file on a new server

```bash
# 1. SSH in
ssh mc@192.168.1.235
cd ~/apps/property_manager

# 2. Create the secrets file (get values from Bitwarden → "Klikk → Staging secrets")
nano backend/.env.secrets

# 3. Verify it looks right
cat backend/.env.secrets
```

### Update a secret on the server

Use this when rotating an API key, changing a password, or adding a new secret variable.

```bash
# Step 1 — SSH in
ssh mc@192.168.1.235
cd ~/apps/property_manager

# Step 2 — Edit the secrets file
nano backend/.env.secrets
# Change or add the line you need, e.g.:
#   ANTHROPIC_API_KEY=sk-ant-api03-newkey...
# Save: Ctrl+O → Enter → Ctrl+X

# Step 3 — Verify the change looks right
cat backend/.env.secrets

# Step 4 — Restart the affected container to pick up the new value
# For most secrets (SECRET_KEY, ANTHROPIC_API_KEY, EMAIL_HOST_PASSWORD):
docker compose -f deploy/docker-compose.staging.yml up -d --force-recreate backend

# If DB_PASSWORD or POSTGRES_PASSWORD changed — restart both db and backend:
docker compose -f deploy/docker-compose.staging.yml up -d --force-recreate db backend

# Step 5 — Confirm the container got the new value
docker compose -f deploy/docker-compose.staging.yml exec backend env | grep ANTHROPIC
# (replace ANTHROPIC with whatever key you updated)

# Step 6 — Update Bitwarden with the new value
# Bitwarden → "Klikk → Staging secrets" → edit the note
```

> **Important:** If you change `DB_PASSWORD`, you must also change `POSTGRES_PASSWORD`
> to the same value, and restart both `db` and `backend`. Changing only one will break
> the database connection.

### Bitwarden convention

- Staging → Secure note: `Klikk → Staging secrets`
- Production → Secure note: `Klikk → Production secrets`

---

## 6. Backend Config Reference

### Django settings modules

| Module | When | Key differences |
|--------|------|-----------------|
| `config.settings.local` | dev | `DEBUG=True`, `CORS_ALLOW_ALL_ORIGINS=True` |
| `config.settings.staging` | staging | `DEBUG=False`, secure cookies, HTTPS proxy headers |
| `config.settings.production` | production | staging + HSTS |

### All backend environment variables

| Variable | Dev | Staging/Prod | Secret? |
|----------|-----|-------------|---------|
| `SECRET_KEY` | generate | generate | **Yes — `.env.secrets`** |
| `DEBUG` | `True` | `False` | No |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | `backend.klikk.co.za` | No |
| `DB_NAME` | `klikk_db` | `klikk_db` | No |
| `DB_USER` | `klikk_user` | `klikk_user` | No |
| `DB_PASSWORD` | `klikk_pass` | strong password | **Yes — `.env.secrets`** |
| `POSTGRES_PASSWORD` | same as DB_PASSWORD | same as DB_PASSWORD | **Yes — `.env.secrets`** |
| `DB_HOST` | `localhost` | `db` (Docker service name) | No |
| `DB_PORT` | `5432` | `5432` | No |
| `GOTENBERG_URL` | `http://localhost:3000` | `http://gotenberg:3000` | No |
| `ANTHROPIC_API_KEY` | your key | your key | **Yes — `.env.secrets`** |
| `SIGNING_PUBLIC_APP_BASE_URL` | `http://localhost:5173` | `https://app.klikk.co.za` | No |
| `ESIGNING_WEBHOOK_PUBLIC_URL` | `http://localhost:8000` | `https://backend.klikk.co.za` | No |
| `EMAIL_BACKEND` | `console.EmailBackend` | `smtp.EmailBackend` | No |
| `EMAIL_HOST` | — | `smtp.gmail.com` | No |
| `EMAIL_PORT` | — | `587` | No |
| `EMAIL_USE_TLS` | — | `True` | No |
| `EMAIL_HOST_USER` | — | `michael.c.dippenaar@gmail.com` | No |
| `EMAIL_HOST_PASSWORD` | — | gmail app password | **Yes — `.env.secrets`** |
| `DEFAULT_FROM_EMAIL` | — | `Klikk <michael.c.dippenaar@gmail.com>` | No |
| `GOOGLE_OAUTH_CLIENT_ID` | shared | shared | No |
| `GOOGLE_MAPS_API_KEY` | shared | shared | No |

---

## 7. Git Workflow

### SSH into the server and go to the repo

```bash
ssh mc@192.168.1.235       # password: pass
cd ~/apps/property_manager  # ALWAYS run git and make from here
```

### Why `git pull` sometimes shows nothing

`git pull origin main` only downloads commits the server does not already have.
**"Already up to date"** means the server is current — this is correct, not broken.

### Check the server's state before pulling

```bash
# See the last 5 commits on the server
git log --oneline -5

# See what GitHub has that the server does not
git fetch origin
git log HEAD..origin/main --oneline
# Empty = server is current. Each line = one unpulled commit.

# Check for unexpected local changes (should always be clean on server)
git status
```

### Pull and verify

```bash
git pull origin main
# Output will list changed files. "Already up to date" means nothing changed.
```

### The server must never have local edits

All code changes happen on the Mac, committed, pushed to GitHub, then pulled on the server.
If `git status` shows modified files, the pull will be blocked.

```bash
# Fix accidental local edits on the server:
git stash                  # save the changes aside
git pull origin main       # now the pull will work
git stash show -p          # inspect what was stashed
git stash drop             # discard it (it was not supposed to be there)
```

### The full deploy loop

```
Mac                          GitHub                  Server (192.168.1.235)
───                          ──────                  ──────────────────────
1. Edit code
2. git add <files>
3. git commit -m "..."  →  git push origin main  →  cd ~/apps/property_manager
                                                     git pull origin main
                                                     [rebuild — see Section 8]
```

---

## 8. When to Rebuild — Decision Table

Use this table to decide exactly what to run after a `git pull`.

| What changed | Action needed |
|---|---|
| Python code only (no new deps) | Rebuild + restart `backend` only |
| `requirements.txt` changed | Rebuild + restart `backend` only (Docker re-runs pip install) |
| `backend/Dockerfile` changed | Rebuild + restart `backend` only |
| New Django migration files | Rebuild `backend` → restart → run migrate |
| Frontend code (Vue / Astro / Quasar) | Rebuild + restart that frontend service only |
| `backend/.env.staging` changed | Restart `backend` (no rebuild needed — env is injected at start) |
| `backend/.env.secrets` changed on server | Restart `backend` and `db` (no rebuild needed) |
| `deploy/Caddyfile` changed | Restart `caddy` only |
| `deploy/docker-compose.staging.yml` changed | `docker compose up -d` — Docker detects and recreates only changed services |
| Everything / unsure | Rebuild all → restart all → migrate |

---

## 9. Docker Commands — Full Reference

All commands run from `~/apps/property_manager` on the server.

### Check status

```bash
# See all running containers, their status and health
docker compose -f deploy/docker-compose.staging.yml ps

# Expected healthy output:
# deploy-backend-1      Up X minutes (healthy)
# deploy-db-1           Up X minutes (healthy)
# deploy-caddy-1        Up X minutes
# deploy-gotenberg-1    Up X minutes
# deploy-website_web-1  Up X minutes
# deploy-admin_web-1    Up X minutes
# deploy-agent_app_web-1 Up X minutes
```

### Start and stop

```bash
# Start all containers (recreates only changed ones)
docker compose -f deploy/docker-compose.staging.yml up -d

# Stop all containers (keeps data volumes intact)
docker compose -f deploy/docker-compose.staging.yml down

# Stop AND delete volumes (WARNING: deletes the database)
docker compose -f deploy/docker-compose.staging.yml down -v
```

### Rebuild — all services

```bash
# Rebuild all images using Docker cache (fast — only changed layers rebuild)
docker compose -f deploy/docker-compose.staging.yml build

# Rebuild all images ignoring cache (slow — full rebuild from scratch)
# Use this when: dependencies changed but Docker cache is not picking it up
docker compose -f deploy/docker-compose.staging.yml build --no-cache

# Rebuild then start
docker compose -f deploy/docker-compose.staging.yml build && \
docker compose -f deploy/docker-compose.staging.yml up -d
```

### Rebuild — single service

```bash
# Rebuild only the backend (fastest when only Python code changed)
docker compose -f deploy/docker-compose.staging.yml build backend
docker compose -f deploy/docker-compose.staging.yml up -d backend

# Rebuild only the admin SPA
docker compose -f deploy/docker-compose.staging.yml build admin_web
docker compose -f deploy/docker-compose.staging.yml up -d admin_web

# Rebuild only the marketing website
docker compose -f deploy/docker-compose.staging.yml build website_web
docker compose -f deploy/docker-compose.staging.yml up -d website_web

# Rebuild only the agent app
docker compose -f deploy/docker-compose.staging.yml build agent_app_web
docker compose -f deploy/docker-compose.staging.yml up -d agent_app_web
```

### Restart — without rebuilding

```bash
# Use when only .env files changed — no code changes, no rebuild needed

# Restart backend (picks up new env vars)
docker compose -f deploy/docker-compose.staging.yml up -d --force-recreate backend

# Restart caddy (picks up Caddyfile changes)
docker compose -f deploy/docker-compose.staging.yml up -d --force-recreate caddy

# Restart db (picks up new POSTGRES_PASSWORD from .env.secrets)
docker compose -f deploy/docker-compose.staging.yml up -d --force-recreate db

# Restart everything without rebuilding
docker compose -f deploy/docker-compose.staging.yml up -d --force-recreate
```

### View logs

```bash
# All services — last 50 lines, then follow
docker compose -f deploy/docker-compose.staging.yml logs -f --tail=50

# Single service
docker compose -f deploy/docker-compose.staging.yml logs -f backend
docker compose -f deploy/docker-compose.staging.yml logs -f caddy
docker compose -f deploy/docker-compose.staging.yml logs -f db

# Last 100 lines without following
docker compose -f deploy/docker-compose.staging.yml logs --tail=100 backend
```

### Run Django management commands

```bash
# Apply database migrations (always run after a deploy that adds migrations)
docker compose -f deploy/docker-compose.staging.yml exec backend python manage.py migrate

# Create a superuser (first time only)
docker compose -f deploy/docker-compose.staging.yml exec backend python manage.py createsuperuser

# Open a Django shell
docker compose -f deploy/docker-compose.staging.yml exec backend python manage.py shell

# Check for migration issues without applying
docker compose -f deploy/docker-compose.staging.yml exec backend python manage.py migrate --check
```

### Verify environment variables inside a container

```bash
# Check what env vars the backend container actually sees
docker compose -f deploy/docker-compose.staging.yml exec backend env | sort

# Check specific vars
docker compose -f deploy/docker-compose.staging.yml exec backend env | grep DB_
docker compose -f deploy/docker-compose.staging.yml exec backend env | grep SECRET
docker compose -f deploy/docker-compose.staging.yml exec backend env | grep DJANGO
```

### Free up disk space

```bash
# Remove unused images (safe — only removes images not used by running containers)
docker image prune -f

# Remove unused images, build cache, stopped containers, unused networks
docker system prune -f

# See disk usage
docker system df
```

---

## 10. First-Time Server Setup

Run these steps in order, top to bottom. Do not skip.

```bash
# Step 1 — SSH into the server
ssh mc@192.168.1.235

# Step 2 — Clone the repo
git clone git@github.com:michaelcdippenaar/property_manager.git ~/apps/property_manager
cd ~/apps/property_manager

# Step 3 — Create the secrets file
# Get the values from Bitwarden → "Klikk → Staging secrets"
nano backend/.env.secrets
# Paste and fill in:
#   SECRET_KEY=
#   DB_PASSWORD=
#   POSTGRES_PASSWORD=   ← must match DB_PASSWORD
#   ANTHROPIC_API_KEY=
#   EMAIL_HOST_PASSWORD=

# Step 4 — Verify the secrets file was saved
cat backend/.env.secrets

# Step 5 — Build all Docker images (takes 5–15 min first time)
docker compose -f deploy/docker-compose.staging.yml build

# Step 6 — Start all containers
docker compose -f deploy/docker-compose.staging.yml up -d

# Step 7 — Confirm all 7 containers are running
docker compose -f deploy/docker-compose.staging.yml ps
# All should show "Up" — backend may show "health: starting" for ~30s, then "healthy"

# Step 8 — Run database migrations
docker compose -f deploy/docker-compose.staging.yml exec backend python manage.py migrate

# Step 9 — Create a Django superuser
docker compose -f deploy/docker-compose.staging.yml exec backend python manage.py createsuperuser

# Step 10 — Check logs for any errors
docker compose -f deploy/docker-compose.staging.yml logs --tail=50 backend
docker compose -f deploy/docker-compose.staging.yml logs --tail=20 caddy
```

---

## 11. Standard Deploy (Updating a Running Server)

Run these steps after pushing new code to GitHub.

```bash
# Step 1 — SSH in and go to the repo
ssh mc@192.168.1.235
cd ~/apps/property_manager

# Step 2 — Check what is incoming
git fetch origin
git log HEAD..origin/main --oneline
# If empty → nothing to deploy. If lines appear → continue.

# Step 3 — Pull
git pull origin main
# Read the output — it lists every changed file. Use Section 8 to decide what to rebuild.

# Step 4 — Rebuild changed images
# For most deploys (Python code / frontend changes):
docker compose -f deploy/docker-compose.staging.yml build

# Step 5 — Restart containers with new images
docker compose -f deploy/docker-compose.staging.yml up -d

# Step 6 — Run migrations if any migration files were in the pull output
docker compose -f deploy/docker-compose.staging.yml exec backend python manage.py migrate

# Step 7 — Confirm healthy
docker compose -f deploy/docker-compose.staging.yml ps
docker compose -f deploy/docker-compose.staging.yml logs --tail=30 backend
```

---

## 12. Troubleshooting

### Container exits immediately / won't start

```bash
# See why it crashed
docker compose -f deploy/docker-compose.staging.yml logs backend

# Common causes:
# - Missing env var → check .env.secrets exists and has all required keys
# - Port already in use → check with: ss -tlnp | grep 8000
# - Bad Dockerfile syntax → check: docker compose -f deploy/docker-compose.staging.yml config
```

### Backend stuck on "health: starting"

```bash
# Check if daphne actually started
docker compose -f deploy/docker-compose.staging.yml logs backend | tail -20

# Test the health endpoint directly
docker compose -f deploy/docker-compose.staging.yml exec backend \
  wget -qO- http://localhost:8000/api/v1/health/

# If Django errors: usually a missing env var or failed migration
docker compose -f deploy/docker-compose.staging.yml exec backend \
  python manage.py check
```

### Migration fails

```bash
# See the full error
docker compose -f deploy/docker-compose.staging.yml exec backend \
  python manage.py migrate

# Common causes:
# - Data integrity issue (duplicate unique values in DB)
# - DB connection refused → check DB_HOST=db and DB_PORT=5432 in container env:
docker compose -f deploy/docker-compose.staging.yml exec backend env | grep DB_
```

### `git pull` is blocked by local changes on server

```bash
git status          # see what is modified
git stash           # stash the changes
git pull origin main
git stash drop      # discard the stash (edits should not be on the server)
```

### `.env.secrets` is missing

```bash
# Error looks like: "required variable X is missing"
# Fix:
nano backend/.env.secrets
# Paste from Bitwarden → "Klikk → Staging secrets"
docker compose -f deploy/docker-compose.staging.yml up -d
```

### Docker build fails with "no space left on device"

```bash
docker system prune -f      # remove unused images and build cache
docker system df            # check how much space is freed
```

### Caddy not serving HTTPS / certificate errors

```bash
docker compose -f deploy/docker-compose.staging.yml logs caddy | tail -30
# Check that port 80 and 443 are open in your router/firewall
# Caddy auto-renews via Let's Encrypt — needs port 80 for ACME challenge
```

---

## 13. Make Command Reference

Run from the **repo root on the Mac** (or the server after `cd ~/apps/property_manager`).

```bash
# ── Staging ────────────────────────────────────────────────────────────────
make -f deploy/Makefile staging-build       # build all images
make -f deploy/Makefile staging-up          # start / recreate all containers
make -f deploy/Makefile staging-down        # stop all containers
make -f deploy/Makefile staging-logs        # tail all logs
make -f deploy/Makefile staging-restart     # rebuild + restart everything

# ── Production ─────────────────────────────────────────────────────────────
make -f deploy/Makefile prod-build
make -f deploy/Makefile prod-up
make -f deploy/Makefile prod-down
make -f deploy/Makefile prod-restart

# ── Django management ──────────────────────────────────────────────────────
make -f deploy/Makefile backend-migrate         STACK=staging
make -f deploy/Makefile backend-createsuperuser STACK=staging
make -f deploy/Makefile backend-shell           STACK=staging
make -f deploy/Makefile backend-logs            STACK=staging

# ── Single-service control ─────────────────────────────────────────────────
make -f deploy/Makefile ps      STACK=staging
make -f deploy/Makefile logs    STACK=staging SERVICE=caddy
make -f deploy/Makefile restart STACK=staging SERVICE=backend
```

---

## 14. Security Notes

| Topic | Detail |
|-------|--------|
| TLS | Caddy handles TLS. Django does NOT redirect HTTP→HTTPS (avoids double-redirect). |
| Proxy headers | `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` — Django trusts Caddy. |
| HSTS | `production.py` sets 5 min (`300s`). Increase to `31536000` after confirming HTTPS on all subdomains. |
| Cookies | `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` are `True` in staging and production. |
| Container user | Backend runs as non-root `appuser` (defined in `backend/Dockerfile`). |
| Secrets | Never in git. Always in `backend/.env.secrets`. Backed up in Bitwarden. |
| DB access | Postgres is on `internal` network only — not reachable from outside Docker. |
