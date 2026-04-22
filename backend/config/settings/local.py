import sys

from .base import *

DEBUG = True
CORS_ALLOW_ALL_ORIGINS = True

# ── django-silk — request/SQL profiler (dev only) ─────────────────────────────
# Browse at http://localhost:8000/silk/
# Intercepts lease/*, esigning/*, payments/* to surface slow queries and p95.
# Excluded from staging/production settings — zero overhead in prod.
INSTALLED_APPS = list(INSTALLED_APPS) + ["silk"]
MIDDLEWARE = ["silk.middleware.SilkyMiddleware"] + list(MIDDLEWARE)

SILKY_PYTHON_PROFILER = False       # CPU profiling off by default (high overhead)
SILKY_MAX_RECORDED_REQUESTS = 1000  # Keep last 1 000 requests in DB
SILKY_MAX_RECORDED_REQUESTS_CHECK_PERCENT = 10
SILKY_INTERCEPT_PERCENT = 100       # Profile all requests in dev
# Focus on the three critical path prefixes defined in QA-008
SILKY_INTERCEPT_FUNC = lambda r: any(
    r.path.startswith(p)
    for p in (
        "/api/v1/leases/",
        "/api/v1/esigning/",
        "/api/v1/payments/",
    )
)

if "test" in sys.argv:
    # Effectively disable throttling in tests (rate limit tests override per-class)
    REST_FRAMEWORK = {
        **REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {
            "anon_auth": "1000/min",
            "otp_send": "1000/min",
            "otp_verify": "1000/min",
        },
    }
    # Remove silk from the test runner — avoid creating silk tables in test DB
    INSTALLED_APPS = [a for a in INSTALLED_APPS if a != "silk"]
    MIDDLEWARE = [m for m in MIDDLEWARE if "silk" not in m.lower()]
