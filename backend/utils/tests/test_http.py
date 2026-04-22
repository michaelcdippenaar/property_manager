"""
Tests for utils.http.get_client_ip — proxy-safe client IP extraction.

Covers:
- NUM_PROXIES=0: XFF is always ignored, REMOTE_ADDR is used
- NUM_PROXIES=1 (default): uses the correct hop from XFF
- NUM_PROXIES=2: walks two hops back
- No XFF header present: falls back to REMOTE_ADDR
- Empty XFF header: falls back to REMOTE_ADDR
- Spoofed XFF when NUM_PROXIES=0: returns REMOTE_ADDR, not the spoofed value
- TRUSTED_PROXY_IPS: XFF ignored when immediate proxy is not in allowlist
- TRUSTED_PROXY_IPS: XFF honoured when immediate proxy is in allowlist
- Fewer XFF hops than NUM_PROXIES: returns first (leftmost) IP defensively
- Missing REMOTE_ADDR and no XFF: returns None
"""

import pytest
from unittest.mock import patch


def _make_request(remote_addr="", xff=""):
    """Return a minimal object that mimics request.META access."""

    class FakeRequest:
        META = {}

    req = FakeRequest()
    req.META["REMOTE_ADDR"] = remote_addr
    if xff:
        req.META["HTTP_X_FORWARDED_FOR"] = xff
    return req


# ---------------------------------------------------------------------------
# NUM_PROXIES = 0  (no proxy — always trust socket)
# ---------------------------------------------------------------------------

def test_num_proxies_0_uses_remote_addr():
    req = _make_request(remote_addr="1.2.3.4", xff="10.0.0.1")
    with patch("django.conf.settings") as mock_settings:
        mock_settings.NUM_PROXIES = 0
        mock_settings.TRUSTED_PROXY_IPS = None
        from utils.http import get_client_ip
        assert get_client_ip(req) == "1.2.3.4"


def test_num_proxies_0_spoofed_xff_ignored():
    """A client that injects a spoofed XFF must not override REMOTE_ADDR."""
    req = _make_request(remote_addr="203.0.113.99", xff="1.1.1.1, 2.2.2.2")
    with patch("django.conf.settings") as mock_settings:
        mock_settings.NUM_PROXIES = 0
        mock_settings.TRUSTED_PROXY_IPS = None
        from utils.http import get_client_ip
        assert get_client_ip(req) == "203.0.113.99"


# ---------------------------------------------------------------------------
# NUM_PROXIES = 1  (single reverse proxy, e.g. Caddy / nginx)
# ---------------------------------------------------------------------------

def test_num_proxies_1_single_xff_entry():
    """Proxy set XFF to the client IP — single entry IS the client.

    Topology: Client -> Proxy -> Django
    XFF: "203.0.113.5"  (proxy appended client IP)
    REMOTE_ADDR: "10.0.0.1" (the proxy itself)

    Algorithm: ips[-(1+1)] = ips[-2] is out-of-range for 1-element list,
    so defensive fallback returns ips[0] = "203.0.113.5".
    """
    req = _make_request(remote_addr="10.0.0.1", xff="203.0.113.5")
    with patch("django.conf.settings") as mock_settings:
        mock_settings.NUM_PROXIES = 1
        mock_settings.TRUSTED_PROXY_IPS = None
        from utils.http import get_client_ip
        assert get_client_ip(req) == "203.0.113.5"


def test_num_proxies_1_multiple_xff_entries():
    """Two entries: rightmost was appended by the trusted proxy; client is the one before.

    Topology: Client -> ProxyA -> ProxyB -> Django
    XFF: "203.0.113.5, 10.0.0.2"
    - ProxyA appended "203.0.113.5" (the client IP it received the connection from)
    - ProxyB appended "10.0.0.2" (the ProxyA address it received from)
    REMOTE_ADDR: "10.0.0.1" (ProxyB)

    With NUM_PROXIES=1, we trust ProxyB only.
    Algorithm: client = ips[-(1+1)] = ips[-2] = "203.0.113.5"
    """
    req = _make_request(remote_addr="10.0.0.1", xff="203.0.113.5, 10.0.0.2")
    with patch("django.conf.settings") as mock_settings:
        mock_settings.NUM_PROXIES = 1
        mock_settings.TRUSTED_PROXY_IPS = None
        from utils.http import get_client_ip
        assert get_client_ip(req) == "203.0.113.5"


def test_num_proxies_1_no_xff_falls_back_to_remote_addr():
    req = _make_request(remote_addr="1.2.3.4")
    with patch("django.conf.settings") as mock_settings:
        mock_settings.NUM_PROXIES = 1
        mock_settings.TRUSTED_PROXY_IPS = None
        from utils.http import get_client_ip
        assert get_client_ip(req) == "1.2.3.4"


# ---------------------------------------------------------------------------
# NUM_PROXIES = 2
# ---------------------------------------------------------------------------

def test_num_proxies_2():
    """Three XFF entries: rightmost two are from trusted proxies; client is the first.

    XFF: "203.0.113.5, 10.0.0.1, 10.0.0.2"
    - "10.0.0.2" appended by the innermost trusted proxy (closest to Django)
    - "10.0.0.1" appended by the outer trusted proxy
    - "203.0.113.5" is the real client

    Algorithm: client = ips[-(2+1)] = ips[-3] = "203.0.113.5"
    """
    req = _make_request(remote_addr="10.0.0.2", xff="203.0.113.5, 10.0.0.1, 10.0.0.2")
    with patch("django.conf.settings") as mock_settings:
        mock_settings.NUM_PROXIES = 2
        mock_settings.TRUSTED_PROXY_IPS = None
        from utils.http import get_client_ip
        assert get_client_ip(req) == "203.0.113.5"


# ---------------------------------------------------------------------------
# Defensive: fewer XFF hops than NUM_PROXIES
# ---------------------------------------------------------------------------

def test_fewer_xff_hops_than_num_proxies():
    """If XFF has fewer entries than (NUM_PROXIES+1), return the leftmost (first) entry."""
    req = _make_request(remote_addr="10.0.0.1", xff="203.0.113.5")
    with patch("django.conf.settings") as mock_settings:
        mock_settings.NUM_PROXIES = 5
        mock_settings.TRUSTED_PROXY_IPS = None
        from utils.http import get_client_ip
        assert get_client_ip(req) == "203.0.113.5"


# ---------------------------------------------------------------------------
# TRUSTED_PROXY_IPS allowlist
# ---------------------------------------------------------------------------

def test_trusted_proxy_ips_allows_known_proxy():
    req = _make_request(remote_addr="10.0.0.1", xff="203.0.113.5")
    with patch("django.conf.settings") as mock_settings:
        mock_settings.NUM_PROXIES = 1
        mock_settings.TRUSTED_PROXY_IPS = ["10.0.0.1"]
        from utils.http import get_client_ip
        assert get_client_ip(req) == "203.0.113.5"


def test_trusted_proxy_ips_rejects_unknown_proxy():
    """REMOTE_ADDR not in allowlist — XFF is ignored, return REMOTE_ADDR directly."""
    req = _make_request(remote_addr="99.88.77.66", xff="1.1.1.1")
    with patch("django.conf.settings") as mock_settings:
        mock_settings.NUM_PROXIES = 1
        mock_settings.TRUSTED_PROXY_IPS = ["10.0.0.1"]
        from utils.http import get_client_ip
        assert get_client_ip(req) == "99.88.77.66"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_xff_falls_back_to_remote_addr():
    req = _make_request(remote_addr="1.2.3.4", xff="   ")
    with patch("django.conf.settings") as mock_settings:
        mock_settings.NUM_PROXIES = 1
        mock_settings.TRUSTED_PROXY_IPS = None
        from utils.http import get_client_ip
        assert get_client_ip(req) == "1.2.3.4"


def test_missing_everything_returns_none():
    req = _make_request(remote_addr="")
    with patch("django.conf.settings") as mock_settings:
        mock_settings.NUM_PROXIES = 1
        mock_settings.TRUSTED_PROXY_IPS = None
        from utils.http import get_client_ip
        assert get_client_ip(req) is None
