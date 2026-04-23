---
id: RNT-SEC-037
stream: rentals
title: "Upgrade agent-app @quasar/app-vite v1→v2 and @capacitor/* v6→v8 to resolve high npm vulnerabilities"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: backlog
assigned_to: null
depends_on: []
asana_gid: null
created: 2026-04-23
updated: 2026-04-23
---

## Goal
Bump `@quasar/app-vite` from v1 to v2.6 and all `@capacitor/*` packages from v6 to v8 to eliminate six high-severity npm advisories (including CVSS 8.1 RCE in `serialize-javascript`) from the mobile app build pipeline.

## Acceptance criteria
- [ ] `@quasar/app-vite` bumped to `^2.6.0` (or latest v2 stable) with quasar build verified clean
- [ ] `@capacitor/cli` bumped to `^8.3.1` with all `@capacitor/*` packages aligned to v8
- [ ] `npm audit --audit-level=high` exits 0 inside `agent-app/`
- [ ] iOS + Android Capacitor build confirmed working after upgrade
- [ ] CI `security.yml` agent-app job tightened back to `--audit-level=high`

## Files likely touched
- `agent-app/package.json`
- `agent-app/package-lock.json`
- `agent-app/src/` (any breaking API changes from major version bumps)
- `agent-app/capacitor.config.ts` (if plugin config changes required)
- `.github/workflows/security.yml`

## Test plan
**Manual:**
- `cd agent-app && npm audit --audit-level=high` — confirm 0 high findings
- `npm run build` — confirm Quasar build succeeds
- `npx cap sync ios && npx cap sync android` — confirm Capacitor plugins sync
- Smoke-test iOS and Android simulator builds

**Automated:**
- CI security workflow passes with `--audit-level=high`

## Handoff notes
2026-04-23: Promoted from discovery `2026-04-23-agent-app-quasar-capacitor-major-upgrade.md` (found during RNT-SEC-010). `serialize-javascript` carries GHSA-5c6j-r48x-rmvq CVSS 8.1 RCE; build-time only but supply-chain risk. All six highs require major version bumps. See `docs/ops/dependency-audit-2026-04.md`.
