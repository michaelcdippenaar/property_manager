"""
Tests for SecurityHeadersMiddleware and security-related settings.

Covers:
  - SecurityHeadersMiddleware injects all required headers
  - CSP report-only vs enforce mode
  - Per-request nonce generation: nonce present, unsafe-inline/unsafe-eval absent
    in non-DEBUG (production) mode
  - CORS_ALLOWED_ORIGINS is an explicit list (no wildcard) in base settings
  - Session/CSRF cookie flags in staging settings
  - HSTS settings in production settings
  - X-Frame-Options and X-Content-Type-Options via Django SecurityMiddleware

Run with:
    pytest backend/config/tests/test_security_headers.py
"""

import importlib
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(**extra_headers):
    """Return a minimal mock HttpResponse-like dict."""
    headers = {}
    headers.update(extra_headers)

    class FakeResponse(dict):
        def __setitem__(self, key, value):
            super().__setitem__(key, value)

        def __getitem__(self, key):
            return super().__getitem__(key)

    return FakeResponse(headers)


def _make_request(path="/api/v1/ping/"):
    req = MagicMock()
    req.path = path
    return req


# ---------------------------------------------------------------------------
# SecurityHeadersMiddleware unit tests
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.unit, pytest.mark.green]


class TestSecurityHeadersMiddlewareReportOnly:
    """Middleware with CSP_REPORT_ONLY = True (staging default)."""

    def _get_middleware(
        self,
        report_only=True,
        extra_connect=None,
        sentry_dsn="",
        debug=False,
    ):
        from config.middleware import security_headers as mod

        fake_settings = MagicMock()
        fake_settings.CORS_ALLOWED_ORIGINS = [
            "http://localhost:5173",
            "https://app.klikk.co.za",
            "capacitor://localhost",
        ]
        fake_settings.SECURITY_HEADERS_CSP_REPORT_ONLY = report_only
        fake_settings.SECURITY_HEADERS_EXTRA_CONNECT = extra_connect or []
        fake_settings.SECURITY_HEADERS_CSP_REPORT_URI = ""
        fake_settings.SENTRY_DSN = sentry_dsn
        # Explicitly control debug mode so the nonce/unsafe-inline branch is predictable.
        fake_settings.DEBUG = debug

        def get_response(request):
            return _make_response()

        with patch.object(mod, "settings", fake_settings):
            middleware = mod.SecurityHeadersMiddleware(get_response)
            # Re-read report_only from fake settings
            middleware._csp_report_only = report_only
            response = middleware(_make_request())

        return response

    def test_csp_report_only_header_present(self):
        response = self._get_middleware(report_only=True)
        assert "Content-Security-Policy-Report-Only" in response
        assert "Content-Security-Policy" not in response

    def test_csp_enforce_header_present(self):
        response = self._get_middleware(report_only=False)
        assert "Content-Security-Policy" in response
        assert "Content-Security-Policy-Report-Only" not in response

    def test_referrer_policy_set(self):
        response = self._get_middleware()
        assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy_set(self):
        response = self._get_middleware()
        pp = response["Permissions-Policy"]
        assert "camera=()" in pp
        assert "microphone=()" in pp
        assert "geolocation=()" in pp
        assert "payment=()" in pp

    def test_coop_header_set(self):
        response = self._get_middleware()
        assert response["Cross-Origin-Opener-Policy"] == "same-origin"

    def test_corp_header_set(self):
        response = self._get_middleware()
        assert response["Cross-Origin-Resource-Policy"] == "same-site"

    def test_csp_contains_frame_ancestors_none(self):
        response = self._get_middleware(report_only=True)
        csp = response["Content-Security-Policy-Report-Only"]
        assert "frame-ancestors 'none'" in csp

    def test_csp_contains_default_src_self(self):
        response = self._get_middleware(report_only=True)
        csp = response["Content-Security-Policy-Report-Only"]
        assert "default-src 'self'" in csp

    def test_csp_contains_object_src_none(self):
        response = self._get_middleware(report_only=True)
        csp = response["Content-Security-Policy-Report-Only"]
        assert "object-src 'none'" in csp

    def test_csp_connect_src_includes_cors_origins(self):
        response = self._get_middleware(report_only=True)
        csp = response["Content-Security-Policy-Report-Only"]
        assert "https://app.klikk.co.za" in csp
        assert "http://localhost:5173" in csp

    def test_csp_connect_src_includes_capacitor_origin(self):
        response = self._get_middleware(report_only=True)
        csp = response["Content-Security-Policy-Report-Only"]
        assert "capacitor://localhost" in csp

    def test_extra_connect_origins_added(self):
        response = self._get_middleware(
            report_only=True,
            extra_connect=["https://sentry.klikk.co.za"],
        )
        csp = response["Content-Security-Policy-Report-Only"]
        assert "https://sentry.klikk.co.za" in csp

    def test_sentry_dsn_host_added_to_connect_src(self):
        response = self._get_middleware(
            report_only=True,
            sentry_dsn="https://abc123@o123456.ingest.sentry.io/789",
        )
        csp = response["Content-Security-Policy-Report-Only"]
        assert "https://o123456.ingest.sentry.io" in csp


# ---------------------------------------------------------------------------
# CSP nonce hardening tests (RNT-SEC-023)
# ---------------------------------------------------------------------------

class TestCSPNonceHardening:
    """Verify that production (DEBUG=False) CSP drops unsafe-inline/unsafe-eval
    and injects a per-request nonce, while dev mode (DEBUG=True) keeps the
    permissive fallbacks for Vite HMR compatibility."""

    def _invoke(self, debug: bool, report_only: bool = True, path: str = "/webhooks/stripe/"):
        """Return (request, response) from a single middleware call.

        Uses a non-exempt path by default (``/webhooks/stripe/``) so tests
        validate the strict production CSP branch.  Pass ``path="/admin/"`` or
        ``path="/api/..."`` explicitly to test the exempt branch.
        """
        from config.middleware import security_headers as mod

        fake_settings = MagicMock()
        fake_settings.CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]
        fake_settings.SECURITY_HEADERS_CSP_REPORT_ONLY = report_only
        fake_settings.SECURITY_HEADERS_EXTRA_CONNECT = []
        fake_settings.SECURITY_HEADERS_CSP_REPORT_URI = ""
        fake_settings.SENTRY_DSN = ""
        fake_settings.DEBUG = debug

        captured_request = {}

        def get_response(request):
            captured_request["req"] = request
            return _make_response()

        with patch.object(mod, "settings", fake_settings):
            middleware = mod.SecurityHeadersMiddleware(get_response)
            middleware._csp_report_only = report_only
            response = middleware(_make_request(path=path))

        return captured_request["req"], response

    def _get_csp(self, response, report_only: bool = True) -> str:
        if report_only:
            return response["Content-Security-Policy-Report-Only"]
        return response["Content-Security-Policy"]

    # --- Production mode (DEBUG=False) ---

    def test_production_nonce_stored_on_request(self):
        req, _ = self._invoke(debug=False)
        assert hasattr(req, "csp_nonce"), "request.csp_nonce must be set by middleware"
        nonce = req.csp_nonce
        assert isinstance(nonce, str) and len(nonce) > 0

    def test_production_nonce_unique_per_request(self):
        req1, _ = self._invoke(debug=False)
        req2, _ = self._invoke(debug=False)
        assert req1.csp_nonce != req2.csp_nonce, "Each request must get a fresh nonce"

    def test_production_nonce_in_script_src(self):
        req, response = self._invoke(debug=False)
        csp = self._get_csp(response)
        assert f"'nonce-{req.csp_nonce}'" in csp

    def test_production_no_unsafe_inline_in_script_src(self):
        _, response = self._invoke(debug=False)
        csp = self._get_csp(response)
        # Extract just the script-src directive value for a targeted assertion.
        script_src = next(
            (d for d in csp.split(";") if d.strip().startswith("script-src")), ""
        )
        assert "'unsafe-inline'" not in script_src, (
            "'unsafe-inline' must not appear in script-src in production"
        )

    def test_production_no_unsafe_eval_in_script_src(self):
        _, response = self._invoke(debug=False)
        csp = self._get_csp(response)
        script_src = next(
            (d for d in csp.split(";") if d.strip().startswith("script-src")), ""
        )
        assert "'unsafe-eval'" not in script_src, (
            "'unsafe-eval' must not appear in script-src in production"
        )

    def test_production_no_unsafe_inline_in_style_src(self):
        _, response = self._invoke(debug=False)
        csp = self._get_csp(response)
        style_src = next(
            (d for d in csp.split(";") if d.strip().startswith("style-src")), ""
        )
        assert "'unsafe-inline'" not in style_src, (
            "'unsafe-inline' must not appear in style-src in production"
        )

    def test_production_no_strict_dynamic_in_script_src(self):
        """'strict-dynamic' must NOT be in the production script-src.

        When 'strict-dynamic' is present the browser ignores allowlist sources
        like 'self', which would block the un-nonced Vite root module script
        served statically by Caddy.  Removing it keeps 'self' honoured so the
        SPA boots correctly.  Mozilla Observatory still awards A/A+ because
        unsafe-inline and unsafe-eval are both absent.
        """
        _, response = self._invoke(debug=False)
        csp = self._get_csp(response)
        script_src = next(
            (d for d in csp.split(";") if d.strip().startswith("script-src")), ""
        )
        assert "'strict-dynamic'" not in script_src, (
            "'strict-dynamic' must be absent so 'self' covers un-nonced Vite "
            "module scripts served statically from Caddy"
        )

    def test_production_self_in_script_src(self):
        """'self' must remain in the production script-src to cover Vite assets."""
        _, response = self._invoke(debug=False)
        csp = self._get_csp(response)
        script_src = next(
            (d for d in csp.split(";") if d.strip().startswith("script-src")), ""
        )
        assert "'self'" in script_src

    def test_production_google_fonts_in_style_src(self):
        """Google Fonts stylesheet must be allowed for the admin SPA."""
        _, response = self._invoke(debug=False)
        csp = self._get_csp(response)
        style_src = next(
            (d for d in csp.split(";") if d.strip().startswith("style-src")), ""
        )
        assert "https://fonts.googleapis.com" in style_src

    # --- Dev mode (DEBUG=True) ---

    def test_dev_mode_nonce_still_set_on_request(self):
        """Even in dev, request.csp_nonce is populated (templates may use it)."""
        req, _ = self._invoke(debug=True)
        assert hasattr(req, "csp_nonce")
        assert len(req.csp_nonce) > 0

    def test_dev_mode_unsafe_inline_preserved_for_hmr(self):
        _, response = self._invoke(debug=True)
        csp = self._get_csp(response)
        script_src = next(
            (d for d in csp.split(";") if d.strip().startswith("script-src")), ""
        )
        assert "'unsafe-inline'" in script_src, (
            "Dev mode must keep unsafe-inline so Vite HMR works"
        )

    def test_dev_mode_unsafe_eval_preserved_for_hmr(self):
        _, response = self._invoke(debug=True)
        csp = self._get_csp(response)
        script_src = next(
            (d for d in csp.split(";") if d.strip().startswith("script-src")), ""
        )
        assert "'unsafe-eval'" in script_src, (
            "Dev mode must keep unsafe-eval so Vite HMR works"
        )


# ---------------------------------------------------------------------------
# Path-based CSP exemption tests (RNT-SEC-023 review fixes)
# ---------------------------------------------------------------------------

class TestCSPPathExemption:
    """Verify the /admin/ and /api/ paths get the relaxed (unsafe-inline) policy
    and that all other paths get the strict nonce-only policy.

    Risk acceptance: Django Admin + DRF browsable API render inline <script>
    blocks.  Re-adding 'unsafe-inline' for those staff-only paths is an
    accepted v1 compensating control (CTO sign-off required before v2
    hardening).
    """

    def _invoke(self, path: str, debug: bool = False, report_only: bool = True):
        from config.middleware import security_headers as mod

        fake_settings = MagicMock()
        fake_settings.CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]
        fake_settings.SECURITY_HEADERS_CSP_REPORT_ONLY = report_only
        fake_settings.SECURITY_HEADERS_EXTRA_CONNECT = []
        fake_settings.SECURITY_HEADERS_CSP_REPORT_URI = ""
        fake_settings.SENTRY_DSN = ""
        fake_settings.DEBUG = debug

        def get_response(request):
            return _make_response()

        with patch.object(mod, "settings", fake_settings):
            middleware = mod.SecurityHeadersMiddleware(get_response)
            middleware._csp_report_only = report_only
            response = middleware(_make_request(path=path))

        return response

    def _script_src(self, response, report_only: bool = True) -> str:
        key = "Content-Security-Policy-Report-Only" if report_only else "Content-Security-Policy"
        csp = response[key]
        return next((d for d in csp.split(";") if d.strip().startswith("script-src")), "")

    # --- /admin/ exemption ---

    def test_admin_path_has_unsafe_inline(self):
        response = self._invoke("/admin/")
        script_src = self._script_src(response)
        assert "'unsafe-inline'" in script_src, (
            "/admin/ must include 'unsafe-inline' for Django Admin inline scripts"
        )

    def test_admin_path_no_strict_dynamic(self):
        response = self._invoke("/admin/auth/user/")
        script_src = self._script_src(response)
        assert "'strict-dynamic'" not in script_src

    def test_admin_path_still_has_self(self):
        response = self._invoke("/admin/")
        script_src = self._script_src(response)
        assert "'self'" in script_src

    def test_admin_path_still_has_nonce(self):
        """Even on exempt paths, the nonce is included so template tags can use it."""
        response = self._invoke("/admin/")
        csp = response["Content-Security-Policy-Report-Only"]
        assert "'nonce-" in csp

    # --- /api/ paths use strict policy (no longer exempt) ---
    # RNT-SEC-023 pass 2: /api/ carve-out was too broad.  BrowsableAPIRenderer
    # is now disabled in production, so /api/ paths only serve JSON and do not
    # need the unsafe-inline compensation.  This keeps the main API surface under
    # the strict CSP.

    def test_api_path_json_no_unsafe_inline(self):
        """API JSON endpoints must NOT have 'unsafe-inline' in production."""
        response = self._invoke("/api/v1/leases/", debug=False)
        script_src = self._script_src(response)
        assert "'unsafe-inline'" not in script_src, (
            "/api/ JSON responses must use strict nonce policy "
            "(BrowsableAPIRenderer disabled in prod)"
        )

    def test_api_path_no_strict_dynamic(self):
        response = self._invoke("/api/v1/leases/", debug=False)
        script_src = self._script_src(response)
        assert "'strict-dynamic'" not in script_src

    # --- Non-exempt paths use strict policy ---

    def test_non_exempt_path_no_unsafe_inline(self):
        """A non-exempt path must NOT have 'unsafe-inline' in script-src."""
        response = self._invoke("/webhooks/stripe/")
        script_src = self._script_src(response)
        assert "'unsafe-inline'" not in script_src

    def test_non_exempt_path_no_strict_dynamic(self):
        response = self._invoke("/webhooks/stripe/")
        script_src = self._script_src(response)
        assert "'strict-dynamic'" not in script_src

    def test_non_exempt_path_has_self_and_nonce(self):
        response = self._invoke("/webhooks/stripe/")
        script_src = self._script_src(response)
        assert "'self'" in script_src
        assert "'nonce-" in script_src

    def test_root_path_is_not_exempt(self):
        """A request to / should get the strict (no unsafe-inline) policy."""
        response = self._invoke("/")
        script_src = self._script_src(response)
        assert "'unsafe-inline'" not in script_src

    # --- Debug mode overrides exemption (everything permissive) ---

    def test_debug_mode_admin_path_has_unsafe_eval(self):
        """In DEBUG mode the permissive dev policy applies regardless of path."""
        response = self._invoke("/admin/", debug=True)
        script_src = self._script_src(response)
        assert "'unsafe-eval'" in script_src


# ---------------------------------------------------------------------------
# Settings smoke tests (unit — no DB, no server)
# ---------------------------------------------------------------------------

class TestBaseSettings:
    """Verify base settings have no wildcard CORS."""

    def test_cors_allowed_origins_is_explicit_list(self):
        from config.settings import base as base_mod

        origins = base_mod.CORS_ALLOWED_ORIGINS
        assert isinstance(origins, list), "CORS_ALLOWED_ORIGINS must be a list"
        assert len(origins) > 0, "CORS_ALLOWED_ORIGINS must not be empty"

    def test_no_cors_allow_all_origins_in_base(self):
        from config.settings import base as base_mod

        allow_all = getattr(base_mod, "CORS_ALLOW_ALL_ORIGINS", False)
        assert allow_all is False, (
            "CORS_ALLOW_ALL_ORIGINS must not be True in base settings "
            "(it may be True only in local.py)"
        )

    def test_no_wildcard_in_cors_origins(self):
        from config.settings import base as base_mod

        for origin in base_mod.CORS_ALLOWED_ORIGINS:
            assert "*" not in origin, (
                f"Wildcard found in CORS_ALLOWED_ORIGINS entry: {origin!r}"
            )


class TestStagingCookieSettings:
    """Verify staging/production cookie hardening."""

    def _load_staging(self):
        """Import (or reload) staging settings module."""
        import sys
        mod = importlib.import_module("config.settings.staging")
        importlib.reload(mod)
        return mod

    def test_session_cookie_secure(self):
        mod = self._load_staging()
        assert getattr(mod, "SESSION_COOKIE_SECURE", False) is True

    def test_csrf_cookie_secure(self):
        mod = self._load_staging()
        assert getattr(mod, "CSRF_COOKIE_SECURE", False) is True

    def test_session_cookie_httponly(self):
        mod = self._load_staging()
        assert getattr(mod, "SESSION_COOKIE_HTTPONLY", False) is True

    def test_session_cookie_samesite_lax(self):
        mod = self._load_staging()
        assert getattr(mod, "SESSION_COOKIE_SAMESITE", None) == "Lax"

    def test_csrf_cookie_samesite_lax(self):
        mod = self._load_staging()
        assert getattr(mod, "CSRF_COOKIE_SAMESITE", None) == "Lax"

    def test_x_frame_options_deny(self):
        mod = self._load_staging()
        assert getattr(mod, "X_FRAME_OPTIONS", None) == "DENY"

    def test_content_type_nosniff(self):
        mod = self._load_staging()
        assert getattr(mod, "SECURE_CONTENT_TYPE_NOSNIFF", False) is True

    def test_security_headers_middleware_registered(self):
        mod = self._load_staging()
        middleware = getattr(mod, "MIDDLEWARE", [])
        assert "config.middleware.security_headers.SecurityHeadersMiddleware" in middleware

    def test_csp_report_only_in_staging(self):
        mod = self._load_staging()
        assert getattr(mod, "SECURITY_HEADERS_CSP_REPORT_ONLY", None) is True


class TestProductionHSTSSettings:
    """Verify production HSTS is ramped to 1 year with preload."""

    def _load_production(self):
        """Import (or reload) production settings module."""
        mod = importlib.import_module("config.settings.production")
        importlib.reload(mod)
        return mod

    def test_hsts_seconds_one_year(self):
        mod = self._load_production()
        assert getattr(mod, "SECURE_HSTS_SECONDS", 0) == 31536000

    def test_hsts_include_subdomains(self):
        mod = self._load_production()
        assert getattr(mod, "SECURE_HSTS_INCLUDE_SUBDOMAINS", False) is True

    def test_hsts_preload(self):
        mod = self._load_production()
        assert getattr(mod, "SECURE_HSTS_PRELOAD", False) is True

    def test_csp_enforced_not_report_only_in_production(self):
        mod = self._load_production()
        assert getattr(mod, "SECURITY_HEADERS_CSP_REPORT_ONLY", True) is False


# ---------------------------------------------------------------------------
# RNT-QUAL-064: localhost must never appear in production CORS / CSRF
# ---------------------------------------------------------------------------

_LOCALHOST_MARKERS = ("localhost", "127.0.0.1")


class TestProductionNoLocalhostOrigins:
    """Regression guard: production settings must contain no localhost entries
    in CORS_ALLOWED_ORIGINS or CSRF_TRUSTED_ORIGINS.

    This is an external-audit finding — localhost origins in base.py settings
    would be present in every environment including production.
    """

    def _load_production(self):
        mod = importlib.import_module("config.settings.production")
        importlib.reload(mod)
        return mod

    def test_cors_allowed_origins_no_localhost(self):
        mod = self._load_production()
        origins = getattr(mod, "CORS_ALLOWED_ORIGINS", [])
        bad = [o for o in origins if any(m in o for m in _LOCALHOST_MARKERS)]
        assert not bad, (
            f"Production CORS_ALLOWED_ORIGINS must not contain localhost entries: {bad}"
        )

    def test_csrf_trusted_origins_no_localhost(self):
        mod = self._load_production()
        origins = getattr(mod, "CSRF_TRUSTED_ORIGINS", [])
        bad = [o for o in origins if any(m in o for m in _LOCALHOST_MARKERS)]
        assert not bad, (
            f"Production CSRF_TRUSTED_ORIGINS must not contain localhost entries: {bad}"
        )

    def test_base_cors_no_localhost(self):
        from config.settings import base as base_mod
        importlib.reload(base_mod)
        origins = getattr(base_mod, "CORS_ALLOWED_ORIGINS", [])
        bad = [o for o in origins if any(m in o for m in _LOCALHOST_MARKERS)]
        assert not bad, (
            f"base.py CORS_ALLOWED_ORIGINS must not contain localhost entries: {bad}"
        )

    def test_base_csrf_no_localhost(self):
        from config.settings import base as base_mod
        importlib.reload(base_mod)
        origins = getattr(base_mod, "CSRF_TRUSTED_ORIGINS", [])
        bad = [o for o in origins if any(m in o for m in _LOCALHOST_MARKERS)]
        assert not bad, (
            f"base.py CSRF_TRUSTED_ORIGINS must not contain localhost entries: {bad}"
        )
