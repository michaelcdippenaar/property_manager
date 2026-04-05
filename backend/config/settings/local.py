import sys

from .base import *

DEBUG = True
CORS_ALLOW_ALL_ORIGINS = True

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

