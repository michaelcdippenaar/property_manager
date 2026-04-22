---
id: RNT-SEC-013
stream: security
title: "Anchor gitleaks path allowlist so committed .env.* files are scanned"
feature: ""
lifecycle_stage: null
priority: P1
effort: S
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: "1214181228024983"
created: 2026-04-22
updated: 2026-04-22
---

## Goal
Fix the `.gitleaks.toml` path allowlist so that unanchored regexes no longer suppress secret detection on committed `.env.development`, `.env.staging`, and `.env.production` files — only the gitignored `.env` and `.env.secrets` files should be excluded.

## Acceptance criteria
- [ ] `backend/\.env` path entry anchored: change to `'''backend/\.env$'''` (or similar end-anchor)
- [ ] `backend/\.env\.secrets` similarly anchored: `'''backend/\.env\.secrets$'''`
- [ ] `admin/\.env` anchored: `'''admin/\.env$'''`
- [ ] `gitleaks detect --source . --no-git` still exits 0 on a clean dev checkout
- [ ] `backend/.env.development`, `backend/.env.staging`, `backend/.env.production`, `admin/.env.*` are NOT in the allowlist — gitleaks scans them normally
- [ ] Pre-commit hook and CI gitleaks step both pass

## Files likely touched
- `.gitleaks.toml`

## Test plan
**Manual:**
- Temporarily add a fake secret string to `backend/.env.development` and run `gitleaks detect --source . --no-git` — must report a finding (not suppress it)
- Remove the fake secret and re-run — must exit 0

**Automated:**
- CI `gitleaks` step exits 0 on the main branch after anchoring

## Handoff notes
(Each agent appends a dated entry here on handoff. Do not edit prior entries.)

2026-04-22 — Promoted from discovery `2026-04-22-gitleaks-env-regex-overbroad.md` found during RNT-SEC-011 review. The overbroad allowlist is a silent gap: any real secret accidentally written to a committed .env file would not trigger a gitleaks alert.
