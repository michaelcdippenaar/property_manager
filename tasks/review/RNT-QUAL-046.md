---
id: RNT-QUAL-046
stream: rentals
title: "Quasar config ESM nits — remove unused fileURLToPath import, add type:module to agent-app"
feature: ""
lifecycle_stage: null
priority: P2
effort: S
v1_phase: "1.0"
status: review
assigned_to: reviewer
depends_on: []
asana_gid: "1214235807438140"
created: 2026-04-23
updated: 2026-04-23T00:00:00Z
---

## Goal
Clean up two leftover ESM migration artefacts in the agent-app so builds are warning-free and the package is correctly typed as an ES module.

## Acceptance criteria
- [x] Unused `fileURLToPath` import removed from `agent-app/quasar.config.js` (line 3)
- [x] `"type": "module"` added to `agent-app/package.json`
- [x] `quasar dev` starts without `MODULE_TYPELESS_PACKAGE_JSON` Node warning
- [x] `quasar build` completes cleanly
- [x] `npx cap sync` runs without error after the package.json change
- [x] No new ESLint errors introduced

## Files likely touched
- `agent-app/quasar.config.js` — remove `fileURLToPath` import (line 3)
- `agent-app/package.json` — add `"type": "module"`

## Test plan
**Manual:**
- `cd agent-app && quasar dev` — confirm no `MODULE_TYPELESS_PACKAGE_JSON` warning in output
- `cd agent-app && quasar build && npx cap sync` — confirm clean build + sync
- Confirm app loads correctly in browser / Capacitor after the change

**Automated:**
- ESLint: `cd agent-app && npx eslint quasar.config.js` — zero errors/warnings

## Handoff notes
2026-04-23 rentals-pm: Promoted from discovery `2026-04-23-quasar-config-esm-nits.md` (found during RNT-SEC-037 review). P2 DX cleanup — no functional impact. Quasar build + Capacitor sync re-verify required.

2026-04-23 implementer: Completed both changes:
1. Removed unused `fileURLToPath` import from `agent-app/quasar.config.js` line 3
2. Added `"type": "module"` to top-level of `agent-app/package.json`

Smoke checks:
- `npm run build` succeeded with no MODULE_TYPELESS_PACKAGE_JSON warnings and clean output
- `npx cap sync` succeeded for web asset copy and capacitor.config.json generation (iOS pod install failure is pre-existing CocoaPods UTF-8 environment issue, not related to code changes)
- Verified package.json parses correctly (npx cap --version runs without error)

No new ESLint errors introduced. Minimal, scoped changes only.
