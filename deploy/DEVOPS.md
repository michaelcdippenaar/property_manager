# Klikk DevOps Runbook

> **AI-readable runbook.** Structured so Cursor / Claude Code can read it and execute deployments. Use `make -f deploy/Makefile <target>` from the repo root.

---

## Environment Overview

| Environment | Where | Server | Compose file | Django settings |
|-------------|-------|--------|--------------|-----------------|
| **development** | Local Mac | — | `docker-compose.yml` | `config.settings.local` |
| **staging** | Ubuntu VM (home server) | On-prem | `deploy/docker-compose.staging.yml` | `config.settings.staging` |
| **production** | ISP-hosted VM | Remote | `deploy/docker-compose.prod.yml` | `config.settings.production` |

`DJANGO_SETTINGS_MODULE` is set in each compose file's `environment` block — never hardcoded in `asgi.py`.

---

## Domain Routing (Caddy)

Caddy terminates TLS and routes by `Host:` header. All subdomains point to the server's public IP.

| Domain | Container | Purpose |
|--------|-----------|---------|
| `www.klikk.co.za` | `website_web:80` | Astro marketing site |
| `app.klikk.co.za` | `admin_web:80` | Vue 3 admin SPA (login/dashboard) |
| `register.klikk.co.za` | `admin_web:80` | Vue 3 admin SPA (register route) |
| `backend.klikk.co.za` | `backend:8000` | Django REST API + WebSocket |
| `mobile-agent.klikk.co.za` | `agent_app_web:80` | Quasar agent mobile web |

Caddy config: `deploy/Caddyfile`

Caddy env vars (export in shell before running compose):

| Variable | Purpose | Example |
|----------|---------|---------|
| `BASIC_AUTH_USER` | Optional Basic Auth username | `admin` |
| `BASIC_AUTH_HASH` | bcrypt hash of password | `$2a$14$...` |
| `DB_PASSWORD` | Postgres password (used by db service) | `str0ngpassword` |

Generate Caddy hash:
```bash
docker run --rm caddy:2.8-alpine caddy hash-password --plaintext 'yourpassword'
```

---

## Network Architecture

```
Internet → Caddy (80/443)
              ├─ www.klikk.co.za      → website_web  (edge network)
              ├─ app.klikk.co.za      → admin_web    (edge network)
              ├─ register.klikk.co.za → admin_web    (edge network)
              ├─ backend.klikk.co.za  → backend      (edge network)
              └─ mobile-agent...      → agent_app_web (edge network)

backend (internal network only)
  ├─ → db:5432        (PostgreSQL)
  └─ → gotenberg:3000 (PDF generation)
```

`internal` network: backend, db, gotenberg — not reachable from Caddy or internet.
`edge` network: Caddy + all frontend containers + backend.

---

## App Configuration Reference

### 1. Website (Astro) — `website/`

**Build reads:** `.env.[mode]` where mode = `development` | `staging` | `production`

| Variable | Dev | Staging/Prod | Purpose |
|----------|-----|-------------|---------|
| `PUBLIC_APP_URL` | `http://localhost:5173` | `https://app.klikk.co.za` | Login button href |
| `PUBLIC_REGISTER_URL` | `http://localhost:5173/register` | `https://register.klikk.co.za` | Register CTA href |

**Dev:** `cd website && npm run dev`
**Staging build:** `cd website && npm run build -- --mode staging`
**Docker build:** `make -f deploy/Makefile website-build ENV=staging`

---

### 2. Admin (Vue 3 / Vite) — `admin/`

**Build reads:** `.env.[mode]`

| Variable | Dev | Staging/Prod | Purpose |
|----------|-----|-------------|---------|
| `VITE_API_URL` | `http://localhost:8000/api/v1` | `https://backend.klikk.co.za/api/v1` | REST API |
| `VITE_WS_URL` | `ws://localhost:8000` | `wss://backend.klikk.co.za` | WebSocket |
| `VITE_GOOGLE_CLIENT_ID` | shared | shared | Google OAuth |
| `VITE_GOOGLE_MAPS_KEY` | shared | shared | Google Maps |
| `VITE_SELF_SIGNUP` | `true` | `false` | Show register on login screen |

**Dev:** `cd admin && npm run dev`
**Docker build:** `make -f deploy/Makefile admin-build ENV=staging`

---

### 3. Agent App (Quasar) — `agent-app/`

**Build reads:** `.env.[mode]`

| Variable | Dev | Staging/Prod | Purpose |
|----------|-----|-------------|---------|
| `API_URL` | `http://localhost:8000/api/v1` | `https://backend.klikk.co.za/api/v1` | REST API |
| `GOOGLE_CLIENT_ID` | shared | shared | Google OAuth |

**Dev:** `cd agent-app && quasar dev`
**Docker build:** `make -f deploy/Makefile agent-build ENV=staging`

---

### 4. Backend (Django / Daphne) — `backend/`

**Config reads:** `.env` on the server (gitignored). Copy the template and fill in secrets.

**Django settings module per environment:**

| Environment | Module | Key differences |
|-------------|--------|-----------------|
| `local` | `config.settings.local` | `DEBUG=True`, `CORS_ALLOW_ALL_ORIGINS=True` |
| `staging` | `config.settings.staging` | `DEBUG=False`, secure cookies, `X-Frame-Options: DENY` |
| `production` | `config.settings.production` | staging + HSTS enabled |

**Dev setup:**
```bash
cp backend/.env.development backend/.env
# Fill in: SECRET_KEY, ANTHROPIC_API_KEY, EMAIL_HOST_PASSWORD
cd backend && python manage.py runserver
```

**Staging/Prod setup (first time on server):**
```bash
cp backend/.env.staging backend/.env          # or .env.production
# Fill in: SECRET_KEY, ANTHROPIC_API_KEY, DB_PASSWORD, EMAIL_HOST_PASSWORD
```

**Key variables:**

| Variable | Dev | Staging | Production | Notes |
|----------|-----|---------|------------|-------|
| `SECRET_KEY` | generate | generate | generate | 50-char random — **never commit** |
| `DEBUG` | `True` | `False` | `False` | Never True in prod |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | `backend.klikk.co.za` | `backend.klikk.co.za` | |
| `DB_HOST` | `localhost` | `db` | `db` | Docker service name |
| `DB_PASSWORD` | `klikk_pass` | **generate** | **generate** | **never commit** |
| `GOTENBERG_URL` | `http://localhost:3000` | `http://gotenberg:3000` | `http://gotenberg:3000` | |
| `SIGNING_PUBLIC_APP_BASE_URL` | `http://localhost:5173` | `https://app.klikk.co.za` | `https://app.klikk.co.za` | |
| `ESIGNING_WEBHOOK_PUBLIC_URL` | `http://localhost:8000` | `https://backend.klikk.co.za` | `https://backend.klikk.co.za` | |
| `ANTHROPIC_API_KEY` | your key | your key | your key | **never commit** |
| `EMAIL_HOST_PASSWORD` | app password | app password | app password | **never commit** |

**Generate SECRET_KEY:**
```bash
python -c "from django.utils.crypto import get_random_string; print(get_random_string(50))"
```

**ASGI server:** `daphne -b 0.0.0.0 -p 8000 config.asgi:application`

---

## Docker Compose Files

| File | Environment | Services |
|------|-------------|---------|
| `docker-compose.yml` | Development | db, backend (runserver), admin (Vite HMR), gotenberg |
| `deploy/docker-compose.staging.yml` | Staging | db, backend (daphne), admin, website, agent-app, gotenberg, caddy |
| `deploy/docker-compose.prod.yml` | Production | same as staging + pinned image versions, `DB_PASSWORD` required |

---

## Common Make Commands

Run from repo root: `make -f deploy/Makefile <target>`

```bash
# Development
make -f deploy/Makefile dev-up
make -f deploy/Makefile dev-down
make -f deploy/Makefile dev-logs

# Staging
make -f deploy/Makefile staging-build
make -f deploy/Makefile staging-up
make -f deploy/Makefile staging-down
make -f deploy/Makefile staging-logs
make -f deploy/Makefile staging-restart      # rebuild + restart

# Production
make -f deploy/Makefile prod-build
make -f deploy/Makefile prod-up
make -f deploy/Makefile prod-down
make -f deploy/Makefile prod-restart

# Per-app image builds
make -f deploy/Makefile website-build ENV=production
make -f deploy/Makefile admin-build   ENV=production
make -f deploy/Makefile agent-build   ENV=production

# Django management (STACK=staging|production)
make -f deploy/Makefile backend-migrate          STACK=staging
make -f deploy/Makefile backend-createsuperuser  STACK=staging
make -f deploy/Makefile backend-shell            STACK=staging
make -f deploy/Makefile backend-logs             STACK=production

# Tail a specific service (STACK=staging|production, SERVICE=<name>)
make -f deploy/Makefile logs    STACK=staging SERVICE=caddy
make -f deploy/Makefile restart STACK=staging SERVICE=backend
make -f deploy/Makefile ps      STACK=staging
```

---

## First-Time Server Setup (Staging or Production)

```bash
# 1. Clone the repo
git clone <repo-url> /opt/klikk
cd /opt/klikk

# 2. Create backend .env from the appropriate template
cp backend/.env.staging backend/.env         # or .env.production
nano backend/.env
# Must fill in: SECRET_KEY, ANTHROPIC_API_KEY, DB_PASSWORD, EMAIL_HOST_PASSWORD

# 3. Export DB_PASSWORD for the db service (must match what's in .env)
export DB_PASSWORD="your-strong-password"

# 4. (Optional) Set up Caddy Basic Auth to prevent indexing
export BASIC_AUTH_USER=admin
export BASIC_AUTH_HASH=$(docker run --rm caddy:2.8-alpine caddy hash-password --plaintext 'yourpassword')

# 5. Build and start everything
make -f deploy/Makefile staging-build        # or prod-build
make -f deploy/Makefile staging-up           # or prod-up

# 6. Run database migrations
make -f deploy/Makefile backend-migrate STACK=staging

# 7. Create superuser
make -f deploy/Makefile backend-createsuperuser STACK=staging

# 8. Verify all containers are healthy
make -f deploy/Makefile ps STACK=staging
make -f deploy/Makefile logs STACK=staging SERVICE=caddy
```

---

## Updating a Running Server

```bash
cd /opt/klikk
git pull

# Rebuild (Docker caches unchanged layers)
make -f deploy/Makefile staging-build

# Restart with new images
make -f deploy/Makefile staging-up

# Run any new migrations
make -f deploy/Makefile backend-migrate STACK=staging
```

---

## Security Notes

- **Caddy** handles TLS termination. Django does not redirect HTTP→HTTPS (avoids double-redirect through the proxy).
- **`SECURE_PROXY_SSL_HEADER`** is set in `staging.py` / `production.py` so Django trusts Caddy's `X-Forwarded-Proto` header.
- **HSTS** is enabled in `production.py` with a 5-minute `max-age` to start — increase to `31536000` once you've confirmed HTTPS is working correctly on all subdomains.
- **Session and CSRF cookies** are `Secure=True` in staging and production.
- **Backend container** runs as non-root user `appuser` (set in `backend/Dockerfile`).

---

## Environment File Rules

| File pattern | Committed? | Purpose |
|---|---|---|
| `.env` | **No** (gitignored) | Actual secrets — never commit |
| `.env.development` | Yes | Template with dev defaults |
| `.env.staging` | Yes | Template with staging URLs + placeholder secrets |
| `.env.production` | Yes | Template with production URLs + placeholder secrets |
| `.env.local` | **No** (gitignored) | Local overrides |

**Never commit:** `SECRET_KEY`, `ANTHROPIC_API_KEY`, `EMAIL_HOST_PASSWORD`, `DB_PASSWORD`
