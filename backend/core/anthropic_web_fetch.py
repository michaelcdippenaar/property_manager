"""
Anthropic hosted web_fetch tool (optional). URLs must already appear in the conversation.
"""
from __future__ import annotations

import os


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def anthropic_web_fetch_enabled() -> bool:
    if _env_flag("ANTHROPIC_WEB_FETCH_DISABLED", default=False):
        return False
    try:
        from django.conf import settings

        if getattr(settings, "ANTHROPIC_WEB_FETCH_ENABLED", False):
            return True
    except Exception:
        pass
    return _env_flag("ANTHROPIC_WEB_FETCH_ENABLED", default=False)


def build_web_fetch_tools() -> list[dict] | None:
    if not anthropic_web_fetch_enabled():
        return None
    max_raw = (os.environ.get("ANTHROPIC_WEB_FETCH_MAX_USES") or "5").strip()
    try:
        max_uses = max(1, min(20, int(max_raw)))
    except ValueError:
        max_uses = 5
    tool: dict = {
        "type": "web_fetch_20250910",
        "name": "web_fetch",
        "max_uses": max_uses,
    }
    domains_raw = (os.environ.get("ANTHROPIC_WEB_FETCH_ALLOWED_DOMAINS") or "").strip()
    if domains_raw:
        domains = [d.strip().lower() for d in domains_raw.split(",") if d.strip()]
        if domains:
            tool["allowed_domains"] = domains
    return [tool]


def extract_anthropic_assistant_text(response) -> str:
    parts: list[str] = []
    for block in getattr(response, "content", None) or []:
        if getattr(block, "type", None) == "text":
            t = getattr(block, "text", None) or ""
            if t:
                parts.append(t)
    joined = "\n".join(parts).strip()
    if joined:
        return joined
    if response.content and hasattr(response.content[0], "text"):
        return (response.content[0].text or "").strip()
    return ""
