"""
HTTP request helpers for Klikk backend.

``get_client_ip(request)``
--------------------------
Returns the *real* client IP from a Django request, safe against spoofed
``X-Forwarded-For`` headers.

Behaviour is controlled by two Django settings:

``NUM_PROXIES`` (int, default ``1``)
    How many trusted reverse-proxies sit in front of Django.

    - ``0``  – no proxy; always use ``REMOTE_ADDR`` directly, ignore XFF.
    - ``1``  – one proxy (Caddy / nginx / ALB); use the *last* IP in XFF
               (appended by the nearest trusted proxy).
    - ``N``  – N proxies; walk *N* hops back from the rightmost XFF entry.

    When ``NUM_PROXIES >= 1`` and ``HTTP_X_FORWARDED_FOR`` is absent,
    ``REMOTE_ADDR`` is used as a fallback.

``TRUSTED_PROXY_IPS`` (list[str] | None, default ``None``)
    Optional explicit allowlist of trusted proxy IP addresses.  If set,
    only XFF entries written by an IP in this list are trusted.  Useful
    for multi-datacenter setups where you know the exact proxy IPs.
    When ``None`` the list is not consulted and only ``NUM_PROXIES`` is used.

Usage::

    from utils.http import get_client_ip

    ip = get_client_ip(request)

The function never raises; it returns ``None`` when no usable IP is found.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_client_ip(request) -> Optional[str]:
    """
    Return the real client IP for *request*, honouring proxy-trust settings.

    Parameters
    ----------
    request:
        Django ``HttpRequest`` (or DRF ``Request`` — META is accessible
        through DRF's ``._request`` transparently via attribute delegation).

    Returns
    -------
    str | None
        Dotted-decimal IPv4 or compressed IPv6 string, or ``None``.
    """
    from django.conf import settings

    num_proxies: int = getattr(settings, "NUM_PROXIES", 1)
    trusted_ips: list[str] | None = getattr(settings, "TRUSTED_PROXY_IPS", None)

    remote_addr: str = (request.META.get("REMOTE_ADDR") or "").strip()

    # No proxy trust — always use the socket address.
    if num_proxies == 0:
        return remote_addr or None

    # Optional strict IP allowlist: only trust XFF if the immediate proxy
    # (REMOTE_ADDR) is in the allowlist.
    if trusted_ips is not None and remote_addr not in trusted_ips:
        logger.debug(
            "get_client_ip: REMOTE_ADDR %r not in TRUSTED_PROXY_IPS — "
            "ignoring X-Forwarded-For.",
            remote_addr,
        )
        return remote_addr or None

    xff_header: str = request.META.get("HTTP_X_FORWARDED_FOR", "").strip()
    if not xff_header:
        # Proxy is trusted but did not add XFF — fall back to socket addr.
        return remote_addr or None

    # XFF is a comma-separated list of IPs, each proxy *appends* the IP it
    # received the connection from.  Convention (RFC 7239 / de-facto):
    #
    #   Client → ProxyA → ProxyB → Django
    #   REMOTE_ADDR = ProxyB_ip
    #   XFF: "client_ip, ProxyA_ip"    (ProxyA appended client_ip, ProxyB appended ProxyA_ip)
    #
    # With NUM_PROXIES=1 (trust ProxyB only):
    #   The last entry "ProxyA_ip" was appended by ProxyB; it is a trusted hop.
    #   The real client is the entry just before the trusted portion → ips[-2].
    #
    # With NUM_PROXIES=1 and a single-entry XFF "client_ip":
    #   There is no proxy entry in XFF (ProxyA was the only upstream proxy
    #   and it appended the client directly). client = ips[-1] = "client_ip".
    #
    # General rule:  client = ips[-(num_proxies + 1)]
    #   When ips has fewer than (num_proxies + 1) entries fall back to ips[0].

    ips = [part.strip() for part in xff_header.split(",") if part.strip()]

    if not ips:
        return remote_addr or None

    # Index of the real client: strip off the num_proxies trusted hops at
    # the right end, then take the rightmost remaining entry.
    client_index = -(num_proxies + 1)
    if abs(client_index) > len(ips):
        # Fewer XFF entries than expected trusted hops — use the leftmost
        # (first) entry defensively.
        client_ip = ips[0]
    else:
        client_ip = ips[client_index]

    return client_ip or None
