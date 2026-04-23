---
id: RNT-SEC-037
stream: rentals
title: "Upgrade agent-app @quasar/app-vite v1→v2 and @capacitor/* v6→v8 to resolve high npm vulnerabilities"
feature: ""
lifecycle_stage: null
priority: P1
effort: M
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214229901336165"
created: 2026-04-23
updated: 2026-04-23T13:30:00
---

## Goal
Bump `@quasar/app-vite` from v1 to v2.6 and all `@capacitor/*` packages from v6 to v8 to eliminate six high-severity npm advisories (including CVSS 8.1 RCE in `serialize-javascript`) from the mobile app build pipeline.

## Acceptance criteria
- [x] `@quasar/app-vite` bumped to `^2.6.0` (or latest v2 stable) with quasar build verified clean
- [x] `@capacitor/cli` bumped to `^8.3.1` with all `@capacitor/*` packages aligned to v8
- [x] `npm audit --audit-level=high` exits 0 inside `agent-app/`
- [ ] iOS + Android Capacitor build confirmed working after upgrade
- [x] CI `security.yml` agent-app job tightened back to `--audit-level=high`

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

2026-04-23 (implementer): Upgrades applied. Summary of changes:

**package.json:**
- `@quasar/app-vite`: `^1.9.0` → `^2.6.0`
- `@capacitor/cli`: `^6.0.0` → `^8.3.1`
- `@capacitor/core`, `@capacitor/ios`, `@capacitor/android`: `^6.0.0` → `^8.3.1`
- `@capacitor/splash-screen`: `^6.0.0` → `^8.0.1`
- `@capacitor/status-bar`: `^6.0.0` → `^8.0.2`
- `@quasar/extras`: `^1.16.0` → `^1.17.0` (peer dep requirement for v2)
- `@sentry/capacitor`: `^1.0.0` → `^3.2.1` (in-scope sub-fix: v1 was hard-incompatible with v8 Capacitor; v3 requires `@sentry/vue` pinned to exact version)
- `@sentry/vue`: `^8.0.0` → `10.43.0` (exact pin required by `@sentry/capacitor@^3`)
- `--legacy-peer-deps` flag removed from CI install (no longer needed)

**quasar.config.js:** Converted from CommonJS (`require`/`module.exports`) to ESM (`import`/`export default`) since `@quasar/app-vite` v2 treats `.js` config as ESM format.

**tsconfig.json:** Dropped `extends: "@quasar/app-vite/tsconfig-preset"` — that path was removed in v2 (no longer exported). Inlined the equivalent compiler options (`module: Preserve`, `strict: true`, `lib: [es2022, dom]`) plus explicit `include` for `.d.ts`, `.ts`, `.vue` files. The old preset's options were minimal and identical.

**`.github/workflows/security.yml`:** Removed `--legacy-peer-deps` from install and reverted `--audit-level=critical` back to `--audit-level=high` as planned.

**Audit result:** `npm audit --audit-level=high` → 0 vulnerabilities (was 6 highs + 3 moderates).

**Smoke-check:** `quasar build` (SPA mode) succeeds cleanly — 574 KB JS, 254 KB CSS, Build succeeded. iOS/Android Capacitor sync (`npx cap sync`) and simulator smoke-test are left to the tester — requires Xcode and Android Studio.
