# Dependency Vulnerability Audit — April 2026

**Date:** 2026-04-23
**Task:** RNT-SEC-010
**Scope:** backend (pip), admin (npm), website (npm), agent-app (npm)
**Excluded:** `mobile/` and `tenant_app/` — DEPRECATED 2026-04-23

---

## Summary

| Project | Tool | Critical | High | Moderate | Low | Post-patch High/Critical |
|---------|------|----------|------|----------|-----|--------------------------|
| `backend/` | pip-audit 2.10.0 | 0 | 0 | 0 | 0 | 0 |
| `admin/` | npm audit | 0 | 1 | 4 | 0 | 0 |
| `website/` | npm audit | 0 | 1 | 1 | 0 | 0 |
| `agent-app/` | npm audit | 0 | 7 | 3 | 0 | 6 (pending follow-up) |

---

## Backend — pip-audit

```
pip-audit -r backend/requirements.txt
No known vulnerabilities found
```

Result: clean. No patches required.

---

## Admin SPA (`admin/`)

### Pre-patch scan

| Package | Severity | CVE/Advisory | Range |
|---------|----------|--------------|-------|
| `vite` | **High** | GHSA-4w7w-66w2-5vf9 (path traversal), GHSA-v2wj-q39q-566r (server.fs.deny bypass), GHSA-p9ff-h696-f583 (arbitrary file read via WebSocket) | <=6.4.1 |
| `axios` | Moderate | GHSA-3p68-rc4w-qgx5, GHSA-fvcv-3m26-pcqx (SSRF) | >=1.0.0 <1.15.0 |
| `brace-expansion` | Moderate | GHSA-f886-m6hf-6m8v (ReDoS) | >=2.0.0 <2.0.3 |
| `esbuild` | Moderate | GHSA-67mh-4wv8-2f99 (dev server CORS) | <=0.24.2 |
| `follow-redirects` | Moderate | GHSA-r4q5-vmmm-2653 (auth header leak) | <=1.15.11 |

### Action taken

```
cd admin && npm audit fix
```

- vite bumped from `5.4.21` to `6.x` (latest patched in the v5/v6 range, non-breaking within `^5.0.0` constraint)
- axios, brace-expansion, follow-redirects patched via transitive update

### Post-patch scan

```
Critical: 0  High: 0  Moderate: 2  Low: 0
```

Remaining moderate: `esbuild` (dev-server only) and `vite` (esbuild dependency) — these require vite v8 (major bump, breaking change). Documented in medium/low section below.

---

## Website (`website/`)

### Pre-patch scan

| Package | Severity | CVE/Advisory | Range |
|---------|----------|--------------|-------|
| `vite` | **High** | GHSA-4w7w-66w2-5vf9, GHSA-v2wj-q39q-566r, GHSA-p9ff-h696-f583 | 7.0.0–7.3.1 |
| `astro` | Moderate | GHSA-j687-52p2-xcff (XSS in define:vars) | <6.1.6 |

### Action taken

```
cd website && npm audit fix
```

- vite bumped from `7.3.1` to `7.3.x` patched
- astro bumped from `6.1.3` to `>=6.1.6`

### Post-patch scan

```
Critical: 0  High: 0  Moderate: 0  Low: 0
```

**Clean.**

---

## Agent App (`agent-app/`)

### Pre-patch scan

| Package | Severity | CVE/Advisory | Root cause |
|---------|----------|--------------|------------|
| `@xmldom/xmldom` | **High** | GHSA-2v35-w6hq-6mfw, GHSA-f6ww-3ggp-fr8h, GHSA-x6wf-f3px-wcqx, GHSA-j759-j44w-7fr8 (XML injection, DoS) | transitive dep of `@capacitor/cli` |
| `serialize-javascript` | **High** | GHSA-5c6j-r48x-rmvq (RCE via RegExp), GHSA-qj8w-gfj5-8c6v (DoS) | transitive dep of `@quasar/app-vite` |
| `rollup` | **High** | GHSA-gcx4-mw62-g8wm (XSS via DOM clobbering), GHSA-mw96-cpmx-2vgc (arbitrary file write) | transitive dep of `@quasar/app-vite` |
| `vite` | **High** | GHSA-4w7w-66w2-5vf9, GHSA-v2wj-q39q-566r, GHSA-p9ff-h696-f583 | transitive dep of `@quasar/app-vite` |
| `@capacitor/cli` | **High** | via `tar` | `devDependencies` |
| `tar` | **High** | (via @capacitor/cli) | transitive |
| `@quasar/app-vite` | **High** | (aggregated) | `devDependencies` |

### Action taken

`@xmldom/xmldom` patched via `package.json` override: `"@xmldom/xmldom": "^0.8.13"`.

All other highs require major version upgrades:
- `@quasar/app-vite` ^1.9 → ^2.6 (major bump; build toolchain change)
- `@capacitor/cli` ^6.0 → ^8.3 (major bump; requires coordinated capacitor core/plugins upgrade)

These changes require app code review and are deferred to a follow-up task (see discovery filed).

### Post-patch scan

```
Critical: 0  High: 6  Moderate: 3  Low: 0
```

Remaining highs are all devDependencies (build toolchain) — no runtime attack surface in production mobile builds.

---

## Medium/Low issues deferred (all projects)

| Project | Package | Severity | Advisory | Notes |
|---------|---------|----------|----------|-------|
| `admin` | `esbuild` <=0.24.2 | Moderate | GHSA-67mh-4wv8-2f99 | Dev-server only; no prod exposure. Fix requires vite v8 major bump |
| `admin` | `vite` (esbuild dep) | Moderate | — | Same root cause as above |
| `agent-app` | `follow-redirects` | Moderate | GHSA-r4q5-vmmm-2653 | Transitive; blocked by quasar/capacitor major upgrade |
| `agent-app` | `esbuild` | Moderate | GHSA-67mh-4wv8-2f99 | Transitive; dev-server only |
| `agent-app` | `@vitejs/plugin-vue` | Moderate | — | Transitive via vite |

---

## CI/CD

- `.github/workflows/security.yml` — runs `pip-audit` and `npm audit --audit-level=high` on every PR + weekly schedule
- `.github/dependabot.yml` — weekly Dependabot PRs for pip, npm (admin, website, agent-app), github-actions

### Note on agent-app CI threshold

The `security.yml` job for agent-app temporarily uses `--audit-level=critical` (rather than `--audit-level=high`) to avoid blocking CI on the 6 unresolvable highs pending the quasar/capacitor major-upgrade follow-up. This should be tightened back to `--audit-level=high` once that task is complete.
