"""
Production — use with DJANGO_SETTINGS_MODULE=config.settings.production

Inherits all of staging's settings and adds HSTS (once the domain is stable).
"""
from .staging import *

# ── HSTS — only enable once the domain is permanently on HTTPS ────────────────
# 1-year max-age satisfies HSTS preload list requirements.
# HSTS preload is enabled — ensures browsers fetch klikk.co.za only over HTTPS
# even on first visit. Reverting requires removal from the preload list (months).
SECURE_HSTS_SECONDS = 31536000             # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ── CSP enforcement mode in production ───────────────────────────────────────
# Staging uses report-only; production enforces the policy.
SECURITY_HEADERS_CSP_REPORT_ONLY = False
