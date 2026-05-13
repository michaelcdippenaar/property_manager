"""``manage.py train_lease_agent`` — Day 1-2 single-scenario runner.

Per plan §5.1 / §16 Phase 1 Day 1-2 scope:

    --scenario=<id>   (required)
    --replay (default) / --record / --live
    --format=text|json
    --output=<path>   (default: content/cto/training/runs/<iso8601>__<scenario>.json)

Phase 1 Day 3+ adds ``--battery`` and Phase 2 adds ``--judge``.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.leases.training.cassette import CassetteMissError
from apps.leases.training.harness import LeaseTrainingHarness
from apps.leases.training.result import ScenarioResult


def _resolve_scenario_path(scenario_id: str) -> Path:
    """Find ``<scenario_id>.yaml`` under any fixtures/ subcategory."""
    fixtures_root = (
        Path(settings.BASE_DIR) / "apps" / "leases" / "training" / "fixtures"
    )
    # Day 1-2 only has fixtures/happy/, but iter every subdir for forward
    # compatibility (regression/, adversarial/).
    for child in fixtures_root.glob(f"**/{scenario_id}.yaml"):
        return child
    raise CommandError(
        f"Scenario {scenario_id!r} not found under {fixtures_root}. "
        f"Expected file: <fixtures>/<category>/{scenario_id}.yaml."
    )


def _default_output_path(scenario_id: str) -> Path:
    """Build ``content/cto/training/runs/<iso8601>__<scenario>.json``."""
    repo_root = Path(settings.BASE_DIR).parent
    stamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    return (
        repo_root / "content" / "cto" / "training" / "runs"
        / f"{stamp}__{scenario_id}.json"
    )


def _build_live_client():
    """Construct an ``anthropic.Anthropic`` for record/live mode.

    Reads ``ANTHROPIC_API_KEY`` from env. Falls back to nothing — the
    caller already knows whether record/live mode is appropriate.
    """
    try:
        import anthropic
    except ImportError as exc:
        raise CommandError(
            "anthropic SDK not installed in this venv. Required for record/live."
        ) from exc
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise CommandError(
            "ANTHROPIC_API_KEY not set; required for --record / --live."
        )
    return anthropic.Anthropic(api_key=api_key, timeout=30.0)


# ── Stdout renderers ─────────────────────────────────────────────────── #


def _render_text(result: ScenarioResult) -> str:
    """Plan §5.2-style human-friendly markdown summary."""
    lines: list[str] = []
    lines.append(f"Scenario: {result.scenario_id}")
    lines.append(f"  Mode:           {result.mode}")
    lines.append(f"  Corpus version: {result.corpus_version}")
    lines.append(f"  Started:        {result.started_at}")
    lines.append("")
    lines.append("Pipeline trace:")
    if not result.call_log:
        lines.append("  (no LLM dispatches recorded)")
    for entry in result.call_log:
        lines.append(
            f"  {entry.get('agent', '?')} call  "
            f"{entry.get('model', '?')}  "
            f"input={entry.get('input_tokens', 0)}  "
            f"output={entry.get('output_tokens', 0)}  "
            f"cache_read={entry.get('cache_read', 0)}  "
            f"{entry.get('duration_ms', 0)}ms  "
            f"${entry.get('cost_usd', 0.0):.4f}"
        )
    totals = result.totals
    lines.append("")
    lines.append(
        f"  Totals: {totals.llm_call_count} calls, "
        f"{result.duration_seconds:.2f}s, "
        f"${totals.cost_usd:.4f}, retry={totals.retry_count}"
    )
    lines.append("")
    lines.append("Assertions:")
    for category, items in result.assertion_results.items():
        total = len(items)
        passed = sum(1 for r in items if r.passed)
        verdict = "PASS" if passed == total else "FAIL"
        lines.append(f"  {category.upper():<30} {passed:>2}/{total:<2} {verdict}")
        for r in items:
            if not r.passed:
                lines.append(f"    - {r.name}: {r.detail}")
    lines.append("")
    lines.append(
        f"OVERALL: {result.verdict.upper()}  "
        f"duration={result.duration_seconds:.2f}s  "
        f"cost=${totals.cost_usd:.4f}"
    )
    return "\n".join(lines)


def _render_json(result: ScenarioResult) -> str:
    """Compact-pretty JSON of the full result."""
    return json.dumps(result.to_jsonable(), indent=2, sort_keys=False)


# ── Command ──────────────────────────────────────────────────────────── #


class Command(BaseCommand):
    help = (
        "Run one lease-AI training scenario through the Day-1-2 harness. "
        "Per plan §5.1 / §16."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--scenario", required=True,
            help="Scenario ID (filename without .yaml).",
        )
        mode_group = parser.add_mutually_exclusive_group()
        mode_group.add_argument(
            "--replay", action="store_const", const="replay", dest="mode",
            help="Cassette replay (default). Zero API spend.",
        )
        mode_group.add_argument(
            "--record", action="store_const", const="record", dest="mode",
            help="Forward to live client, append to cassette.",
        )
        mode_group.add_argument(
            "--live", action="store_const", const="live", dest="mode",
            help="Live API call without recording.",
        )
        parser.set_defaults(mode="replay")
        parser.add_argument(
            "--format", choices=("text", "json"), default="text",
            help="Stdout format. Default: text.",
        )
        parser.add_argument(
            "--output", default=None,
            help=(
                "Path to write the result JSON file. Default: "
                "content/cto/training/runs/<iso8601>__<scenario>.json"
            ),
        )
        parser.add_argument(
            "--corpus-hash", default=None,
            help=(
                "Override the corpus hash used to resolve the cassette path "
                "(cassettes/<scenario>__<corpus_hash>.jsonl). Default: "
                "'day-1-2-stub' until the legal_rag indexer lands."
            ),
        )

    def handle(self, *args, **options):
        scenario_id: str = options["scenario"]
        mode: str = options["mode"]
        fmt: str = options["format"]

        scenario_path = _resolve_scenario_path(scenario_id)
        output_path = Path(options["output"]) if options["output"] else (
            _default_output_path(scenario_id)
        )

        live_client: Any | None = None
        if mode in ("record", "live"):
            live_client = _build_live_client()

        harness = LeaseTrainingHarness(
            scenario_path,
            mode=mode,  # type: ignore[arg-type]
            anthropic_client=live_client,
            corpus_hash=options.get("corpus_hash"),
        )

        try:
            result = harness.run()
        except CassetteMissError as exc:
            raise CommandError(
                f"Cassette miss for {scenario_id} (hash={exc.request_hash[:12]}). "
                f"{exc.hint}"
            ) from exc

        result.write(output_path)

        if fmt == "json":
            self.stdout.write(_render_json(result))
        else:
            self.stdout.write(_render_text(result))
        self.stdout.write("")
        self.stdout.write(f"Result file: {output_path}")

        if result.verdict != "pass":
            sys.exit(2)
