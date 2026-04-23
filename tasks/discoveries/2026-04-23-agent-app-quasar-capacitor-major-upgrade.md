---
discovered_by: rentals-implementer
discovered_during: RNT-SEC-010
discovered_at: 2026-04-23
priority_hint: P1
suggested_prefix: RNT-SEC
---

## What I found

`agent-app/` has 6 unresolved high-severity npm vulnerabilities in `@quasar/app-vite` (v1.9), `@capacitor/cli` (v6), and their transitive deps (rollup, vite, serialize-javascript, tar). All fixes require major version bumps: `@quasar/app-vite` v1 → v2.6 and `@capacitor/cli` v6 → v8.

## Why it matters

`serialize-javascript` carries a CVSS 8.1 RCE (GHSA-5c6j-r48x-rmvq) and `rollup` carries path-traversal + XSS advisories. These are build-time/devDep dependencies so there is no direct runtime production exposure, but a compromised build pipeline could inject malicious code into the mobile app bundle.

## Where I saw it

- `agent-app/package.json` — `@quasar/app-vite: "^1.9.0"`, `@capacitor/cli: "^6.0.0"`
- `npm audit` output in `docs/ops/dependency-audit-2026-04.md`
- All six high advisories require `@quasar/app-vite@2.6.0` or `@capacitor/cli@8.3.1` to resolve

## Suggested acceptance criteria (rough)

- [ ] `@quasar/app-vite` bumped to `^2.6.0` (or latest v2) and quasar build verified
- [ ] `@capacitor/cli` bumped to `^8.3.1` with all `@capacitor/*` packages aligned to v8
- [ ] `npm audit --audit-level=high` exits 0 in agent-app
- [ ] iOS + Android capacitor build confirmed working after upgrade
- [ ] CI `security.yml` agent-app job tightened back to `--audit-level=high`

## Why I didn't fix it in the current task

Upgrading @quasar/app-vite from v1 to v2 and @capacitor/* from v6 to v8 requires coordinated changes across app source code and Capacitor plugin configuration — this is a breaking change that could require modifications in `agent-app/src/` which is outside this task's scope constraint.
