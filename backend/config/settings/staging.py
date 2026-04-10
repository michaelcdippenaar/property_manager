"""
Staging / Docker — use with DJANGO_SETTINGS_MODULE=config.settings.staging

- Loads the same .env-driven values as base (DB_*, DEBUG, ALLOWED_HOSTS, secrets).
- Does not override DEBUG to True (unlike local.py).
- Lets you extend CORS / CSRF for your Nginx hostnames via .env.
"""
from .base import *


def _split_csv(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


# Optional: comma-separated extra browser origins (admin / website / agent on real URLs)
_extra_cors = _split_csv(config("CORS_EXTRA_ORIGINS", default=""))
if _extra_cors:
    CORS_ALLOWED_ORIGINS = list(CORS_ALLOWED_ORIGINS) + _extra_cors

# Optional: comma-separated origins for CSRF (include scheme, e.g. https://admin.example.com)
_csrf = _split_csv(config("CSRF_TRUSTED_ORIGINS", default=""))
if _csrf:
    CSRF_TRUSTED_ORIGINS = _csrf
