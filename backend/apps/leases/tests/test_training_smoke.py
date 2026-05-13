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

import tempfile
import textwrap
import unittest
from pathlib import Path

from apps.leases.training.harness import (
    LeaseTrainingHarness,
    Scenario,
    ScenarioConfigError,
)


SCENARIO_PATH = (
    Path(__file__).resolve().parent.parent
    / "training"
    / "fixtures"
    / "happy"
    / "generate-sectional-title-1-tenant-fixed.yaml"
)


class SmokeBatteryTests(unittest.TestCase):
    """Phase 1 Day 1-2: just the one S1 scenario."""

    def test_generate_sectional_title_1_tenant_fixed(self):
        """S1 — canonical happy-path generate, replay mode, zero API spend."""
        self.assertTrue(SCENARIO_PATH.exists(), f"scenario fixture missing: {SCENARIO_PATH}")

        harness = LeaseTrainingHarness(SCENARIO_PATH, mode="replay")
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
        # Wave 2A: the Reviewer now multi-turns with pull tools. The S1
        # cassette records 1 Drafter call + 2 Reviewer turns (auto →
        # query_statute pull tool → auto → submit_audit_report).
        # Front Door is pure Python so doesn't count.
        self.assertEqual(
            result.totals.llm_call_count,
            3,
            "Wave 2A generate scenario should dispatch Drafter + 2 Reviewer turns.",
        )


class CassettePathCanonicalisationTests(unittest.TestCase):
    """Day 3 G.1: cassette is resolved from ``cassettes/<id>__<hash>.jsonl``.

    The Day-1-2 layout co-located the cassette with the YAML; G.1 moves
    it to the canonical path. These tests confirm:

      1. The canonical path is the primary lookup.
      2. A legacy fixture-adjacent cassette is still resolvable via the
         deprecation fallback (until Phase 2 drops it).
    """

    def test_canonical_cassette_path_is_used(self):
        """Cassette MUST live under ``training/cassettes/`` not ``fixtures/``."""
        training_dir = SCENARIO_PATH.parent.parent.parent  # training/
        canonical = (
            training_dir
            / "cassettes"
            / "generate-sectional-title-1-tenant-fixed__day-1-2-stub.jsonl"
        )
        self.assertTrue(
            canonical.exists(),
            f"Day 3 G.1 expects the cassette at the canonical path {canonical}.",
        )
        legacy = (
            SCENARIO_PATH.parent
            / "generate-sectional-title-1-tenant-fixed__day-1-2-stub.jsonl"
        )
        self.assertFalse(
            legacy.exists(),
            f"Legacy fixture-adjacent cassette {legacy} must be relocated.",
        )

        # Harness must run from the canonical path.
        harness = LeaseTrainingHarness(SCENARIO_PATH, mode="replay")
        client = harness._build_cassette_client(
            "generate-sectional-title-1-tenant-fixed"
        )
        self.assertEqual(client.cassette_path, canonical)

    def test_legacy_fallback_resolves_when_canonical_missing(self):
        """If the canonical path is missing AND exactly one
        legacy cassette exists, the harness falls back with a warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            training_dir = tmp / "training"
            fixtures_dir = training_dir / "fixtures" / "happy"
            cassettes_dir = training_dir / "cassettes"
            fixtures_dir.mkdir(parents=True)
            cassettes_dir.mkdir(parents=True)

            # Stage a scenario YAML + a legacy-adjacent cassette ONLY.
            scenario_yaml = fixtures_dir / "scn-legacy.yaml"
            scenario_yaml.write_text(
                SCENARIO_PATH.read_text(encoding="utf-8").replace(
                    "id: generate-sectional-title-1-tenant-fixed",
                    "id: scn-legacy",
                ),
                encoding="utf-8",
            )
            legacy_cassette = fixtures_dir / "scn-legacy__day-1-2-stub.jsonl"
            legacy_cassette.write_text("", encoding="utf-8")

            harness = LeaseTrainingHarness(scenario_yaml, mode="replay")
            client = harness._build_cassette_client("scn-legacy")
            self.assertEqual(client.cassette_path, legacy_cassette)


class AssertionKeyLintTests(unittest.TestCase):
    """Day 3 G.2: misspelled assertion keys must raise at scenario-load
    time, not silently land in a stub branch."""

    def _write_temp_scenario(self, dst_dir: Path, body: str) -> Path:
        path = dst_dir / "scn-temp.yaml"
        path.write_text(body, encoding="utf-8")
        return path

    def test_unknown_assertion_key_raises(self):
        """A misspelled structural key MUST raise ``ScenarioConfigError``."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_body = textwrap.dedent(
                """\
                ---
                id: scn-temp
                title: Bad assertion key
                category: happy
                priority: smoke
                intent: generate
                chat:
                  - role: user
                    content: anything
                assertions:
                  structural:
                    - not_a_real_check: true
                """
            )
            path = self._write_temp_scenario(Path(tmpdir), yaml_body)
            with self.assertRaises(ScenarioConfigError) as ctx:
                Scenario.load(path)
            self.assertIn("not_a_real_check", str(ctx.exception))
            self.assertIn("structural", str(ctx.exception))

    def test_unknown_assertion_under_stub_category_emits_warning(self):
        """Stub categories accept any key but warn via logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_body = textwrap.dedent(
                """\
                ---
                id: scn-temp
                title: Stub assertion key
                category: happy
                priority: smoke
                intent: generate
                chat:
                  - role: user
                    content: anything
                assertions:
                  reviewer_pipeline:
                    - some_future_check: true
                """
            )
            path = self._write_temp_scenario(Path(tmpdir), yaml_body)
            # Should NOT raise — stub categories don't lint keys.
            with self.assertLogs(
                "apps.leases.training.harness", level="WARNING"
            ) as captured:
                scenario = Scenario.load(path)
            self.assertEqual(scenario.id, "scn-temp")
            self.assertTrue(
                any("stub category" in m for m in captured.output),
                f"Expected stub-category warning, got: {captured.output}",
            )

    def test_known_assertion_keys_load_cleanly(self):
        """The canonical S1 scenario loads without raising (sanity check)."""
        scenario = Scenario.load(SCENARIO_PATH)
        self.assertEqual(scenario.id, "generate-sectional-title-1-tenant-fixed")
