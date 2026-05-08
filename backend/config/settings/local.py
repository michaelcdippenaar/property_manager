import os
import sys

from .base import *

DEBUG = True
CORS_ALLOW_ALL_ORIGINS = True

# ── localhost CORS / CSRF origins (dev only) ──────────────────────────────────
# These must NOT live in base.py — they are invalid in production and are a
# recurring audit finding when left in the shared settings module.
_CORS_LOCAL = [
    # Vite admin SPA
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # Vite web_app (tenant)
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    # Vite agent-app alternate port
    "http://localhost:5178",
    "http://127.0.0.1:5178",
    # Quasar agent-app dev server
    "http://localhost:9000",
    "http://127.0.0.1:9000",
    # Capacitor agent-app (iOS WebView + Android WebView origin)
    "capacitor://localhost",
    "http://localhost",
    # Local network dev device (e.g. mobile browser on LAN)
    "http://192.168.1.176:9501",
]
CORS_ALLOWED_ORIGINS = list(CORS_ALLOWED_ORIGINS) + _CORS_LOCAL

_CSRF_LOCAL = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5178",
    "http://127.0.0.1:5178",
    "http://192.168.1.176:9501",
]
CSRF_TRUSTED_ORIGINS = list(CSRF_TRUSTED_ORIGINS) + _CSRF_LOCAL

# Include testserver so Django's test client (APIClient) is not rejected by
# CommonMiddleware with a 400 DisallowedHost during pytest runs.
ALLOWED_HOSTS = list(ALLOWED_HOSTS) + ["testserver"]

# -- django-silk -- request/SQL profiler (dev only) ----------------------------
# Browse at http://localhost:8000/silk/
# Intercepts lease/*, esigning/*, payments/* to surface slow queries and p95.
# Excluded from staging/production settings -- zero overhead in prod.
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

_IS_TEST = "test" in sys.argv or "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ
if _IS_TEST:
    # Effectively disable throttling in tests (rate limit tests override per-class).
    # MERGE into the base scopes so production scopes (login_hourly_user, etc.)
    # remain present — the rate-limit unit tests assert on those keys.
    _test_throttle_rates = dict(REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}))
    _test_throttle_rates.update({
        "anon_auth": "1000/min",
        "otp_send": "1000/min",
        "otp_verify": "1000/min",
    })
    REST_FRAMEWORK = {
        **REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": _test_throttle_rates,
        # Force JSON-only renderers in tests. Under DEBUG=True + Python
        # 3.13 the BrowsableAPIRenderer crashes with
        # `Invalid isoformat string: ''` when it tries to template-render
        # empty DateFields back into the browsable API HTML. That produces
        # ~30 spurious 500s in the RBAC matrix. JSON-only sidesteps it.
        "DEFAULT_RENDERER_CLASSES": [
            "rest_framework.renderers.JSONRenderer",
        ],
        "TEST_REQUEST_DEFAULT_FORMAT": "json",
    }
    # Remove silk from the test runner -- avoid creating silk tables in test DB
    INSTALLED_APPS = [a for a in INSTALLED_APPS if a != "silk"]
    MIDDLEWARE = [m for m in MIDDLEWARE if "silk" not in m.lower()]
