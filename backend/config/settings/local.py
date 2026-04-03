import sys

from .base import *

DEBUG = True
CORS_ALLOW_ALL_ORIGINS = True

# Unit tests POST unsigned webhooks; .env may set DOCUSEAL_WEBHOOK_SECRET for real DocuSeal.
if "test" in sys.argv:
    DOCUSEAL_WEBHOOK_SECRET = ""
    DOCUSEAL_WEBHOOK_HEADER_NAME = ""
    # Effectively disable throttling in tests (rate limit tests override per-class)
    REST_FRAMEWORK = {
        **REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {
            "anon_auth": "1000/min",
            "otp_send": "1000/min",
            "otp_verify": "1000/min",
        },
    }

