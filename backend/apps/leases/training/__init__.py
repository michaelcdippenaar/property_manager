"""Lease-AI training harness package.

Phase 1 Day 1-2 scaffold per
``content/cto/lease-ai-testing-and-training-plan.md`` §16.

Public surface:
    - ``LeaseTrainingHarness`` — orchestrates one scenario run.
    - ``ScenarioResult`` — the JSON-serialisable result emitted per run.
    - ``AssertionResult`` — one assertion's verdict.
    - ``CassetteAnthropicClient`` — record/replay wrapper around
      ``anthropic.Anthropic``.
    - ``CassetteMissError`` — raised in replay mode when no cassette line
      matches the request hash.

The training package is NOT a pytest discovery target by directory name.
Smoke battery entry point is ``apps.leases.tests.test_training_smoke``.
"""
from __future__ import annotations

from apps.leases.training.assertions import AssertionResult
from apps.leases.training.cassette import (
    CassetteAnthropicClient,
    CassetteMissError,
)
from apps.leases.training.harness import LeaseTrainingHarness
from apps.leases.training.result import ScenarioResult

__all__ = [
    "AssertionResult",
    "CassetteAnthropicClient",
    "CassetteMissError",
    "LeaseTrainingHarness",
    "ScenarioResult",
]
