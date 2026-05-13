"""Lease AI multi-agent cluster — Phase 2 Day 1-2 scaffold.

The architecture is locked in ``docs/system/lease-ai-agent-architecture.md``
§4 (25 decisions) and §5 (roster). This package wires the four
specialists:

  * ``front_door``  — pure Python coordinator. Builds the Context Object,
    classifies intent, retrieves RAG chunks, assembles the three cached
    system blocks, and chooses the route.
  * ``drafter``     — "SA Property Lawyer" persona. Owns the document
    surface. Calls ``edit_lines`` / ``add_clause`` / ``format_sa_standard``
    / ``insert_signature_field`` / ``highlight_fields`` /
    ``check_rha_compliance`` tools.
  * ``reviewer``    — "Compliance Counsel" persona. Read-only. Emits one
    forced ``submit_audit_report`` tool call.
  * ``formatter``   — "Layout Engineer" — Phase 2 Day 3+. Module stub
    raises ``NotImplementedError`` until then.

Every dispatch goes through :class:`apps.leases.agent_runner.LeaseAgentRunner`
so the runner's cost / call / wall-clock / retry caps cover the full
pipeline.
"""
from __future__ import annotations

from .context import IntentEnum, LeaseContext
from .drafter import (
    PERSONA as DRAFTER_PERSONA,
)
from .drafter import (
    TOOLS as DRAFTER_TOOLS,
)
from .drafter import (
    DrafterHandler,
    DrafterResult,
)
from .front_door import (
    FrontDoorDispatch,
    build_dispatch,
    classify_intent,
)
from .reviewer import (
    PERSONA as REVIEWER_PERSONA,
)
from .reviewer import (
    SUBMIT_AUDIT_REPORT_SCHEMA,
)
from .reviewer import (
    TOOLS as REVIEWER_TOOLS,
)
from .reviewer import (
    ReviewerHandler,
    ReviewerResult,
    ReviewerTruncatedError,
)

__all__ = [
    "DRAFTER_PERSONA",
    "DRAFTER_TOOLS",
    "DrafterHandler",
    "DrafterResult",
    "FrontDoorDispatch",
    "IntentEnum",
    "LeaseContext",
    "REVIEWER_PERSONA",
    "REVIEWER_TOOLS",
    "ReviewerHandler",
    "ReviewerResult",
    "ReviewerTruncatedError",
    "SUBMIT_AUDIT_REPORT_SCHEMA",
    "build_dispatch",
    "classify_intent",
]
