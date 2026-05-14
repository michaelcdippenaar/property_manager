"""Lease AI multi-agent loop coordinator.

This module owns ALL budget enforcement for the multi-agent loop. Every
Drafter / Reviewer / Formatter dispatch goes through ``LeaseAgentRunner``;
the view layer never calls ``anthropic.Anthropic.messages.create`` directly
for this pipeline.

Caps enforced:
    - total LLM calls per request    (``max_calls``)
    - wall-clock seconds per request (``max_wallclock_seconds``)
    - retry count                    (``max_retries``)
    - running cost in USD            (``max_cost_usd``)

On cap-hit the runner raises ``LeaseAgentBudgetExceeded`` with
``terminated_reason`` populated. The view catches it, ships a partial
result with a user-visible banner, and the runner's ``finalize()`` call
persists the ``AILeaseAgentRun`` row.

See ``docs/system/lease-ai-agent-architecture.md`` decisions 10, 20, 23
and §8.1 for the locked design.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.conf import settings

if TYPE_CHECKING:
    import anthropic
    from anthropic.types import Message

logger = logging.getLogger(__name__)


# ── Exceptions ────────────────────────────────────────────────────────── #


class LeaseAgentBudgetExceeded(Exception):
    """Raised by ``LeaseAgentRunner`` when a budget cap is hit.

    ``terminated_reason`` is one of the ``AILeaseAgentRun.TerminatedReason``
    enum values (string form): cap_calls / cap_walltime / cap_cost /
    cap_retries.
    """

    def __init__(self, terminated_reason: str, message: str = ""):
        self.terminated_reason = terminated_reason
        super().__init__(message or terminated_reason)


# ── Configuration ─────────────────────────────────────────────────────── #


# Cost model — decision 23 of the architecture doc.
# Pricing is USD per million tokens, current snapshot 2026-05.
PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {
        "input_per_mtok": 3.00,
        "output_per_mtok": 15.00,
        "cache_read_per_mtok": 0.30,
        "cache_create_per_mtok": 3.75,
    },
    # Backwards-compat aliases — the architecture doc uses "claude-sonnet-4-6"
    # while the current production model snapshot is "claude-sonnet-4-5".
    # Keep both keyed so model-name drift doesn't silently fall through to a
    # zero-cost computation.
    "claude-sonnet-4-5": {
        "input_per_mtok": 3.00,
        "output_per_mtok": 15.00,
        "cache_read_per_mtok": 0.30,
        "cache_create_per_mtok": 3.75,
    },
    "claude-haiku-4-5-20251001": {
        "input_per_mtok": 0.80,
        "output_per_mtok": 4.00,
        "cache_read_per_mtok": 0.08,
        "cache_create_per_mtok": 1.00,
    },
}


@dataclass
class _CallRecord:
    """In-memory record of one LLM call. Serialised into ``call_log`` JSON."""

    agent: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read: int
    cache_created: int
    cost_usd: float
    duration_ms: int
    timestamp: str  # ISO8601 UTC


# ── Coordinator ───────────────────────────────────────────────────────── #


class LeaseAgentRunner:
    """Coordinator for the lease-AI multi-agent loop.

    Owns: total LLM-call cap, wall-clock cap, retry cap, running-cost cap.
    On cap-hit raises ``LeaseAgentBudgetExceeded`` with ``terminated_reason``.
    On completion persists an ``AILeaseAgentRun`` row.

    Usage:
        runner = LeaseAgentRunner(
            request_id=str(uuid4()),
            intent="generate",
            anthropic_client=client,
            lease_id=lease.pk,
        )
        try:
            resp = runner.dispatch(
                agent="drafter",
                model=settings.LEASE_AI_DRAFTER_MODEL,
                messages=[...],
                system=[...],
                tools=[...],
            )
            ...
            run = runner.finalize(terminated_reason="completed")
        except LeaseAgentBudgetExceeded as exc:
            run = runner.finalize(terminated_reason=exc.terminated_reason)
    """

    # Defaults aligned with decision 10 + decision 20 of the architecture doc.
    DEFAULT_MAX_CALLS = 8
    DEFAULT_MAX_WALLCLOCK_SECONDS = 90.0
    DEFAULT_MAX_RETRIES = 1
    DEFAULT_MAX_COST_USD = 0.50

    PRICING = PRICING

    def __init__(
        self,
        *,
        request_id: str,
        intent: str,
        anthropic_client: "anthropic.Anthropic | None" = None,
        lease_id: int | None = None,
        corpus_version: str | None = None,
        max_calls: int | None = None,
        max_wallclock_seconds: float | None = None,
        max_retries: int | None = None,
        max_cost_usd: float | None = None,
        # P0-7 POPIA accountability fields — passed from the authenticated view.
        template_id: int | None = None,
        user_id: int | None = None,
        agency_id: int | None = None,
        user_message: str = "",
        document_html_before: str = "",
    ):
        self.request_id = request_id
        self.intent = intent
        self.anthropic_client = anthropic_client
        self.lease_id = lease_id
        self.corpus_version = corpus_version
        # P0-7 accountability
        self.template_id = template_id
        self.user_id = user_id
        self.agency_id = agency_id
        self.user_message = user_message
        self.document_html_before = document_html_before
        # Mutable — set by the view after pipeline completion so finalize() can persist it.
        self.document_html_after: str = ""

        self.max_calls = max_calls if max_calls is not None else self.DEFAULT_MAX_CALLS
        self.max_wallclock_seconds = (
            max_wallclock_seconds
            if max_wallclock_seconds is not None
            else self.DEFAULT_MAX_WALLCLOCK_SECONDS
        )
        self.max_retries = (
            max_retries if max_retries is not None else self.DEFAULT_MAX_RETRIES
        )
        self.max_cost_usd = (
            max_cost_usd
            if max_cost_usd is not None
            else float(
                getattr(
                    settings,
                    "LEASE_AI_MAX_COST_USD_PER_REQUEST",
                    self.DEFAULT_MAX_COST_USD,
                )
            )
        )

        self.llm_call_count: int = 0
        self.retry_count: int = 0
        self.running_cost_usd: float = 0.0
        self.wall_clock_start: float = time.monotonic()
        self.terminated_reason: str | None = None
        self._call_log: list[_CallRecord] = []

    # ── Public surface ───────────────────────────────────────────────── #

    def dispatch(
        self,
        *,
        agent: str,
        model: str,
        messages: list[dict[str, Any]],
        system: list[dict[str, Any]] | str,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        max_tokens: int = 4096,
    ) -> "Message":
        """Single entry point for ALL agent dispatches.

        Enforces caps BEFORE the call (so a 9th call never fires), then
        invokes the Anthropic client, updates counters from the response's
        ``usage``, logs the call, and returns the raw ``Message``.
        """
        self._enforce_caps_before_call()

        if self.anthropic_client is None:
            raise RuntimeError(
                "LeaseAgentRunner.dispatch called with no anthropic_client. "
                "Construct the runner with anthropic_client=<anthropic.Anthropic>."
            )

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
            "system": system,
        }
        if tools is not None:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice

        t0 = time.monotonic()
        try:
            resp = self.anthropic_client.messages.create(**kwargs)
        except Exception:
            logger.exception(
                "LeaseAgentRunner: anthropic.messages.create failed "
                "request_id=%s agent=%s model=%s",
                self.request_id,
                agent,
                model,
            )
            raise
        duration_ms = int((time.monotonic() - t0) * 1000)

        self._record_call(
            agent=agent, model=model, response=resp, duration_ms=duration_ms
        )

        if self.is_truncated_tool_use(resp, tool_choice):
            logger.warning(
                "LeaseAgentRunner: forced tool_choice hit max_tokens — tool_use "
                "input is truncated partial-JSON and will fail downstream parse. "
                "request_id=%s agent=%s model=%s max_tokens=%d",
                self.request_id, agent, model, max_tokens,
            )

        return resp

    def increment_retry(self) -> None:
        """Bump the retry counter (called after Reviewer says revise_required)."""
        self.retry_count += 1
        if self.retry_count > self.max_retries:
            self.terminated_reason = "cap_retries"
            raise LeaseAgentBudgetExceeded(
                "cap_retries",
                f"retry_count={self.retry_count} > max_retries={self.max_retries}",
            )

    def should_retry(self, audit_report: dict[str, Any] | None) -> bool:
        """Decide whether the Drafter should run a revision pass.

        Per decision 24: retry ONLY if Reviewer emitted >=1 ``blocking``
        finding AND the retry counter has not been spent. ``recommended`` and
        ``nice_to_have`` findings ship in the audit report without forcing a
        Drafter re-run.
        """
        if audit_report is None:
            return False
        if self.retry_count >= self.max_retries:
            return False

        for bucket in ("statute_findings", "case_law_findings", "format_findings"):
            for finding in audit_report.get(bucket) or []:
                if finding.get("severity") == "blocking":
                    return True
        return False

    def finalize(self, *, terminated_reason: str | None = None) -> Any:
        """Persist the run as an ``AILeaseAgentRun`` row and return it.

        ``terminated_reason`` defaults to ``"completed"`` when not set on the
        runner already (e.g. by a cap-hit). Imports the model lazily so this
        module is importable from contexts where Django is not configured
        (e.g. test discovery scaffolding).
        """
        from apps.leases.models import AILeaseAgentRun

        reason = terminated_reason or self.terminated_reason or "completed"
        elapsed = time.monotonic() - self.wall_clock_start

        run = AILeaseAgentRun.objects.create(
            request_id=self.request_id,
            lease_id=self.lease_id,
            intent=self.intent,
            completed_at=datetime.now(tz=timezone.utc),
            llm_call_count=self.llm_call_count,
            retry_count=self.retry_count,
            wall_clock_seconds=round(elapsed, 4),
            running_cost_usd=Decimal(str(round(self.running_cost_usd, 4))),
            terminated_reason=reason,
            corpus_version=self.corpus_version,
            call_log=[record.__dict__ for record in self._call_log],
            # P0-7 POPIA accountability fields
            template_id=self.template_id,
            created_by_id=self.user_id,
            agency_id=self.agency_id,
            user_message=self.user_message or "",
            document_html_before=self.document_html_before or "",
            document_html_after=self.document_html_after or "",
        )
        return run

    @staticmethod
    def is_truncated_tool_use(
        response: Any, tool_choice: dict[str, Any] | None
    ) -> bool:
        """Detect Anthropic's strict-tool + max_tokens edge case.

        When ``tool_choice={"type":"tool",...}`` forces the model to emit a
        ``tool_use`` block AND the call hits ``max_tokens``, the response
        still has ``stop_reason="max_tokens"`` and exactly one ``tool_use``
        block — but the ``tool_use.input`` is truncated partial-JSON that
        will fail downstream ``json.loads`` / schema validation.

        Callers (Reviewer, anything else using force-tool-choice) should
        check this and treat it as a soft error: bump ``max_tokens`` and
        retry, or escalate. Strict-mode ``additionalProperties: false`` does
        NOT protect against this — strict checks fields, not completeness.
        """
        if tool_choice is None or tool_choice.get("type") != "tool":
            return False
        return getattr(response, "stop_reason", None) == "max_tokens"

    # ── Internals ────────────────────────────────────────────────────── #

    def _enforce_caps_before_call(self) -> None:
        """Pre-call cap enforcement. Raises ``LeaseAgentBudgetExceeded``."""
        # Call cap: a runner with max_calls=2 must allow 2 dispatches and
        # block the 3rd. llm_call_count is post-increment, so the comparison
        # is `>=`.
        if self.llm_call_count >= self.max_calls:
            self.terminated_reason = "cap_calls"
            raise LeaseAgentBudgetExceeded(
                "cap_calls",
                f"llm_call_count={self.llm_call_count} >= max_calls={self.max_calls}",
            )

        elapsed = time.monotonic() - self.wall_clock_start
        if elapsed >= self.max_wallclock_seconds:
            self.terminated_reason = "cap_walltime"
            raise LeaseAgentBudgetExceeded(
                "cap_walltime",
                f"elapsed={elapsed:.3f}s >= max={self.max_wallclock_seconds}s",
            )

        if self.running_cost_usd >= self.max_cost_usd:
            self.terminated_reason = "cap_cost"
            raise LeaseAgentBudgetExceeded(
                "cap_cost",
                f"running_cost_usd=${self.running_cost_usd:.4f} "
                f">= max=${self.max_cost_usd:.4f}",
            )

    def _record_call(
        self, *, agent: str, model: str, response: Any, duration_ms: int
    ) -> None:
        """Update counters + append a ``_CallRecord``."""
        usage = response.usage
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        cache_created = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)

        cost = self._compute_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read=cache_read,
            cache_created=cache_created,
        )

        self.llm_call_count += 1
        self.running_cost_usd += cost
        self._call_log.append(
            _CallRecord(
                agent=agent,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read=cache_read,
                cache_created=cache_created,
                cost_usd=round(cost, 6),
                duration_ms=duration_ms,
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
            )
        )

    def _compute_cost(
        self,
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read: int,
        cache_created: int,
    ) -> float:
        """Return the USD cost for one ``messages.create`` call.

        Notes per the Anthropic pricing model:
          - ``input_tokens`` excludes cache-read and cache-create tokens
            (the SDK already partitions them).
          - cache-write tokens are billed at the "create" rate; reads at
            the "read" rate.
          - unknown model → cost 0.0 with a logged warning, never KeyError.
        """
        pricing = self.PRICING.get(model)
        if pricing is None:
            logger.warning(
                "LeaseAgentRunner: unknown model %r — cost will be reported as 0. "
                "Add to PRICING dict in apps.leases.agent_runner.",
                model,
            )
            return 0.0

        cost = 0.0
        cost += (input_tokens / 1_000_000.0) * pricing["input_per_mtok"]
        cost += (output_tokens / 1_000_000.0) * pricing["output_per_mtok"]
        cost += (cache_read / 1_000_000.0) * pricing["cache_read_per_mtok"]
        cost += (cache_created / 1_000_000.0) * pricing["cache_create_per_mtok"]
        return cost


__all__ = [
    "LeaseAgentBudgetExceeded",
    "LeaseAgentRunner",
    "PRICING",
]
