"""Day 1-2 smoke battery — ONE scenario.

Phase 1 Day 1-2 entry point per plan §16. The full battery (7 happy +
1 adversarial) lands on Day 3+; today this just proves the harness +
cassette + assertion round-trip works for the canonical S1 scenario.

The test inherits from ``unittest.TestCase`` rather than
``django.test.TestCase`` because the Day-1-2 harness only calls
``LeaseAgentRunner.dispatch`` (not ``finalize``) — no DB row is
created. Skipping DB setup keeps the smoke battery fast and decoupled
from migrations state.

Run:
    cd backend && .venv/bin/python manage.py test \\
        apps.leases.tests.test_training_smoke -v 2

or via pytest:
    cd backend && .venv/bin/python -m pytest \\
        apps/leases/tests/test_training_smoke.py -v --no-cov
"""
from __future__ import annotations

import unittest
from pathlib import Path

from apps.leases.training.harness import LeaseTrainingHarness


class SmokeBatteryTests(unittest.TestCase):
    """Phase 1 Day 1-2: just the one S1 scenario."""

    def test_generate_sectional_title_1_tenant_fixed(self):
        """S1 — canonical happy-path generate, replay mode, zero API spend."""
        scenario = (
            Path(__file__).resolve().parent.parent
            / "training"
            / "fixtures"
            / "happy"
            / "generate-sectional-title-1-tenant-fixed.yaml"
        )
        self.assertTrue(scenario.exists(), f"scenario fixture missing: {scenario}")

        harness = LeaseTrainingHarness(scenario, mode="replay")
        result = harness.run()

        # If anything failed, show the failure detail so the test output
        # is actionable rather than a bare assertion error.
        failed = [
            r
            for results in result.assertion_results.values()
            for r in results
            if not r.passed
        ]
        self.assertEqual(
            result.verdict,
            "pass",
            f"Smoke scenario failed. Failures: {[f.__dict__ for f in failed]}",
        )
        # Sanity: at least one LLM dispatch happened (i.e. the cassette
        # actually fed a response back to the runner).
        self.assertEqual(
            result.totals.llm_call_count,
            1,
            "Day 1-2 scenario should dispatch exactly one Drafter call.",
        )
