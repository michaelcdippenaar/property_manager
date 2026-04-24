---
name: klikk-ops-deployment
description: >
  Production deployment, DNS, TLS, email auth, and CDN for the Klikk platform.
  Use this skill whenever the user is configuring or troubleshooting: Caddy reverse
  proxy, Let's Encrypt auto-HTTPS, TLS certificates, HSTS, DNS records (A/AAAA/CNAME/MX),
  subdomain routing, Django production settings (ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS,
  CORS_ALLOWED_ORIGINS), AWS SES transactional email, SPF/DKIM/DMARC records,
  Google Workspace coexistence on the apex domain, Cloudflare CDN,
  CloudFront, Cloudflare Authenticated Origin Pulls, cache-control headers, production
  PostgreSQL backup/restore, staging environment parity, release process, blue-green or
  rolling deploys, zero-downtime deploys, health checks, or environment variable
  management. Trigger phrases: "deploy to prod", "configure DNS", "set up TLS",
  "Caddyfile", "Let's Encrypt", "HSTS preload", "ALLOWED_HOSTS", "CSRF error in prod",
  "CORS failing in prod", "SES DKIM", "DMARC", "SPF record", "mail deliverability",
  "mail-tester", "apex sender", "no-reply@klikk.co.za", "Google Workspace", "Cloudflare cache",
  "static assets", "origin protection", "CDN cache", "pg_dump backup", "restore backup",
  "staging environment", "release checklist", "env vars", ".env.production",
  "zero downtime deploy", "rollback", "subdomain redirect", "301 redirect",
  "app.klikk.co.za", "api.klikk.co.za", "tenant.klikk.co.za", "mobile-agent.klikk.co.za",
  "mobile-tenant.klikk.co.za". Use this skill for any OPS-NNN task in tasks/backlog/
  covering deployment, DNS, email, CDN, or backups. Even if the user just says
  "prod is broken" or "email isn't arriving" — use this skill.
---

# Klikk Ops — Deployment, DNS, TLS, Email, CDN

Production-readiness expertise for Klikk. Covers OPS-001 (CI/CD), OPS-003 (backups), OPS-005 (staging parity), OPS-006 (DNS/TLS/email), OPS-007 (release process). Read the specific task file in `tasks/backlog/` first — the acceptance criteria are the spec. This skill gives you the domain expertise to satisfy them.

## Canonical subdomain map (from DEC-013, locked 2026-04-22)

| Subdomain | Role | Type |
|---|---|---|
| `klikk.co.za` | Marketing site (Astro) | Canonical |
| `app.klikk.co.za` | Admin SPA (Vue 3, `admin/`) | Canonical agent URL |
| `agent.klikk.co.za` | → `app.klikk.co.za` | 301 redirect |
| `tenant.klikk.co.za` | Tenant web app (`web_app/`) | Canonical |
| `mobile-agent.klikk.co.za` | Quasar agent PWA | Canonical |
| `mobile-tenant.klikk.co.za` | Quasar tenant PWA | Canonical |
| `api.klikk.co.za` | Django API | Canonical |
| `backend.klikk.co.za` | → `api.klikk.co.za` | 301 redirect (sunset 90d after launch) |
| `status.klikk.co.za` | Uptime status page | Canonical |
| `klikk.co.za` (apex) | AWS SES transactional sender | DKIM CNAMEs coexist with Google Workspace |
| `www.klikk.co.za` | → `klikk.co.za` | 301 redirect |

**Never change this map without a new DEC task.** It's load-bearing across Django settings, mobile app configs, CORS, and MC's muscle memory.

## Caddyfile patterns

**Canonical HTTPS site:**
```
api.klikk.co.za {
    reverse_proxy localhost:8000
    encode gzip
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}
```

**Permanent redirect (canonical-compliant, preserves path + query):**
```
backend.klikk.co.za {
    redir https://api.klikk.co.za{uri} permanent
}
```

Caddy handles Let's Encrypt automatically — no certbot, no renewal cron. Verify issuance via `journalctl -u caddy | grep -i "certificate obtained"`.

## Django settings (production)

Three settings must include every canonical agent + tenant surface:

```python
ALLOWED_HOSTS = [
    "api.klikk.co.za",
    "backend.klikk.co.za",  # legacy — sunset 90 days post-launch
    "app.klikk.co.za",
    "tenant.klikk.co.za",
    "mobile-agent.klikk.co.za",
    "mobile-tenant.klikk.co.za",
]

CSRF_TRUSTED_ORIGINS = [
    "https://app.klikk.co.za",
    "https://agent.klikk.co.za",
    "https://tenant.klikk.co.za",
    "https://mobile-agent.klikk.co.za",
    "https://mobile-tenant.klikk.co.za",
]

CORS_ALLOWED_ORIGINS = [  # no wildcards, ever
    "https://app.klikk.co.za",
    "https://agent.klikk.co.za",
    "https://tenant.klikk.co.za",
    "https://mobile-agent.klikk.co.za",
    "https://mobile-tenant.klikk.co.za",
]
```

Add `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` so Django trusts Caddy's TLS termination.

## Apex-sender email: Google Workspace + AWS SES coexisting on `klikk.co.za`

**DEC-023 (locked 2026-04-24):** Both human mail (Google Workspace) and transactional mail (AWS SES af-south-1) live on the `klikk.co.za` apex. No `mail.` subdomain. Coexistence works because DKIM uses distinct selector CNAMEs per sender and SPF supports multiple `include:` directives.

- **Transactional from:** `no-reply@klikk.co.za`
- **Reply-to:** `support@klikk.co.za`
- **Human mail:** unchanged (`mc@klikk.co.za` on Google Workspace)

### SPF — single apex record, both senders included

Replace the Google-only SPF with a combined record (one `TXT` record per domain, never two):
```
TXT @  "v=spf1 include:_spf.google.com include:amazonses.com ~all"
```

### DKIM — both sets of CNAMEs coexist

- Keep Google's existing `google._domainkey` CNAME (or `google*._domainkey` selectors).
- Add SES Easy DKIM's three selector CNAMEs (e.g. `<token1>._domainkey.klikk.co.za`, `<token2>._domainkey.klikk.co.za`, `<token3>._domainkey.klikk.co.za`) directly on the apex. DKIM is selector-scoped — the two senders never collide.
- SES MAIL FROM domain: leave as `amazonses.com` default (or set to a dedicated `bounce.klikk.co.za` subdomain **only** for bounce handling if SES requests custom MAIL FROM).

### DMARC — single apex policy covers both

```
TXT _dmarc "v=DMARC1; p=quarantine; rua=mailto:dmarc@klikk.co.za; pct=100"
```
Launch at `p=quarantine`; escalate to `p=reject` after 30 days of clean aggregate reports.

### Verification

```bash
dig +short TXT klikk.co.za                          # combined SPF — must include both _spf.google.com and amazonses.com
dig +short TXT _dmarc.klikk.co.za                   # apex DMARC
dig +short CNAME google._domainkey.klikk.co.za      # Google DKIM
dig +short CNAME <ses-selector>._domainkey.klikk.co.za  # SES DKIM (×3 selectors)
```

Then send a test SES email → paste the headers into `mail-tester.com` → target ≥ 9/10.

## CDN

Two acceptable setups:
1. **Cloudflare proxy** in front of the app origin. Enable "Authenticated Origin Pulls" so Caddy rejects any request that didn't come through Cloudflare.
2. **S3 + CloudFront** for static assets with hashed filenames (Vite build output is already hashed). `Cache-Control: public, max-age=31536000, immutable` on hashed assets; `no-cache` on `index.html`.

Long-cache hashed assets by default; reserve short TTLs for HTML entry points only.

## Backups

PostgreSQL nightly full + WAL archiving:
```bash
pg_dump --format=custom --jobs=4 --compress=9 klikk_prod > klikk_prod_$(date +%Y%m%d).dump
# ship to S3 bucket with lifecycle policy (30d hot, 90d glacier, 365d delete)
aws s3 cp klikk_prod_*.dump s3://klikk-backups/postgres/ --storage-class STANDARD_IA
```

Restore drill cadence: quarterly. Document the restore steps in `docs/ops/backup-restore.md` so it's not tribal knowledge.

## CI/CD shape (OPS-001)

- One GitHub Actions workflow per surface: backend, admin, web_app, agent-app (Quasar), tenant-app (Quasar).
- On `main` push: run tests → build artefacts → deploy to staging → smoke check → promote to prod with manual approval gate.
- Every deploy tags the commit + writes a Sentry release marker (see `klikk-ops-observability`).
- Secrets in GitHub Actions → synced from a single source of truth (1Password or AWS Secrets Manager). No secrets in `.env` files committed anywhere.

## Common gotchas

- **`CORS_ALLOW_ALL_ORIGINS = True` anywhere in production** — always a bug. Never ship.
- **Missing `X-Forwarded-Proto` trust** — Django thinks it's on HTTP, redirects loop.
- **SPF over 10 lookups** — Google + SES on the same record blows the limit. That's why we isolate SES on the subdomain.
- **DMARC `p=reject` too soon** — always start `p=quarantine`, watch `rua` reports for 30 days, then escalate.
- **Forgetting the redirect hosts in `ALLOWED_HOSTS`** — `backend.klikk.co.za` and `agent.klikk.co.za` need to be listed even though they only redirect, or Django rejects the request before the redirect fires.

## Where to look in the repo

- `deploy/Caddyfile` — reverse proxy + TLS config
- `backend/config/settings.py` — ALLOWED_HOSTS, CSRF, CORS
- `docs/ops/dns.md` — document every DNS record here (create if missing)
- `docs/ops/email-deliverability.md` — dual-domain email runbook
- `.github/workflows/` — CI/CD

## Output standards for OPS tasks

- **Document every DNS record.** If you add one, add a row to `docs/ops/dns.md`.
- **TLS-A+ or nothing.** Every canonical surface should hit A+ on Qualys SSL Labs.
- **No wildcard origins.** Explicit allowlists for CORS, CSRF, ALLOWED_HOSTS.
- **Rollback is a first-class feature.** Any release process must have a documented rollback path.
