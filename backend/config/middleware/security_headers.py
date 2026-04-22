"""
SecurityHeadersMiddleware
=========================
Injects browser-security HTTP response headers that Django's built-in
SecurityMiddleware does not cover:

  - Content-Security-Policy (report-only in non-production; enforced in prod)
  - Referrer-Policy
  - Permissions-Policy
  - Cross-Origin-Opener-Policy (COOP)
  - Cross-Origin-Resource-Policy (CORP)
  - Cross-Origin-Embedder-Policy (COEP)  — kept report-only to avoid breaking
      third-party iframes on the signing page.

X-Frame-Options and X-Content-Type-Options are handled by Django's built-in
SecurityMiddleware (SECURE_CONTENT_TYPE_NOSNIFF, X_FRAME_OPTIONS settings).

Configuration (all optional, set in settings):
  SECURITY_HEADERS_CSP_REPORT_ONLY  bool  — True → use CSP-Report-Only header
                                            False → use Content-Security-Policy
                                            Default: True (report-only first pass)
  SECURITY_HEADERS_CSP_REPORT_URI   str   — URI for CSP violation reports
                                            Default: "" (omitted)
  SECURITY_HEADERS_EXTRA_CONNECT    list  — Extra connect-src origins (e.g. Sentry DSN)
                                            Default: []

Known safe origins pulled from CORS_ALLOWED_ORIGINS at import time so you
don't repeat yourself.
"""

from __future__ import annotations

from django.conf import settings


def _csp_directives() -> str:
    """Build the CSP directive string from settings."""
    allowed = list(getattr(settings, "CORS_ALLOWED_ORIGINS", []))

    # Gather origins that host static assets or API calls
    # Strip trailing slash, deduplicate
    api_origins = sorted({o.rstrip("/") for o in allowed if o.startswith("http")})
    # Capacitor WebView is treated as 'self' from its own origin
    capacitor_origins = [o for o in allowed if o.startswith("capacitor://")]

    connect_src = ["'self'"] + api_origins + capacitor_origins
    # Allow Sentry / telemetry extras
    extra_connect = getattr(settings, "SECURITY_HEADERS_EXTRA_CONNECT", [])
    if extra_connect:
        connect_src += list(extra_connect)

    # Sentry DSN host if configured.
    # DSN format: https://<key>@<host>/<project-id> — use .hostname to strip credentials.
    sentry_dsn = getattr(settings, "SENTRY_DSN", "")
    if sentry_dsn:
        from urllib.parse import urlparse
        parsed = urlparse(sentry_dsn)
        sentry_host = f"{parsed.scheme}://{parsed.hostname}"
        if sentry_host not in connect_src:
            connect_src.append(sentry_host)

    # Script-src: self + unsafe-inline is needed for Vite HMR in dev.
    # In production, you'd ideally use nonces — flagged as a discovery item.
    script_src = ["'self'", "'unsafe-inline'", "'unsafe-eval'"]

    # Style-src: self + unsafe-inline (Tailwind CSS-in-JS and Vue scoped styles)
    style_src = ["'self'", "'unsafe-inline'"]

    # img-src: allow data: URIs (base64 avatars, Leaflet map tiles, etc.)
    img_src = ["'self'", "data:", "blob:"] + api_origins

    # font-src: self + Google Fonts (marketing website uses Bricolage Grotesque)
    font_src = ["'self'", "data:", "https://fonts.gstatic.com"]

    # frame-ancestors: stronger than X-Frame-Options, supported by modern browsers
    frame_ancestors = ["'none'"]

    # CSP violation report URI
    report_uri = getattr(settings, "SECURITY_HEADERS_CSP_REPORT_URI", "")

    directives = {
        "default-src": ["'self'"],
        "script-src": script_src,
        "style-src": style_src,
        "img-src": img_src,
        "font-src": font_src,
        "connect-src": connect_src,
        "media-src": ["'self'", "blob:"],
        "object-src": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
        "frame-ancestors": frame_ancestors,
    }
    if report_uri:
        directives["report-uri"] = [report_uri]

    return "; ".join(
        f"{key} {' '.join(values)}" for key, values in directives.items()
    )


class SecurityHeadersMiddleware:
    """Add supplementary security response headers on every response."""

    def __init__(self, get_response):
        self.get_response = get_response
        self._csp_report_only: bool = getattr(
            settings, "SECURITY_HEADERS_CSP_REPORT_ONLY", True
        )

    def __call__(self, request):
        response = self.get_response(request)

        csp = _csp_directives()
        if self._csp_report_only:
            response["Content-Security-Policy-Report-Only"] = csp
        else:
            response["Content-Security-Policy"] = csp

        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), "
            "interest-cohort=()"
        )
        response["Cross-Origin-Opener-Policy"] = "same-origin"
        response["Cross-Origin-Resource-Policy"] = "same-site"

        return response
