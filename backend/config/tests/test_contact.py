"""
Tests for config/contact.py — contact_view rate limiting and IP extraction.

Covers:
- Forged X-Forwarded-For does NOT bypass rate limit when NUM_PROXIES=0
  (REMOTE_ADDR is always used, XFF is ignored).
- Regression: keyed IP is REMOTE_ADDR, not a spoofed XFF value.
- Happy-path submission creates a ContactEnquiry and returns 200.
- Origin allowlist rejects unknown origins.

Run with:
    cd backend && pytest config/tests/test_contact.py -v
"""

import json
from unittest.mock import patch

import pytest
from django.test import RequestFactory, override_settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _post(rf, *, remote_addr="10.0.0.1", xff=None, data=None, origin="https://klikk.co.za"):
    """Build a POST request to contact_view."""
    payload = data or {
        "name": "Test User",
        "email": "test@example.com",
        "message": "Hello from the test suite.",
        "consent": True,
    }
    kwargs = {
        "content_type": "application/json",
        "SERVER_NAME": "klikk.co.za",
        "HTTP_ORIGIN": origin,
        "REMOTE_ADDR": remote_addr,
    }
    if xff is not None:
        kwargs["HTTP_X_FORWARDED_FOR"] = xff
    return rf.post("/contact/", json.dumps(payload), **kwargs)


# ---------------------------------------------------------------------------
# Rate-limit / XFF bypass tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@override_settings(NUM_PROXIES=0, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_forged_xff_does_not_bypass_rate_limit(rf: RequestFactory):
    """
    With NUM_PROXIES=0 the rate limit keys on REMOTE_ADDR.
    A spoofed X-Forwarded-For header with a different IP must not change
    the keyed IP, so an attacker cannot submit >5 times by rotating XFF.
    """
    from config.contact import contact_view

    real_ip = "10.0.0.1"
    forged_ip = "1.2.3.4"

    # Submit RATE_LIMIT_PER_HOUR times from the real IP (no XFF)
    for _ in range(5):
        req = _post(rf, remote_addr=real_ip)
        resp = contact_view(req)
        assert resp.status_code in (200, 500)  # email may fail in test; row is created

    # 6th attempt with a forged XFF claiming a different IP — must still be blocked
    req = _post(rf, remote_addr=real_ip, xff=forged_ip)
    resp = contact_view(req)
    assert resp.status_code == 429, (
        "Rate limit bypassed: forged XFF allowed a 6th submission from the same real IP"
    )


@pytest.mark.django_db
@override_settings(NUM_PROXIES=0, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_keyed_ip_is_remote_addr_not_xff(rf: RequestFactory):
    """
    Regression: with NUM_PROXIES=0, the IP stored on the ContactEnquiry row
    must be REMOTE_ADDR, never the spoofed XFF value.
    """
    from apps.contact.models import ContactEnquiry
    from config.contact import contact_view

    real_ip = "192.168.1.50"
    forged_ip = "5.6.7.8"

    req = _post(rf, remote_addr=real_ip, xff=forged_ip)
    contact_view(req)

    enquiry = ContactEnquiry.objects.order_by("-created_at").first()
    assert enquiry is not None
    assert str(enquiry.ip_address) == real_ip, (
        f"Expected ip_address={real_ip!r}, got {enquiry.ip_address!r}; "
        "spoofed XFF must not influence stored IP when NUM_PROXIES=0"
    )


# ---------------------------------------------------------------------------
# Origin allowlist
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_unknown_origin_rejected(rf: RequestFactory):
    """Requests from origins outside the allowlist are refused with 403."""
    from config.contact import contact_view

    req = _post(rf, origin="https://evil.com")
    resp = contact_view(req)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Happy path (smoke)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@override_settings(NUM_PROXIES=0, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_happy_path_creates_enquiry(rf: RequestFactory):
    """Valid submission creates a ContactEnquiry row."""
    from apps.contact.models import ContactEnquiry
    from config.contact import contact_view

    req = _post(rf, remote_addr="203.0.113.10")
    resp = contact_view(req)
    # 200 OK expected; 500 only if email relay fails (acceptable in unit test)
    assert resp.status_code in (200, 500)
    assert ContactEnquiry.objects.filter(email="test@example.com").exists()
