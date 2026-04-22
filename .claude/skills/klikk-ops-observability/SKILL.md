---
name: klikk-ops-observability
description: >
  Monitoring, error tracking, uptime, and analytics for the Klikk platform. Use this
  skill whenever configuring or debugging: Sentry (Django backend, Vue 3 SPA, Quasar
  + Capacitor mobile), Sentry releases and source maps, Sentry alert rules,
  UptimeRobot monitors, public status pages at status.klikk.co.za, incident response
  routing, Plausible Analytics (self-hosted) event tracking and goals, request-level
  tracing, structured logging, log aggregation, or any "are we down / did we break
  something" question. Trigger phrases: "Sentry", "error tracking", "source maps",
  "release marker", "Sentry Capacitor", "UptimeRobot", "uptime monitor",
  "status page", "status.klikk.co.za", "5xx alert", "down alert", "incident response",
  "alert rules", "Plausible", "self-hosted analytics", "goal tracking", "conversion
  event", "funnel analytics", "observability", "monitoring stack", "crash reporting",
  "MTTR", "alert fatigue", "health check", "synthetic monitor", "TLS expiry alert",
  "SLO", "error budget". Use this skill for OPS-002, OPS-008, and GTM-006 tasks.
  Even if the user just says "prod is throwing 500s" or "we're not seeing any
  analytics" — use this skill.
---

# Klikk Ops — Observability

Monitoring and analytics expertise for Klikk. Covers OPS-002 (Sentry), OPS-008 (UptimeRobot + status page), GTM-006 (Plausible). Read the specific task file first; this skill supplies the domain expertise.

## The three pillars for v1

| Pillar | Tool | Scope |
|---|---|---|
| Errors & crashes | Sentry | Django, Vue admin, Quasar agent + tenant PWAs, Capacitor native apps |
| Uptime & SLA | UptimeRobot | All canonical HTTPS surfaces + status.klikk.co.za |
| Product analytics | Plausible (self-hosted) | Marketing site + in-app conversion events |

Three tools, three different questions. Don't conflate — don't try to track product conversion in Sentry or crashes in Plausible.

## Sentry

### SDK install per surface

- **Django backend (`backend/`):** `sentry-sdk[django]`, init in `backend/config/wsgi.py` or `asgi.py` before Django. Set `traces_sample_rate` to 0.1 in prod, 1.0 in staging.
- **Vue 3 admin (`admin/`):** `@sentry/vue`, init in `admin/src/main.ts` with `Sentry.browserTracingIntegration()` + `Sentry.replayIntegration()` (session replay at 10% sample, 100% on error).
- **Quasar agent/tenant PWA:** `@sentry/vue` same pattern, init in the app boot file.
- **Capacitor native wraps:** `@sentry/capacitor` + `@sentry/vue`. Capacitor SDK handles native iOS crashes (Swift) and Android (Java) automatically; Vue SDK handles JS errors in the webview. Both report to the same Sentry project.

### Releases + source maps

Every CI deploy must:
```bash
SENTRY_RELEASE="klikk-backend@$(git rev-parse --short HEAD)"
sentry-cli releases new "$SENTRY_RELEASE"
sentry-cli releases set-commits "$SENTRY_RELEASE" --auto
sentry-cli sourcemaps upload --release="$SENTRY_RELEASE" ./dist
sentry-cli releases finalize "$SENTRY_RELEASE"
```

Without source maps, Vue + Capacitor stack traces are useless — minified names only. Make this a CI gate.

### Alert rules (minimum viable)

- New issue seen in `production` environment → Slack `#klikk-alerts` immediately.
- Issue escalation: > 10 events / 5 min → page MC.
- Release regression: issue first seen in the latest release → tag the commit author.

Silence known-noisy issues explicitly (e.g. `ChunkLoadError` after deploys) — don't let them erode alert trust.

### PII scrubbing

POPIA is non-negotiable. Configure Sentry:
- `send_default_pii: false`
- Add a `before_send` hook that strips email addresses, phone numbers, RSA ID numbers, bank account numbers, and lease document content from breadcrumbs and exception messages.
- Scrub headers: `Authorization`, `Cookie`, `X-CSRF-Token`.

## UptimeRobot

### Monitor set (5-min interval)

- `https://klikk.co.za` — marketing
- `https://app.klikk.co.za` — admin
- `https://tenant.klikk.co.za` — tenant web
- `https://mobile-agent.klikk.co.za` — agent PWA
- `https://mobile-tenant.klikk.co.za` — tenant PWA
- `https://api.klikk.co.za/api/v1/health/` — Django health endpoint (expects `{"ok": true}`)
- `https://status.klikk.co.za` — the status page itself (meta-monitor)

Content-match assertions on `/health` prevent "200 OK serving an error page" false-greens.

### Alert policies

- Down > 2 min → SMS + email MC.
- TLS cert < 14 days → email (soft alert).
- 5xx rate > 1% (via Sentry, not UptimeRobot — different tool) → Slack.

### Public status page at status.klikk.co.za

UptimeRobot offers a free public status page. Point `status.klikk.co.za` at it (CNAME to UptimeRobot's hosted URL, then TLS via Caddy redirect). This is the one page MC can point tenants at during an incident.

## Plausible (self-hosted)

### Why self-hosted (from DEC-001, answered 2026-04-22)

- POPIA-friendly: no cookies, no PI, data stays in-region.
- No GDPR/POPIA consent banner needed.
- Cheaper than Plausible Cloud at scale.

### Install

Docker Compose on the same host as Caddy. Reverse-proxy `analytics.klikk.co.za` → Plausible container. Point the Plausible site at `klikk.co.za` for marketing and add separate sites for `app.klikk.co.za` and `tenant.klikk.co.za` if in-app conversion is a v1 goal.

### Events worth tracking for v1 launch

Marketing site:
- `cta_book_demo_click`
- `pricing_view`
- `feature_detail_view` (feature name as custom prop)

Admin (agent) app:
- `mandate_signed`
- `lease_generated`
- `lease_sent_for_signature`
- `lease_signed_by_tenant`
- `first_rent_received`

Tenant app:
- `lease_accepted`
- `rent_payment_made`
- `maintenance_ticket_opened`

Keep the list short. Every event must map to a decision MC would actually make.

## Runbook shape

Every observability task should produce a small runbook in `docs/ops/runbooks/`:
- **What the alert looks like** (screenshot or sample payload)
- **First 5 minutes** — triage steps
- **Common causes** — top 3 with fixes
- **When to escalate** — criteria + who

The runbook is the deliverable, not just the tool config. A monitor without a runbook is just noise generation.

## Common gotchas

- **Sentry DSN committed to the repo** — fine for frontend (public by design), fatal for backend (server-side DSN = rate-limit abuse vector). Use env vars both ways.
- **Missing source maps in Sentry** — the single most common "why can't I debug this" failure mode. CI gate required.
- **UptimeRobot on `/` only** — a 200 from the homepage doesn't mean the API works. Always monitor `/health`.
- **Plausible not tracking SPA route changes** — you need `plausible.js` with `{ hashMode: false }` and manual `plausible('pageview')` on each Vue Router `afterEach`.
- **Self-hosted Plausible backup** — Postgres + ClickHouse both. Don't assume one dump is enough.

## Where to look in the repo

- `backend/config/settings.py` — Sentry init
- `admin/src/main.ts`, `web_app/src/main.ts`, `agent-app/src/boot/sentry.ts` — frontend Sentry
- `deploy/docker-compose.plausible.yml` — Plausible stack
- `deploy/Caddyfile` — `status.klikk.co.za` + `analytics.klikk.co.za` entries
- `docs/ops/runbooks/` — runbook library
