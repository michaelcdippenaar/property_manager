"""
Production — use with DJANGO_SETTINGS_MODULE=config.settings.production

Inherits all of staging's settings and adds HSTS (once the domain is stable).
"""
from .staging import *

# ── HSTS — only enable once the domain is permanently on HTTPS ────────────────
# Start with a short max-age (300 s) and increase once confirmed working.
# DO NOT enable preload until you're certain — it's very hard to reverse.
SECURE_HSTS_SECONDS = 300                  # ramp to 31536000 after confirming
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True               # uncomment only after full verification
