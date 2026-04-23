import os
from pathlib import Path

from decouple import Config, RepositoryEmpty, RepositoryEnv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

_env_path = BASE_DIR / ".env"
if _env_path.is_file():
    _env_repo = RepositoryEnv(str(_env_path))
    for _key, _val in _env_repo.data.items():
        os.environ.setdefault(_key, _val)
    config = Config(_env_repo)
else:
    config = Config(RepositoryEmpty())

SECRET_KEY = config("SECRET_KEY", default="dev-secret-key")
DEBUG = config("DEBUG", default=False, cast=bool)

# Gate for test/debug endpoints. Defaults to False (off in production).
# Set ENABLE_TEST_ENDPOINTS=true in staging .env only — never in production.
ENABLE_TEST_ENDPOINTS = config("ENABLE_TEST_ENDPOINTS", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",")
CSRF_TRUSTED_ORIGINS = ["http://localhost:5178", "http://127.0.0.1:5178", "http://127.0.0.1:5173", "http://localhost:5173", "http://192.168.1.176:9501"]

DJANGO_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "channels",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "graphene_django",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.properties",
    "apps.leases",
    "apps.tenant",
    "apps.maintenance",
    "apps.esigning",
    "apps.ai",
    "apps.tenant_portal",
    "apps.notifications",
    "apps.test_hub",
    "apps.market_data",
    "apps.the_volt",
    "apps.integrations",
    "apps.contact",
    "apps.legal",
    "apps.payments",
    "apps.audit",
    "apps.popia",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.audit.middleware.AuditContextMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="klikk_db"),
        "USER": config("DB_USER", default="klikk_user"),
        "PASSWORD": config("DB_PASSWORD", default="klikk_pass"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Johannesburg"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Upload limits — Django defaults are 2.5 MB (memory) / 2.5 MB (POST body).
# Lease PDFs and DOCX files can be larger, so raise to 20 MB.
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024   # 20 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024    # 20 MB

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_RATES": {
        # Auth endpoints (login, register, Google OAuth, password reset)
        "anon_auth": "5/min",
        # OTP send / verify
        "otp_send": "3/min",
        "otp_verify": "5/min",
        # Per-user login hourly bucket (applied alongside anon_auth)
        "login_hourly_user": "20/hour",
        # Tenant-invite acceptance
        "invite_accept": "5/min",
        # Public e-signing endpoints (no auth, UUID token in URL)
        "public_sign_minute": "10/min",
        "public_sign_hourly": "60/hour",
    },
}

GRAPHENE = {
    "SCHEMA": "config.schema.schema",
}

from datetime import timedelta
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=4),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5178",
    "http://127.0.0.1:5178",
    # Agent-app Quasar dev server
    "http://localhost:9000",
    "http://127.0.0.1:9000",
    # Capacitor agent-app (iOS WebView origin + Android WebView origin)
    "capacitor://localhost",
    "http://localhost",
    # Marketing website
    "https://klikk.co.za",
    "https://www.klikk.co.za",
]

CONTACT_EMAIL = config("CONTACT_EMAIL", default="mc@klikk.co.za")

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID = config("GOOGLE_OAUTH_CLIENT_ID", default="")

# Anthropic Claude API
# Read directly from .env repo data to avoid decouple's issues with '--' in values
_env_data = _env_repo.data if _env_path.is_file() else {}
ANTHROPIC_API_KEY = _env_data.get("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))

# AI Guide widget — set ENABLE_AI_GUIDE=false to disable the /api/v1/ai/guide/ endpoint.
# Defaults to True so the widget works out-of-the-box in dev/staging.
ENABLE_AI_GUIDE = config("ENABLE_AI_GUIDE", default=True, cast=bool)
GOOGLE_MAPS_API_KEY = _env_data.get("GOOGLE_MAPS_API_KEY", os.environ.get("GOOGLE_MAPS_API_KEY", ""))

# Local contract / policy RAG (ChromaDB under RAG_CHROMA_PATH)
CONTRACT_DOCUMENTS_ROOT = Path(
    config("CONTRACT_DOCUMENTS_ROOT", default=str(BASE_DIR / "documents"))
)
RAG_CHROMA_PATH = Path(config("RAG_CHROMA_PATH", default=str(BASE_DIR / "rag_chroma")))
RAG_PDF_MAX_PAGES = config("RAG_PDF_MAX_PAGES", default=120, cast=int)
RAG_MAX_FILE_BYTES = config("RAG_MAX_FILE_BYTES", default=40 * 1024 * 1024, cast=int)
RAG_QUERY_CHUNKS = config("RAG_QUERY_CHUNKS", default=8, cast=int)
# Embedding model for RAG vector search (nomic-embed-text-v1.5 recommended)
RAG_EMBEDDING_MODEL = config(
    "RAG_EMBEDDING_MODEL", default="nomic-ai/nomic-embed-text-v1.5"
)

# The Volt — personal data sovereignty vault RAG collections
VOLT_DOCUMENTS_COLLECTION = "volt_documents"
VOLT_ENTITIES_COLLECTION = "volt_entities"

# The Volt — Weaviate Cloud backend (optional; falls back to ChromaDB when unset)
#   - VOLT_VECTOR_BACKEND: "chroma" (default) or "weaviate"
#   - WEAVIATE_URL: https://<cluster>.weaviate.cloud  (REST endpoint from WCS console)
#   - WEAVIATE_API_KEY: admin API key from WCS console → Security → API Keys
VOLT_VECTOR_BACKEND = config("VOLT_VECTOR_BACKEND", default="chroma")
WEAVIATE_URL = config("WEAVIATE_URL", default="")
WEAVIATE_API_KEY = config("WEAVIATE_API_KEY", default="")

# Tenant AI chat attachments (multipart uploads)
TENANT_AI_MAX_IMAGE_BYTES = config(
    "TENANT_AI_MAX_IMAGE_BYTES", default=12 * 1024 * 1024, cast=int
)
TENANT_AI_MAX_VIDEO_BYTES = config(
    "TENANT_AI_MAX_VIDEO_BYTES", default=45 * 1024 * 1024, cast=int
)

# Anthropic hosted web_fetch for agent-assist (optional)
ANTHROPIC_WEB_FETCH_ENABLED = config(
    "ANTHROPIC_WEB_FETCH_ENABLED", default=False, cast=bool
)

# ── Logging ──
# Maintenance chat log file for review and training data extraction
MAINTENANCE_CHAT_LOG = config(
    "MAINTENANCE_CHAT_LOG", default=str(BASE_DIR / "logs" / "maintenance_chat.jsonl")
)

# Ensure the logs directory exists before Django configures FileHandlers.
# This handles fresh checkouts, CI containers, and any environment where
# backend/logs/ was not created by git (e.g. shallow clone without .gitkeep).
os.makedirs(os.path.dirname(MAINTENANCE_CHAT_LOG), exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
        "jsonl": {
            "format": "{message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "maintenance_chat_file": {
            "class": "logging.FileHandler",
            "filename": MAINTENANCE_CHAT_LOG,
            "formatter": "jsonl",
        },
    },
    "loggers": {
        "apps.maintenance": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "apps.ai": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "apps.tenant_portal": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "maintenance_chat": {
            "handlers": ["maintenance_chat_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ── OTP Service ───────────────────────────────────────────────────────────────
# Channel-abstracted OTP for registration, password-reset, sensitive-change flows.
# OTP_CHANNELS: ordered list of channels — first-working wins.
#   "email"  — delivered via Django email backend (console in dev, SES in prod)
#   "sms"    — stub pending WinSMS/Panacea onboarding
OTP_CHANNELS = ["email"]
# TTL in seconds for each issued OTP code (default 5 min).
OTP_CODE_TTL_SECONDS = 300
# Max failed verify attempts before the code is locked (requires new code).
OTP_MAX_ATTEMPTS = 3
# Max OTP codes a user may request in a rolling 1-hour window.
OTP_MAX_ISSUES_PER_HOUR = 5

# Passwordless signing page (admin SPA /sign/<uuid>/) — full URL for SMS/email if set
ESIGNING_PUBLIC_LINK_EXPIRY_DAYS = config("ESIGNING_PUBLIC_LINK_EXPIRY_DAYS", default=14, cast=int)
SIGNING_PUBLIC_APP_BASE_URL = config("SIGNING_PUBLIC_APP_BASE_URL", default="").strip().rstrip("/")

# Tenant web-app base URL — used to build /invite/<token> links in tenant invite emails.
# Defaults to localhost:5174 (Vite dev port for web_app). Set to the production
# tenant web-app URL in staging/production (e.g. https://app.klikk.co.za).
TENANT_APP_BASE_URL = config("TENANT_APP_BASE_URL", default="").strip().rstrip("/")

# Gotenberg — Chromium-based HTML→PDF service (docker-compose: gotenberg on port 3000)
GOTENBERG_URL = config("GOTENBERG_URL", default="http://localhost:3000")

# Email (Django) — Gmail: smtp.gmail.com:587 + app password; see apps/notifications/NOTIFICATIONS.md
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@localhost")

# SMS / WhatsApp (Twilio)
TWILIO_ACCOUNT_SID = config("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = config("TWILIO_AUTH_TOKEN", default="")
TWILIO_SMS_FROM = config("TWILIO_SMS_FROM", default="")
TWILIO_WHATSAPP_FROM = config("TWILIO_WHATSAPP_FROM", default="")

# apps.notifications — phone normalization when number has leading 0 (e.g. SA)
NOTIFICATIONS_DEFAULT_DIAL_CODE = config("NOTIFICATIONS_DEFAULT_DIAL_CODE", default="+27")
NOTIFICATIONS_ENABLE_LOG = config("NOTIFICATIONS_ENABLE_LOG", default=True, cast=bool)

# Vault33 internal gateway — trusted Vault33-family service fetches vault data
# on behalf of an already-authenticated Klikk user. No owner-approval / OTP flow.
# Every call writes a DataCheckout audit row on the Vault33 side.
# See: apps/integrations/vault33.py
VAULT33_BASE_URL = config("VAULT33_BASE_URL", default="http://localhost:8001")
VAULT33_INTERNAL_TOKEN = config("VAULT33_INTERNAL_TOKEN", default="")

# ── Webhook shared secrets (HMAC-SHA256) ──────────────────────────────────────
# Pattern: WEBHOOK_SECRET_<NAME>  — one per integration.
# Loaded by utils.webhook_signature.get_webhook_secret("<name>").
# Rotate by updating the env var and restarting the server.
# Leave empty in development to skip verification (a warning is logged).
# See docs/ops/webhooks.md for the full scheme.
#
# Currently defined integrations:
#   WEBHOOK_SECRET_ESIGNING   — reserved for future machine-to-machine callbacks
#                                (native signing is inbound from tenants, not servers)
#   WEBHOOK_SECRET_CONTACT    — not used (contact form is origin-allowlisted, not HMAC)
#
WEBHOOK_SECRET_ESIGNING = config("WEBHOOK_SECRET_ESIGNING", default="")

# ── Push notifications (Firebase) ─────────────────────────────────────────────
# Path to the Firebase service account credentials JSON file.
# Leave blank in development to disable push dispatch.
# On production/staging set FIREBASE_CREDENTIALS_PATH in the environment or .env.
FIREBASE_CREDENTIALS_PATH = config("FIREBASE_CREDENTIALS_PATH", default="")

# ── Sentry ────────────────────────────────────────────────────────────────────
# Set SENTRY_DSN in .env to enable.  Leave blank to run without Sentry (dev default).
# SENTRY_ENVIRONMENT should be "development" / "staging" / "production".
# SENTRY_TRACES_SAMPLE_RATE: 0.0–1.0 fraction of transactions to trace (default 0.05).
SENTRY_DSN = config("SENTRY_DSN", default="")
SENTRY_ENVIRONMENT = config("SENTRY_ENVIRONMENT", default="development")
SENTRY_TRACES_SAMPLE_RATE = config("SENTRY_TRACES_SAMPLE_RATE", default=0.05, cast=float)

# Derive release from GIT_COMMIT env var (set by CI/deploy scripts).
import subprocess as _sp

def _git_sha() -> str | None:
    try:
        return _sp.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=_sp.DEVNULL,
            cwd=str(BASE_DIR),
        ).decode().strip()
    except Exception:
        return None

SENTRY_RELEASE = os.environ.get("GIT_COMMIT") or _git_sha()

if SENTRY_DSN:
    from config.sentry import init as _sentry_init
    _sentry_init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        release=SENTRY_RELEASE,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
    )
