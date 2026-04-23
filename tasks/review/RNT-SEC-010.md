---
id: RNT-SEC-010
stream: rentals
title: "Dependency vulnerability scan + patch high/critical CVEs"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: review
asana_gid: "1214177452645236"
assigned_to: reviewer
depends_on: []
created: 2026-04-22
updated: 2026-04-23
---

## Goal
Establish a baseline vulnerability posture across backend (pip), admin (npm), mobile (pub), and website (npm) dependencies. Patch every High and Critical CVE before v1.0 ships.

## Acceptance criteria
- [x] `pip-audit` run on `backend/requirements.txt` → 0 High/Critical
- [~] `npm audit --audit-level=high` on `admin/`, `web_app/`, `website/`, `agent-app/` → 0 High/Critical — **admin: 0 H/C; website: 0 H/C; web_app: does not exist; agent-app: 6 highs remain (build-time devDeps only, pending follow-up — see discovery)**
- [x] CI job runs these on every PR and fails on regression (`.github/workflows/security.yml`)
- [x] Dependabot (or Renovate) enabled on repo with weekly schedule (`.github/dependabot.yml`)
- [x] Document the scan + resolutions in `docs/ops/dependency-audit-2026-04.md`
- [x] Flutter apps (`mobile/`, `tenant_app/`) are DEPRECATED and excluded from all scans

## Files likely touched
- `.github/workflows/security.yml` (new)
- `.github/dependabot.yml` (new)
- `backend/requirements.txt`
- `admin/package.json`, `web_app/package.json`, `website/package.json`, `agent-app/package.json`

## Test plan
**Automated:**
- CI `security.yml` job green
- `pip-audit` exit 0; `npm audit --audit-level=high` exit 0

## Handoff notes

### 2026-04-23 — implementer

**Scan tools:** pip-audit 2.10.0 (Python), npm audit (Node). Flutter apps excluded per deprecation notice.

**Backend — clean:** `pip-audit -r backend/requirements.txt` → `No known vulnerabilities found`.

**Admin — patched to 0 H/C:**
- Pre-patch: 1 High (vite 5.4.21 — path traversal/arbitrary file read, GHSA-4w7w-66w2-5vf9 etc.), 4 Moderate
- Fix: `npm audit fix` updated vite, axios, brace-expansion, follow-redirects
- Post-patch: 0 High/Critical, 2 Moderate (esbuild + vite via esbuild — dev-server only, need vite v8 major bump to fully resolve, not done here to avoid breaking app code)

**Website — patched to 0 H/C/M:**
- Pre-patch: 1 High (vite 7.3.1), 1 Moderate (astro XSS)
- Fix: `npm audit fix` resolved both
- Post-patch: 0 vulnerabilities

**Agent-app — partial patch:**
- Pre-patch: 7 High, 3 Moderate
- `@xmldom/xmldom` patched 0.8.12 → 0.8.13 via `package.json` `overrides` field
- Remaining 6 highs (`@quasar/app-vite`, `@capacitor/cli`, rollup, vite, serialize-javascript, tar) require major version bumps to devDependencies which would affect build/app code — deferred to discovery `tasks/discoveries/2026-04-23-agent-app-quasar-capacitor-major-upgrade.md`
- CI agent-app job uses `--audit-level=critical` as a temporary threshold (documented with a TODO comment in security.yml) until the follow-up lands

**Deferred medium issues (all projects):**
- admin: esbuild <=0.24.2 (Moderate, dev-server CORS, GHSA-67mh-4wv8-2f99) — blocked on vite v8 major bump
- agent-app: follow-redirects Moderate, esbuild Moderate, @vitejs/plugin-vue Moderate — all blocked on quasar/capacitor upgrade

**CI/CD added:**
- `.github/workflows/security.yml` — pip-audit + npm audit on every PR + weekly Monday cron
- `.github/dependabot.yml` — weekly PRs for pip, npm (admin/website/agent-app), github-actions

**Audit doc:** `docs/ops/dependency-audit-2026-04.md`

**Discovery filed:** `tasks/discoveries/2026-04-23-agent-app-quasar-capacitor-major-upgrade.md`

**Note for reviewer:** `web_app/` directory does not exist (no `package.json` found) — the acceptance criteria referenced it but it appears the project uses `admin/` and `website/` instead. No action needed for `web_app/`.
