"""Tests for ``apps.leases.agent_runner.LeaseAgentRunner``.

Covers the budget caps and audit-decision logic locked in
``docs/system/lease-ai-agent-architecture.md`` decisions 10, 20, 24 and §7.3.

Run:
    cd backend && .venv/bin/python manage.py test \
        apps.leases.tests.test_agent_runner -v 2
"""
from __future__ import annotations

import time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import TestCase

from apps.leases.agent_runner import (
    LeaseAgentBudgetExceeded,
    LeaseAgentRunner,
)
from apps.leases.models import AILeaseAgentRun


def _fake_response(
    *,
    input_tokens: int = 100,
    output_tokens: int = 50,
    cache_read: int = 0,
    cache_created: int = 0,
) -> SimpleNamespace:
    """Build a fake Anthropic ``Message`` with the usage shape we read."""
    return SimpleNamespace(
        id="msg_test",
        content=[],
        stop_reason="end_turn",
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_input_tokens=cache_read,
            cache_creation_input_tokens=cache_created,
        ),
    )


def _build_runner(
    *,
    request_id: str = "req-test-abc123",
    intent: str = "generate",
    max_calls: int | None = None,
    max_wallclock_seconds: float | None = None,
    max_retries: int | None = None,
    max_cost_usd: float | None = None,
    response_factory=None,
) -> tuple[LeaseAgentRunner, MagicMock]:
    """Construct a runner with a mocked anthropic client.

    The mocked client's ``messages.create`` returns ``response_factory()`` per
    call (or a default fake response).
    """
    client = MagicMock()
    factory = response_factory or _fake_response
    client.messages.create.side_effect = lambda **kw: factory()

    runner = LeaseAgentRunner(
        request_id=request_id,
        intent=intent,
        anthropic_client=client,
        lease_id=None,
        max_calls=max_calls,
        max_wallclock_seconds=max_wallclock_seconds,
        max_retries=max_retries,
        max_cost_usd=max_cost_usd,
    )
    return runner, client


def _dispatch_once(runner: LeaseAgentRunner) -> None:
    """Convenience helper that issues a minimal dispatch."""
    runner.dispatch(
        agent="drafter",
        model="claude-sonnet-4-5",
        messages=[{"role": "user", "content": "hi"}],
        system=[{"type": "text", "text": "persona"}],
    )


class DispatchCountingTests(TestCase):
    """Decision 20 — every dispatch ticks ``llm_call_count``."""

    def test_dispatch_counts_calls(self):
        runner, _client = _build_runner()
        _dispatch_once(runner)
        _dispatch_once(runner)
        _dispatch_once(runner)
        self.assertEqual(runner.llm_call_count, 3)


class CostTrackingTests(TestCase):
    """Decision 23 + decision 20 — running cost matches the pricing table."""

    def test_dispatch_tracks_cost(self):
        # 1000 input, 500 output on Sonnet:
        #   input  = 1000 / 1e6 * $3.00 = $0.003
        #   output =  500 / 1e6 * $15.00 = $0.0075
        # Total expected = $0.0105
        runner, _client = _build_runner(
            response_factory=lambda: _fake_response(
                input_tokens=1000, output_tokens=500
            ),
        )
        _dispatch_once(runner)
        self.assertAlmostEqual(runner.running_cost_usd, 0.0105, places=6)

    def test_cache_read_priced_below_input(self):
        # Cache-read at $0.30/Mtok vs input $3.00/Mtok — should be 10x cheaper.
        runner, _ = _build_runner(
            response_factory=lambda: _fake_response(
                input_tokens=0, output_tokens=0, cache_read=1_000_000
            ),
        )
        _dispatch_once(runner)
        # 1Mtok cache_read on Sonnet = $0.30
        self.assertAlmostEqual(runner.running_cost_usd, 0.30, places=4)

    def test_unknown_model_costs_zero_but_does_not_raise(self):
        runner, _ = _build_runner()
        runner.dispatch(
            agent="drafter",
            model="claude-experimental-vapor",
            messages=[{"role": "user", "content": "hi"}],
            system=[{"type": "text", "text": "persona"}],
        )
        self.assertEqual(runner.running_cost_usd, 0.0)
        self.assertEqual(runner.llm_call_count, 1)


class BudgetCapTests(TestCase):
    """Decision 10 — caps enforced before each call."""

    def test_cap_calls_raises(self):
        runner, _client = _build_runner(max_calls=2)
        _dispatch_once(runner)
        _dispatch_once(runner)
        with self.assertRaises(LeaseAgentBudgetExceeded) as ctx:
            _dispatch_once(runner)
        self.assertEqual(ctx.exception.terminated_reason, "cap_calls")
        self.assertEqual(runner.terminated_reason, "cap_calls")
        # Third call must NOT have hit the wire.
        self.assertEqual(runner.llm_call_count, 2)

    def test_cap_walltime_raises(self):
        runner, _client = _build_runner(max_wallclock_seconds=0.05)
        # Sleep past the walltime cap; the next dispatch must abort.
        time.sleep(0.07)
        with self.assertRaises(LeaseAgentBudgetExceeded) as ctx:
            _dispatch_once(runner)
        self.assertEqual(ctx.exception.terminated_reason, "cap_walltime")
        self.assertEqual(runner.terminated_reason, "cap_walltime")

    def test_cap_cost_raises(self):
        # Each call costs ~$0.6 (expensive mock).
        # max_cost_usd=0.001 should trip on call #2.
        runner, _client = _build_runner(
            max_cost_usd=0.001,
            response_factory=lambda: _fake_response(
                input_tokens=100_000, output_tokens=20_000
            ),
        )
        _dispatch_once(runner)  # First call goes through; cost lands above cap.
        with self.assertRaises(LeaseAgentBudgetExceeded) as ctx:
            _dispatch_once(runner)
        self.assertEqual(ctx.exception.terminated_reason, "cap_cost")
        self.assertEqual(runner.terminated_reason, "cap_cost")


class ShouldRetryTests(TestCase):
    """Decision 24 — retry only on blocking findings + spare retry budget."""

    def test_should_retry_true_on_blocking(self):
        runner, _ = _build_runner(max_retries=1)
        report = {
            "verdict": "revise_required",
            "summary": "...",
            "statute_findings": [
                {"citation": "RHA s5(3)(f)", "severity": "blocking", "message": "..."},
                {"citation": "RHA s4A", "severity": "recommended", "message": "..."},
            ],
        }
        self.assertTrue(runner.should_retry(report))

    def test_should_retry_false_on_nice_to_have(self):
        runner, _ = _build_runner(max_retries=1)
        report = {
            "verdict": "pass",
            "summary": "...",
            "statute_findings": [
                {"citation": "RHA s5(3)(f)", "severity": "nice_to_have", "message": "..."},
                {"citation": "RHA s4A", "severity": "recommended", "message": "..."},
            ],
        }
        self.assertFalse(runner.should_retry(report))

    def test_should_retry_false_when_retry_cap_hit(self):
        runner, _ = _build_runner(max_retries=1)
        runner.retry_count = 1  # already used the only retry
        report = {
            "verdict": "revise_required",
            "summary": "...",
            "statute_findings": [
                {"citation": "RHA s5(3)(f)", "severity": "blocking", "message": "..."},
            ],
        }
        self.assertFalse(runner.should_retry(report))

    def test_should_retry_false_on_none_report(self):
        runner, _ = _build_runner()
        self.assertFalse(runner.should_retry(None))

    def test_should_retry_picks_blocking_from_format_findings(self):
        # Even if statute_findings is empty, a blocking format finding triggers retry.
        runner, _ = _build_runner(max_retries=1)
        report = {
            "verdict": "revise_required",
            "summary": "...",
            "statute_findings": [],
            "format_findings": [
                {"section": "S", "severity": "blocking", "message": "h3 instead of h2"},
            ],
        }
        self.assertTrue(runner.should_retry(report))


class FinalizeTests(TestCase):
    """§7.3 — ``finalize()`` persists an ``AILeaseAgentRun`` row."""

    def test_finalize_persists_run(self):
        runner, _ = _build_runner(
            request_id="req-finalize-001",
            intent="generate",
            response_factory=lambda: _fake_response(
                input_tokens=1000, output_tokens=500
            ),
        )
        runner.corpus_version = "rag-v1.0-abc1234"
        _dispatch_once(runner)
        _dispatch_once(runner)

        run = runner.finalize(terminated_reason="completed")

        self.assertIsInstance(run, AILeaseAgentRun)
        self.assertEqual(run.request_id, "req-finalize-001")
        self.assertEqual(run.intent, "generate")
        self.assertEqual(run.llm_call_count, 2)
        self.assertEqual(run.retry_count, 0)
        self.assertEqual(run.terminated_reason, "completed")
        self.assertEqual(run.corpus_version, "rag-v1.0-abc1234")
        self.assertIsNotNone(run.completed_at)
        self.assertGreater(run.wall_clock_seconds, 0)
        # 2 dispatches at $0.0105 each → $0.0210.
        self.assertEqual(run.running_cost_usd, Decimal("0.0210"))
        # Reading back from the DB confirms persistence.
        from_db = AILeaseAgentRun.objects.get(pk=run.pk)
        self.assertEqual(from_db.request_id, "req-finalize-001")

    def test_finalize_uses_cap_reason_when_already_set(self):
        runner, _ = _build_runner(
            request_id="req-finalize-cap-002", max_calls=1
        )
        _dispatch_once(runner)
        with self.assertRaises(LeaseAgentBudgetExceeded):
            _dispatch_once(runner)
        # finalize() with no override should pick up cap_calls from the runner.
        run = runner.finalize()
        self.assertEqual(run.terminated_reason, "cap_calls")


class CallLogTests(TestCase):
    """``call_log`` is appended per dispatch with the right keys."""

    def test_call_log_is_appended_per_dispatch(self):
        runner, _ = _build_runner(
            request_id="req-calllog-003",
            response_factory=lambda: _fake_response(
                input_tokens=200, output_tokens=80, cache_read=120
            ),
        )
        _dispatch_once(runner)
        _dispatch_once(runner)
        _dispatch_once(runner)

        run = runner.finalize(terminated_reason="completed")
        self.assertEqual(len(run.call_log), 3)

        expected_keys = {
            "agent",
            "model",
            "input_tokens",
            "output_tokens",
            "cache_read",
            "cache_created",
            "cost_usd",
            "duration_ms",
            "timestamp",
        }
        for entry in run.call_log:
            self.assertEqual(set(entry.keys()), expected_keys)
            self.assertEqual(entry["agent"], "drafter")
            self.assertEqual(entry["model"], "claude-sonnet-4-5")
            self.assertEqual(entry["input_tokens"], 200)
            self.assertEqual(entry["cache_read"], 120)
            self.assertIsInstance(entry["timestamp"], str)
            self.assertGreater(entry["cost_usd"], 0)


class TruncatedToolUseTests(TestCase):
    """``is_truncated_tool_use`` — detect strict-tool + max_tokens edge case.

    See ``backend/scripts/spikes/strict_tool_spike.py`` for the live-API
    confirmation that forced tool_choice can hit max_tokens with a
    truncated partial-JSON ``tool_use.input`` that schema-validation does
    NOT catch.
    """

    FORCE_TOOL = {"type": "tool", "name": "submit_audit_report"}

    def test_truncated_on_forced_tool_with_max_tokens_stop(self):
        resp = SimpleNamespace(stop_reason="max_tokens", content=[], usage=None)
        self.assertTrue(LeaseAgentRunner.is_truncated_tool_use(resp, self.FORCE_TOOL))

    def test_not_truncated_on_normal_stop_reason(self):
        resp = SimpleNamespace(stop_reason="tool_use", content=[], usage=None)
        self.assertFalse(LeaseAgentRunner.is_truncated_tool_use(resp, self.FORCE_TOOL))

    def test_not_truncated_without_tool_choice(self):
        """max_tokens on a non-forced-tool call is a normal stream cutoff."""
        resp = SimpleNamespace(stop_reason="max_tokens", content=[], usage=None)
        self.assertFalse(LeaseAgentRunner.is_truncated_tool_use(resp, None))

    def test_not_truncated_on_tool_choice_auto(self):
        """tool_choice={'type': 'auto'} doesn't force; same as None."""
        resp = SimpleNamespace(stop_reason="max_tokens", content=[], usage=None)
        self.assertFalse(
            LeaseAgentRunner.is_truncated_tool_use(resp, {"type": "auto"})
        )
