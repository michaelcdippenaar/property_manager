# Skill Audit — Klikk Rentals v1

Audit date: 2026-04-22. Project skills live in `.claude/skills/`. Audit maps them against the v1 backlog task streams.

## Stream coverage matrix

| Stream | Tasks | Supporting skills | Verdict |
|---|---|---|---|
| RNT (rentals code hardening) | RNT-001..002 + promoted discoveries | `klikk-leases-*` (7 skills), `klikk-rental-master`, `klikk-platform-product-status` | ✅ strong |
| RNT-SEC (security) | RNT-SEC-001..010 | `klikk-security-audit`, `-auth-hardening`, `-api-review`, `-user-model`, `-vuln-scan`, `-compliance`, `klikk-legal-POPIA-RHA` | ✅ very strong — 7 skills |
| RNT-QUAL (quality/edge) | RNT-QUAL-001..010 | `klikk-platform-testing`, `klikk-leases-test-battery` | ✅ adequate |
| GTM (marketing) | GTM-001..007 | `klikk-marketing-strategy`, `-website`, `-sales-enablement`, `-competitive-intel` | ✅ strong |
| UX (onboarding) | UX-NNN (none yet) | `klikk-design-standard`, `-mobile-ux`, `-frontend-taste` | ⚠️ **gap** — UI covered, onboarding content not |
| OPS (launch ops) | OPS-001..009 | `klikk-platform-gotenberg` (partial) | ❌ **major gap** — CI/CD, monitoring, DNS/TLS, SES, backups uncovered |
| QA | QA-001..010 | `klikk-platform-testing`, `klikk-leases-test-battery` | ✅ adequate |
| MIL / DEC | gates / decisions | n/a | not skill-shaped |

## Gaps — recommended new skills

Priority order. Each backs at least one v1 task stream that currently has no expert skill behind it.

### 1. `klikk-ops-deployment` — **HIGH**
Backs: OPS-001 (CI/CD), OPS-003 (backups), OPS-005 (staging env), OPS-006 (DNS/TLS/email), OPS-007 (release process).
What it knows: Caddy Caddyfile, Let's Encrypt auto-HTTPS, Django ALLOWED_HOSTS/CSRF/CORS patterns, AWS SES DKIM/SPF/DMARC on subdomain, Cloudflare/CloudFront CDN, Postgres backup/restore, env-var management. Sonnet.

### 2. `klikk-ops-observability` — **HIGH**
Backs: OPS-002 (Sentry), OPS-008 (UptimeRobot + status page), GTM-006 (Plausible analytics).
What it knows: Sentry Django + Capacitor wiring, release tagging, source maps, alert policies; UptimeRobot setup + incident routing; Plausible self-hosted install + goal tracking. Sonnet.

### 3. `klikk-mobile-capacitor` — **MEDIUM**
Backs: RNT-008, RNT-009 (Quasar + Capacitor native wraps).
What it knows: `quasar mode add capacitor`, iOS Xcode signing + Info.plist permission strings + `PrivacyInfo.xcprivacy`, Android AndroidManifest + Play Data Safety form, TestFlight + Play Internal Testing submission, deep links / Universal Links / App Links, APNs + FCM push. Distinct from `klikk-design-mobile-ux` (which is UI-only). Sonnet.

### 4. `klikk-onboarding-author` — **MEDIUM**
Backs: all future UX-NNN tasks; gives `ux-onboarding` agent a real skill to lean on.
What it knows: first-rental-cycle golden path (from lifecycle.yaml), coach-mark / empty-state copy patterns, Grade-8 readability, short video script format, in-app help-centre article structure. Haiku — mostly content writing.

### 5. `klikk-ops-secrets` — **LOW**
Backs: RNT-SEC-001 (secret rotation) + ongoing hygiene.
What it knows: secret inventory, rotation runbooks, .env policy, AWS IAM policy minima, key-rotation cadence, leak response. Could also fold into `klikk-ops-deployment` — decide once that one exists.

## Naming / duplication notes

- `klikk-vault31-ingestion` vs `klikk-volt31-test` — "Vault" vs "Volt" vs "vault31" vs "volt31" is confusing. Recommend picking one (Vault33 per the system doc?) and renaming.
- `klikk-leases-pdf-export` + `klikk-platform-gotenberg` — legitimate split (lease-specific pipeline vs service layer). Keep both.
- `klikk-security-audit` + `klikk-security-vuln-scan` — legitimate split (OWASP framework vs pattern SAST). Keep both.
- `klikk-rental-master` + `klikk-legal-POPIA-RHA` — rental-master is broader workflow; legal is strict statutory. Keep both; `klikk-legal-POPIA-RHA` has a nice explicit "for general workflow questions use klikk-rental-master instead" pointer.

## Agent tool-allowlist fixes (immediate)

Three agents reference MCP tools that aren't in their `tools:` allowlist — they will fail at runtime:

- `.claude/agents/rentals-tester.md` — add `mcp__tremly-e2e__*, mcp__Claude_Preview__*`
- `.claude/agents/rentals-pm.md` — add `mcp__10639c47-fcf4-4539-a5e4-246e10d541c8__*`
- `.claude/agents/ux-onboarding.md` — add `mcp__Claude_Preview__*, mcp__tremly-e2e__*`

## Recommendation

Build the two HIGH-priority skills (`klikk-ops-deployment`, `klikk-ops-observability`) before kicking off the OPS stream — those 9 tasks otherwise land with no expert skill behind them, which is a quality risk on launch-critical work. The other three can be drafted lazily as their streams start.
