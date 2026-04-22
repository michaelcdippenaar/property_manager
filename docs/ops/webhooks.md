# Klikk Webhook Security

## Overview

Every inbound HTTP endpoint that accepts machine-to-machine payloads must verify
the sender's identity.  Klikk uses **HMAC-SHA256** for server-to-server callbacks
and **origin allowlisting** for browser-initiated public forms.

---

## Audit: current inbound endpoints (v1.0)

| URL pattern | Auth model | Verification | Notes |
|---|---|---|---|
| `POST /api/v1/esigning/public-sign/<uuid>/sign/` | UUID-scoped public link | Link UUID is a 128-bit secret; throttled; POPIA-consent required | Tenant-initiated — not a machine-to-machine webhook |
| `POST /api/v1/esigning/public-sign/<uuid>/documents/` | UUID-scoped public link | Same as above | Supporting-document upload |
| `POST /api/v1/esigning/public-sign/<uuid>/draft/` | UUID-scoped public link | Same as above | Draft save |
| `POST /contact/` | Origin allowlist | Checked against `ALLOWED_ORIGINS`; honeypot; rate-limited | Marketing site contact form; `@csrf_exempt` is intentional |
| All `/api/v1/…` staff endpoints | JWT Bearer | `IsAuthenticated` / `IsAgentOrAdmin` | Standard DRF auth |
| Gotenberg | Internal / outbound only | Called outbound by Django; no inbound webhook | Docker-network only |

**Finding:** As of v1.0 there are no bare public machine-to-machine webhook URLs
that would require HMAC verification.  The signing flow is tenant-driven via UUID
public links, not server callbacks.

---

## HMAC-SHA256 scheme (for future integrations)

### Helper: `utils.webhook_signature`

```python
from utils.webhook_signature import verify_hmac_signature, get_webhook_secret

def post(self, request):
    secret = get_webhook_secret("myintegration")   # reads WEBHOOK_SECRET_MYINTEGRATION
    sig    = request.META.get("HTTP_X_KLIKK_SIGNATURE", "")
    if not verify_hmac_signature(request.body, sig, secret):
        logger.warning("webhook rejected: bad sig from %s", request.META.get("REMOTE_ADDR"))
        return Response({"detail": "Invalid signature."}, status=401)
    ...
```

### Signed payload format

**Without timestamp** (basic):
```
HMAC-SHA256(secret, raw_body_bytes)  →  hex string
```

**With timestamp** (replay-protected, preferred):
```
HMAC-SHA256(secret, f"{epoch_ts}.{body_hex}")  →  hex string
```

The timestamp must be within **300 seconds** (5 minutes) of server time.
Adjust `max_age_seconds` if your integration requires a different window.

### HTTP header convention

Use `X-Klikk-Signature` for Klikk-originated callbacks, or the sender's
native header (e.g. `X-Hub-Signature-256` for GitHub-style webhooks).

Reject with **HTTP 401** on invalid signature. Log the rejection (IP, path,
partial sig) for security monitoring.

### Shared secrets — environment variables

One env var per integration, pattern `WEBHOOK_SECRET_<NAME>`:

| Env var | Integration | Rotation |
|---|---|---|
| `WEBHOOK_SECRET_ESIGNING` | Reserved for future e-signing server callbacks | Rotate via `docs/ops/secret-rotation-*.md` |

Secrets are loaded at startup by `utils.webhook_signature.get_webhook_secret`.
Rotate by updating `.env` and restarting the server (zero-downtime: deploy new
secret, update sender, then remove old secret).

---

## Adding a new webhook endpoint

1. Add `WEBHOOK_SECRET_<MYINTEGRATION>` to `.env` and `docs/ops/webhooks.md`.
2. Declare the setting in `config/settings/base.py` under the webhook-secrets block.
3. In your view call `verify_hmac_signature`; return **HTTP 401** on failure.
4. Write a unit test in `apps/<app>/tests/test_webhooks.py` covering: valid sig,
   invalid sig, missing sig, replay (timestamp >5 min).
5. Update the audit table in this file.

---

## Contact form (`/contact/`) — not HMAC

The marketing contact form is `@csrf_exempt` because it is a cross-origin
browser POST from `klikk.co.za`.  It is protected by:

- **Origin allowlist** — only `https://klikk.co.za` and `https://www.klikk.co.za`
  (plus `http://localhost` in DEBUG) are accepted.
- **Honeypot field** — bots fill it; humans don't see it.
- **IP rate limit** — max 5 submissions per IP per hour.

HMAC is not applicable here because the sender is a browser, not a server.

---

## Public signing links — not HMAC

The `ESigningPublicLink` UUID (128-bit random, stored in the DB) is
functionally equivalent to a bearer token for the signing session.  The UUID
is:

- Never guessable (UUID v4, cryptographically random).
- Single-use per signer role (prior links are expired on resend).
- Time-limited (`ESIGNING_PUBLIC_LINK_EXPIRY_DAYS`, default 14 days).
- Throttled (60 req/hour per IP, 5 req/min per IP via DRF throttle classes).

An additional HMAC layer on top of the UUID link would provide marginal extra
security and is not implemented in v1.
