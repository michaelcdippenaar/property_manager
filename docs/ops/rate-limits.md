# Klikk API Rate Limits

All rate limiting is implemented via **DRF throttle classes** (no additional
library required). Throttle state is stored in Django's default cache backend
(locmem in development, Redis recommended in production).

Rate-limit breaches return **HTTP 429 Too Many Requests**.  
All breaches are visible in the Django request log at WARNING level from the
`rest_framework.throttling` logger.

---

## Limit tiers

### Public e-signing endpoints

Applies to all `AllowAny` e-signing views under `/api/v1/esigning/public-sign/<uuid>/...`
and includes: detail, document, sign/submit, draft save/restore, file upload, file delete.

| Bucket | Limit | Key |
|--------|-------|-----|
| `public_sign_minute` | **10 req / min** | per IP |
| `public_sign_hourly` | **60 req / hr** | per IP |

Both buckets are applied simultaneously. A request counts against both.

Implementation: `apps/esigning/throttles.PublicSignMinuteThrottle` and
`PublicSignHourlyThrottle`.

---

### Login endpoint (`POST /api/v1/auth/login/`)

Two independent buckets are applied:

| Bucket | Limit | Key |
|--------|-------|-----|
| `anon_auth` | **5 req / min** | per IP |
| `login_hourly_user` | **20 req / hr** | per email address |

In addition to these throttles, the `LoginView` has a **DB-backed lockout** for
failed attempts: 5 consecutive failures within 30 minutes locks the account for
that window (returns 429 with a "temporarily locked" message).

Implementation: `apps/accounts/throttles.AuthAnonThrottle` +
`LoginHourlyThrottle`.

---

### Register / Google OAuth / password reset

| Bucket | Limit | Key |
|--------|-------|-----|
| `anon_auth` | **5 req / min** | per IP |

Endpoints: `POST /api/v1/auth/register/`, `POST /api/v1/auth/google/`,
`POST /api/v1/auth/password-reset/`, `POST /api/v1/auth/password-reset/confirm/`.

---

### Tenant-invite acceptance (`/api/v1/auth/accept-invite/`)

| Bucket | Limit | Key |
|--------|-------|-----|
| `invite_accept` | **5 req / min** | per IP |

Implementation: `apps/accounts/throttles.InviteAcceptThrottle`.

---

### OTP endpoints

| Endpoint | Bucket | Limit | Key |
|----------|--------|-------|-----|
| `POST /api/v1/auth/otp/send/` | `otp_send` | **3 req / min** | per IP |
| `POST /api/v1/auth/otp/verify/` | `otp_verify` | **5 req / min** | per IP |

Implementation: `apps/accounts/throttles.OTPSendThrottle` + `OTPVerifyThrottle`.

---

## Configuration

All rates are defined in `backend/config/settings/base.py` under
`REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`. Override in environment-specific
settings files as needed.

```python
"DEFAULT_THROTTLE_RATES": {
    "anon_auth":          "5/min",
    "otp_send":           "3/min",
    "otp_verify":         "5/min",
    "login_hourly_user":  "20/hour",
    "invite_accept":      "5/min",
    "public_sign_minute": "10/min",
    "public_sign_hourly": "60/hour",
}
```

---

## Cache backend

DRF throttles require a working cache. Configure Redis in production:

```python
# settings/production.py
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
    }
}
```

Without Redis, the default locmem cache resets on every process restart, so
limits only hold within a single worker instance. This is acceptable for
development but is **not production-safe** for multi-worker deploys.

---

## Testing

```bash
# Run the rate-limit unit tests
pytest backend/apps/test_hub/esigning/unit/test_rate_limits.py -v

# Manual smoke test — hit the submit endpoint 4× rapid-fire (3/min limit in test settings)
for i in 1 2 3 4; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:8000/api/v1/esigning/public-sign/00000000-0000-0000-0000-000000000000/sign/
done
# Expected output: 404 404 404 429
```
