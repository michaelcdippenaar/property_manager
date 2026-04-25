"""
apps/ai/knowledge.py

Loads the admin-editable AI domain knowledge file and caches it with a
5-minute TTL.  The returned string is ready to be injected verbatim into a
system prompt under a ``## Klikk Domain Rules`` section.

Usage
-----
    from apps.ai.knowledge import get_knowledge, bust_cache

    # Inject into prompt:
    knowledge = get_knowledge()
    system = f"{base_prompt}\n\n## Klikk Domain Rules\n{knowledge}"

    # After an admin save:
    bust_cache()
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

# BASE_DIR = backend/  →  repo root = backend/../
# knowledge.md lives at <repo_root>/content/ai/knowledge.md
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
_REPO_ROOT = _BACKEND_DIR.parent
_KNOWLEDGE_FILE = _REPO_ROOT / "content" / "ai" / "knowledge.md"

# ---------------------------------------------------------------------------
# In-process cache (thread-safe, no external dependency)
# ---------------------------------------------------------------------------

_CACHE_TTL = 5 * 60  # 5 minutes in seconds

_lock = threading.Lock()
_cached_content: str | None = None
_cached_at: float = 0.0


def _load_from_disk() -> str:
    """Read knowledge.md from disk.  Returns empty string on any error."""
    try:
        return _KNOWLEDGE_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning(
            "AI knowledge file not found at %s — injecting empty knowledge block",
            _KNOWLEDGE_FILE,
        )
        return ""
    except OSError as exc:
        logger.error("Failed to read AI knowledge file %s: %s", _KNOWLEDGE_FILE, exc)
        return ""


def get_knowledge() -> str:
    """
    Return the knowledge markdown string.

    First call reads from disk.  Subsequent calls return the cached value
    until the 5-minute TTL expires or bust_cache() is called.
    """
    global _cached_content, _cached_at

    with _lock:
        now = time.monotonic()
        if _cached_content is None or (now - _cached_at) >= _CACHE_TTL:
            _cached_content = _load_from_disk()
            _cached_at = now

        return _cached_content


def bust_cache() -> None:
    """
    Immediately invalidate the in-process cache.

    Call this after persisting a new version of knowledge.md so the next
    request picks up the fresh content without waiting for TTL expiry.
    """
    global _cached_content, _cached_at

    with _lock:
        _cached_content = None
        _cached_at = 0.0

    logger.info("AI knowledge cache busted — next request will reload from disk")


def save_knowledge(content: str) -> None:
    """
    Write *content* to knowledge.md and bust the in-process cache.

    Raises ``OSError`` on write failure (caller is responsible for surfacing
    the error to the HTTP layer).
    """
    _KNOWLEDGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _KNOWLEDGE_FILE.write_text(content, encoding="utf-8")
    bust_cache()
    logger.info("AI knowledge file updated (%d chars)", len(content))
