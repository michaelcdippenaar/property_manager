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
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",")
CSRF_TRUSTED_ORIGINS = ["http://localhost:5178", "http://127.0.0.1:5178"]

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
    "corsheaders",
    "django_filters",
    "graphene_django",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.properties",
    "apps.leases",
    "apps.maintenance",
    "apps.esigning",
    "apps.ai",
    "apps.tenant_portal",
    "apps.notifications",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

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
}

GRAPHENE = {
    "SCHEMA": "config.schema.schema",
}

from datetime import timedelta
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5178",
    "http://127.0.0.1:5178",
]

# Anthropic Claude API
ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY", default="")

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

# DocuSeal e-signing
DOCUSEAL_API_URL        = config("DOCUSEAL_API_URL", default="https://api.docuseal.com")
DOCUSEAL_API_KEY        = config("DOCUSEAL_API_KEY", default="")
DOCUSEAL_WEBHOOK_SECRET = config("DOCUSEAL_WEBHOOK_SECRET", default="")
# If set, verify webhook with this header == DOCUSEAL_WEBHOOK_SECRET (DocuSeal “Add secret” key/value mode).
DOCUSEAL_WEBHOOK_HEADER_NAME = config("DOCUSEAL_WEBHOOK_HEADER_NAME", default="").strip()
# Optional: DocuSeal admin URL to configure webhooks (UI only; DocuSeal POSTs to Tremly, not here).
DOCUSEAL_HOOK_URL = config("DOCUSEAL_HOOK_URL", default="").strip().rstrip("/")
# Public URL DocuSeal must call (HTTPS). If empty, staff API falls back to the current request host.
ESIGNING_WEBHOOK_PUBLIC_URL = config("ESIGNING_WEBHOOK_PUBLIC_URL", default="").strip().rstrip("/")

# Passwordless signing page (admin SPA /sign/<uuid>/) — full URL for SMS/email if set
ESIGNING_PUBLIC_LINK_EXPIRY_DAYS = config("ESIGNING_PUBLIC_LINK_EXPIRY_DAYS", default=14, cast=int)
SIGNING_PUBLIC_APP_BASE_URL = config("SIGNING_PUBLIC_APP_BASE_URL", default="").strip().rstrip("/")

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
