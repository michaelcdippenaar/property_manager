---
id: RNT-SEC-010
stream: rentals
title: "Dependency vulnerability scan + patch high/critical CVEs"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: backlog
asana_gid: "1214177452645236"
assigned_to: null
depends_on: []
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Establish a baseline vulnerability posture across backend (pip), admin (npm), mobile (pub), and website (npm) dependencies. Patch every High and Critical CVE before v1.0 ships.

## Acceptance criteria
- [ ] `pip-audit` run on `backend/requirements.txt` → 0 High/Critical
- [ ] `npm audit --audit-level=high` on `admin/`, `web_app/`, `website/`, `agent-app/` → 0 High/Critical
- [ ] CI job runs these on every PR and fails on regression
- [ ] Dependabot (or Renovate) enabled on repo with weekly schedule
- [ ] Document the scan + resolutions in `docs/ops/dependency-audit-2026-04.md`
- [ ] Flutter apps (`mobile/`, `tenant_app/`) are DEPRECATED and excluded from all scans

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
