---
discovered_by: rentals-reviewer
discovered_during: RNT-SEC-037
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: RNT-QUAL
---

## What I found
After the ESM conversion in `agent-app/quasar.config.js`:
1. Unused import `fileURLToPath` on line 3 (leftover from the ESM migration).
2. `agent-app/package.json` is missing `"type": "module"`. Node warns `MODULE_TYPELESS_PACKAGE_JSON` every time the config is loaded and has to re-parse — minor perf + noisy logs.

## Why it matters
Cosmetic / DX. No functional impact, but dead code and a noisy startup warning are the kind of thing that bit-rots into real confusion later. Quasar v2 tooling may expect `"type": "module"` in some flows.

## Where I saw it
- `agent-app/quasar.config.js:3` — unused `fileURLToPath` import
- `agent-app/package.json` — missing `"type": "module"`
- Node warning reproduced via `node --input-type=module -e "import('./quasar.config.js')"`

## Suggested acceptance criteria (rough)
- [ ] Remove unused `fileURLToPath` import from `quasar.config.js`
- [ ] Add `"type": "module"` to `agent-app/package.json` and verify `quasar dev`/`quasar build`/`cap sync` still work
- [ ] Confirm no `MODULE_TYPELESS_PACKAGE_JSON` warning on build

## Why I didn't fix it in the current task
Out of scope — RNT-SEC-037 is a security dependency bump. These are DX cleanups that should go through their own implement/test cycle (and require a Quasar build + Capacitor sync re-verify, which the tester is already doing).
