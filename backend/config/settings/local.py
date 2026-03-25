import sys

from .base import *

DEBUG = True
CORS_ALLOW_ALL_ORIGINS = True

# Unit tests POST unsigned webhooks; .env may set DOCUSEAL_WEBHOOK_SECRET for real DocuSeal.
if "test" in sys.argv:
    DOCUSEAL_WEBHOOK_SECRET = ""
    DOCUSEAL_WEBHOOK_HEADER_NAME = ""
