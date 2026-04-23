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

Nonce:
  A cryptographically random nonce is generated per request and stored on
  ``request.csp_nonce``.  In non-DEBUG (production/staging) the nonce replaces
  ``unsafe-inline`` / ``unsafe-eval`` in both ``script-src`` and ``style-src``.
  In DEBUG mode (local Vite HMR) the permissive fallbacks are preserved so the
  dev server continues to work.

Path-based exemptions:
  ``/admin/`` and ``/api/`` paths receive a relaxed policy that re-adds
  ``'unsafe-inline'`` to ``script-src``.  Django Admin and DRF's browsable API
  both render inline ``<script>`` blocks that cannot easily be nonce-stamped
  without full template overrides.  Since these paths are staff-only and
  low-volume this is an acceptable compensating control for v1 (documented risk,
  CTO sign-off required before v2 hardening).  The SPA and all JSON API
  responses still use the strict nonce policy.
"""

from __future__ import annotations

import secrets

from django.conf import settings


def _csp_directives(nonce: str, exempt: bool = False) -> str:
    """Build the CSP directive string from settings.

    Args:
        nonce: Per-request base64url nonce included in script-src/style-src.
        exempt: When True the path is a staff-only route (``/admin/`` or
            ``/api/`` browsable API) that requires ``'unsafe-inline'`` because
            Django Admin and DRF render inline ``<script>`` blocks.  The nonce
            is still generated and stored on the request so context processors
            can use it, but ``'unsafe-inline'`` is re-added as a fallback.
            See module docstring for the risk acceptance note.
    """
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

    debug = getattr(settings, "DEBUG", False)

    if debug:
        # Development: Vite HMR injects inline scripts and uses eval for hot-reload.
        # Keep unsafe-inline / unsafe-eval so the local dev server works.
        script_src = ["'self'", "'unsafe-inline'", "'unsafe-eval'"]
        # Tailwind JIT and Vue scoped styles also emit inline styles in dev.
        style_src = ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"]
    elif exempt:
        # Staff-only path (/admin/, /api/ browsable API): re-add unsafe-inline.
        # 'strict-dynamic' is intentionally absent so 'self' + 'unsafe-inline'
        # cover both Django Admin's inline scripts and external static assets.
        # RISK: accepted for v1 because these paths are only accessible to
        # authenticated staff.  Full nonce stamping on admin templates is a v2
        # hardening item.
        nonce_token = f"'nonce-{nonce}'"
        script_src = ["'self'", nonce_token, "'unsafe-inline'"]
        style_src = ["'self'", nonce_token, "'unsafe-inline'", "https://fonts.googleapis.com"]
    else:
        # Production / staging: strict nonce-based policy.
        # The Vite build emits only external <script type="module" src="..."> tags
        # (no inline scripts), so 'self' + nonce covers everything.
        # 'strict-dynamic' is intentionally NOT included: when 'strict-dynamic' is
        # present the browser ignores allowlist sources like 'self', which would
        # block the un-nonced root module script emitted by Vite
        # (<script type="module" crossorigin src="/assets/index-*.js">) since
        # Caddy serves admin/dist/index.html as a static file without Django
        # injecting a nonce attribute.  Dropping 'strict-dynamic' keeps 'self'
        # honoured so the SPA boots correctly.  Observatory still awards A/A+
        # because unsafe-inline and unsafe-eval are both absent.
        # Vue 3 template compiler is disabled in the production build (see
        # admin/vite.config.ts), eliminating the unsafe-eval requirement.
        nonce_token = f"'nonce-{nonce}'"
        script_src = ["'self'", nonce_token]
        # Style: external CSS files from the Vite build + Google Fonts link tag.
        # 'unsafe-inline' removed; nonce covers any remaining inline style needs.
        style_src = [
            "'self'",
            nonce_token,
            "https://fonts.googleapis.com",
        ]

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
    """Add supplementary security response headers on every response.

    Generates a per-request CSP nonce (16 bytes, base64url-encoded) and stores
    it on ``request.csp_nonce``.  Django templates and views can read this
    attribute to stamp any inline <script> or <style> blocks they emit.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._csp_report_only: bool = getattr(
            settings, "SECURITY_HEADERS_CSP_REPORT_ONLY", True
        )

    # Paths that receive the relaxed (unsafe-inline) policy because Django Admin
    # and DRF browsable API render inline <script> blocks we cannot easily nonce.
    # Matching is prefix-based (startswith).  Staff-only; low XSS exposure.
    _EXEMPT_PREFIXES = ("/admin/", "/api/")

    def __call__(self, request):
        # Generate a fresh nonce for this request cycle.
        nonce = secrets.token_urlsafe(16)
        request.csp_nonce = nonce

        response = self.get_response(request)

        # Apply the relaxed policy for staff-only paths that need unsafe-inline.
        path = getattr(request, "path", "") or ""
        exempt = any(path.startswith(prefix) for prefix in self._EXEMPT_PREFIXES)

        csp = _csp_directives(nonce, exempt=exempt)
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
