---
discovered_by: rentals-reviewer
discovered_during: OPS-001
discovered_at: 2026-04-22
priority_hint: P2
suggested_prefix: OPS
---

## What I found

`website_web` in `deploy/docker-compose.staging.yml` has no `image:` override and is not built or pushed by the CI/CD workflow added in OPS-001. Every other service (`backend`, `admin_web`, `agent_app_web`) was given an `image:` env-var override so the deploy workflow can pin an exact SHA tag — `website_web` was missed.

## Why it matters

On every staging deploy, `docker compose pull` skips `website_web` (nothing to pull from a registry). The marketing site on staging will run from whatever locally-built image already exists on the server, meaning it can silently lag `main` by many commits. Once the Astro site ships real content, this will cause staging/production drift.

## Where I saw it

- `deploy/docker-compose.staging.yml` lines 92–100: `website_web` has `build:` but no `image:` field
- `.github/workflows/staging-deploy.yml`: only builds/pushes `klikk-backend`, `klikk-admin`, `klikk-agent-app` — no `klikk-website` image

## Suggested acceptance criteria (rough)
- [ ] Add `image: ${WEBSITE_IMAGE:-ghcr.io/michaelcdippenaar/klikk-website:latest}` to `website_web` in `docker-compose.staging.yml`
- [ ] Add a `Build & push website` step to `staging-deploy.yml` using `./website/Dockerfile`
- [ ] `WEBSITE_IMAGE` exported in the deploy SSH block alongside the other three images

## Why I didn't fix it in the current task

OPS-001 scope was the three app images already in the pipeline. The Astro website Dockerfile may not yet be stable; promoting `website_web` into the automated pipeline is a follow-up decision.
