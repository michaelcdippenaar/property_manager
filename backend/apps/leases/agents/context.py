"""Frozen ``LeaseContext`` + ``IntentEnum`` for the lease-AI cluster.

Per ``docs/system/lease-ai-agent-architecture.md`` §7.1, the Front Door
builds a Context Object from the Property/Lease ORM rows + the user's
message + clarifying answers, then hands it to every downstream agent.

The dataclass is ``frozen`` so a Drafter can't accidentally mutate the
Reviewer's context: contextual drift is the failure class this prevents.

The dataclass is **hashable** (every field's type is hashable — tuples
not lists, ``str`` not ``list[str]``) so the cache layer can key on it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IntentEnum(str, Enum):
    """User-intent classification (architecture §5.1).

    Heuristic v1; we promote to a haiku LLM call only if routing
    complexity outgrows keyword matching.
    """

    GENERATE = "generate"
    EDIT = "edit"
    INSERT_CLAUSE = "insert_clause"
    FORMAT = "format"
    AUDIT = "audit"
    AUDIT_CASE_LAW = "audit_case_law"
    ANSWER = "answer"


@dataclass(frozen=True)
class LeaseContext:
    """Per-request execution context for the lease-AI cluster.

    Built by the Front Door once and passed by reference to every
    downstream agent. Frozen so no agent can mutate it — any change
    must round-trip through the Front Door (Phase 3+ revision flow).

    Field semantics:
      * ``intent`` is the classified user intent (see :class:`IntentEnum`).
      * ``property_type`` / ``tenant_count`` / ``lease_type`` /
        ``lease_term_months`` / ``deposit_amount`` / ``monthly_rent`` /
        ``province`` come from the Property + Lease DB rows (and from
        clarifying-question answers when missing).
      * ``conditions`` is a tuple (hashable) of free-form condition
        flags carried from the brief — e.g. ``("no_pets", "no_smoking")``.
      * ``with_case_law`` toggles the Reviewer's case-law tool surface.
      * ``fast_mode`` opts out of the Reviewer gate per decision 25.
      * ``template_html`` is the lease HTML before this turn's edits.
      * ``chat_history`` is the full ``messages.create``-shape turn list
        from the frontend (tuple of dicts — kept hashable so the context
        object is fully cacheable).
      * ``user_message`` is the latest user turn (already in chat_history,
        repeated here for ergonomic access).
    """

    intent: IntentEnum
    user_message: str

    # From ORM / clarifying answers — every field is Optional because the
    # Front Door may need to ask a clarifying question before all are
    # populated.
    property_type: str | None = None
    tenant_count: int | None = None
    lease_type: str | None = None
    lease_term_months: int | None = None
    deposit_amount: float | None = None
    monthly_rent: float | None = None
    province: str | None = None
    conditions: tuple[str, ...] = field(default_factory=tuple)

    # Flags.
    with_case_law: bool = False
    fast_mode: bool = False

    # Document surface.
    template_html: str = ""
    chat_history: tuple[dict[str, str], ...] = field(default_factory=tuple)

    # ── Helpers ────────────────────────────────────────────────────── #

    def gaps(self, required: frozenset[str]) -> frozenset[str]:
        """Return the set of required field names still missing.

        The Front Door uses this to decide whether to ask a clarifying
        question before dispatching. Per architecture §5.1 step 5: if
        gaps exist the Front Door returns a conversational question and
        does nothing else this turn.

        ``required`` is typically intent-dependent — generation needs
        property_type + tenant_count + lease_type, an audit needs only
        the document, etc. See ``front_door._required_for_intent``.
        """
        missing: set[str] = set()
        for name in required:
            if getattr(self, name, None) in (None, ""):
                missing.add(name)
        return frozenset(missing)


__all__ = ["IntentEnum", "LeaseContext"]
