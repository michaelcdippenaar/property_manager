"""Exceptions raised by the legal_rag query API.

Keep this module dependency-free so it can be imported from anywhere
(views, signals, management commands, MCP server adapter, marketing
build scripts).
"""
from __future__ import annotations


class LegalFactNotFound(Exception):
    """Raised when a requested citation or concept_id is not in the corpus.

    Consumers must catch this explicitly — there is no implicit fallback to
    a "best effort" fact. The query API is fail-loud so a wrong cite cannot
    silently propagate into customer-facing output.

    Example:
        try:
            fact = query_statute("RHA s99(99)")
        except LegalFactNotFound:
            # Log + render a neutral disclaimer; do NOT guess.
            ...
    """
