# CI/CD Pipeline

## Overview

Two GitHub Actions workflows automate quality gates and deployments:

| Workflow | File | Trigger |
|----------|------|---------|
| **CI** | `.github/workflows/ci.yml` | Every PR to `main`, every push to `main` |
| **Deploy to Staging** | `.github/workflows/staging-deploy.yml` | Every push to `main` (after CI passes) |

---

## CI Workflow

Runs three parallel jobs:

### `backend` — Python quality + tests
1. Spins up a Postgres 16 service container.
2. Installs `requirements.txt` plus `ruff` and `black`.
3. `ruff check .` — lint
4. `black --check .` — format
5. `pytest --tb=short -q` against the test DB.

### `admin` — Admin SPA quality
1. `npm ci` in `admin/`.
2. ESLint (skipped gracefully if no config exists yet).
3. `vitest --run` — unit tests.
4. `vue-tsc --noEmit` — TypeScript compile check.

### `flutter` — Mobile analyze
1. Sets up Flutter stable (3.x).
2. `flutter pub get` in `mobile/`.
3. `flutter analyze --no-fatal-infos`.

---

## Staging Deploy Workflow

Runs on every push to `main` (i.e. after any PR merge).

### `build-and-push` job
- Tags all images with the short Git SHA (first 8 chars of `GITHUB_SHA`).
- Pushes to GitHub Container Registry (`ghcr.io/michaelcdippenaar/`):
  - `klikk-backend`
  - `klikk-admin`
  - `klikk-agent-app`
- Uses GitHub Actions layer cache (`type=gha`) to speed up re-builds.

### `deploy` job
1. SSHs into the staging server using `STAGING_SSH_KEY`.
2. `git pull --ff-only origin main` — ensures compose files and Caddyfile are current.
3. Sets `BACKEND_IMAGE`, `ADMIN_IMAGE`, `AGENT_APP_IMAGE` env vars to the exact SHA tag.
4. `docker compose pull` — downloads the new images.
5. `docker compose up -d --remove-orphans` — starts containers.
6. `python manage.py migrate --noinput` — applies any pending DB migrations.
7. Smoke-checks `https://<STAGING_DOMAIN>/api/v1/health/`.

---

## Required GitHub Actions Secrets

Set these in **GitHub → repository Settings → Secrets and variables → Actions**:

| Secret name | Description |
|-------------|-------------|
| `STAGING_SSH_KEY` | Private key matching the public key in `~/.ssh/authorized_keys` on the staging server. Use `ssh-keygen -t ed25519 -C "github-actions"`. |
| `STAGING_SSH_USER` | SSH username (e.g. `mc`) |
| `STAGING_HOST` | Staging server IP or hostname (e.g. `192.168.1.235`) |
| `STAGING_DOMAIN` | Public domain for the smoke-check (e.g. `backend.klikk.co.za`) |
| `GHCR_PAT` | GitHub Personal Access Token with `read:packages` scope — used to `docker login ghcr.io` on the staging server so it can pull images. |

`GITHUB_TOKEN` is provided automatically by Actions for the `build-and-push` job (write:packages).

---

## Branch Protection

To enforce CI before merging, configure in **GitHub → Settings → Branches → Branch protection rules** for `main`:

- [x] Require a pull request before merging
- [x] Require status checks to pass before merging
  - Required checks: `Backend (ruff, black, pytest)`, `Admin SPA (eslint, vitest)`, `Flutter (analyze)`
- [x] Require branches to be up to date before merging
- [x] Do not allow bypassing the above settings

---

## Rollback

Each deploy keeps the previous image tag alive in GHCR (only `latest` is overwritten; the SHA-tagged images are never deleted automatically).

### One-command rollback

SSH into the staging server and re-pin to the previous SHA:

```bash
ssh mc@192.168.1.235
cd ~/apps/property_manager

# Find the previous commit SHA (8 chars)
git log --oneline -5

# Set the images to the previous SHA and restart
export BACKEND_IMAGE="ghcr.io/michaelcdippenaar/klikk-backend:<previous-sha>"
export ADMIN_IMAGE="ghcr.io/michaelcdippenaar/klikk-admin:<previous-sha>"
export AGENT_APP_IMAGE="ghcr.io/michaelcdippenaar/klikk-agent-app:<previous-sha>"

docker compose -f deploy/docker-compose.staging.yml pull backend admin_web agent_app_web
docker compose -f deploy/docker-compose.staging.yml up -d
```

Old DB migrations are not automatically reversed. If a migration must be reversed, run:

```bash
docker compose -f deploy/docker-compose.staging.yml exec backend \
  python manage.py migrate <app_label> <previous_migration_number>
```

---

## Image Retention

GHCR does not auto-delete old image versions. To avoid unbounded growth, configure a retention policy in **GitHub → Packages → klikk-backend → Package settings → Set retention policy** (e.g. keep last 10 versions).
