"""Scenario-run result types.

The result file shape is locked at §5.3 of
``content/cto/lease-ai-testing-and-training-plan.md``. Day 1-2 emits a
subset — the trainer/diagnostic blocks land in Phase 3.

Every run produces one ``ScenarioResult``. The harness serialises it to
JSON and writes one file per run under
``content/cto/training/runs/<iso8601>__<scenario_id>.json``.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from apps.leases.training.assertions import AssertionResult


SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ScenarioTotals:
    """Aggregated runner-level metrics for one scenario run.

    Mirrors the ``totals`` block of the result file schema at §5.3 of the
    plan. Cost is plain float (not ``Decimal``) because this is for
    diagnostic comparisons, not accounting; the persisted
    ``AILeaseAgentRun`` row holds the authoritative ``Decimal`` cost.
    """

    llm_call_count: int
    input_tokens: int
    output_tokens: int
    cache_read: int
    cost_usd: float
    retry_count: int
    terminated_reason: str


@dataclass
class ScenarioResult:
    """Result of one ``LeaseTrainingHarness.run()`` call.

    Verdict is ``pass`` iff every assertion in ``assertion_results`` has
    ``passed=True``. Day 1-2 only populates ``structural`` and
    ``citation_correctness`` with real checks; the other three categories
    receive stub ``AssertionResult`` entries with
    ``detail="skipped — Phase 1 Day 1-2 stub"``.
    """

    scenario_id: str
    run_id: str
    mode: str
    corpus_version: str
    started_at: str
    duration_seconds: float
    verdict: str  # "pass" | "fail"
    totals: ScenarioTotals
    call_log: list[dict[str, Any]] = field(default_factory=list)
    assertion_results: dict[str, list[AssertionResult]] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_jsonable(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict suitable for ``json.dump``.

        ``AssertionResult`` is frozen so its ``asdict`` is well-defined.
        Cost is rounded to 6 decimal places for stable diffs.
        """
        totals = asdict(self.totals)
        totals["cost_usd"] = round(totals["cost_usd"], 6)
        return {
            "schema_version": self.schema_version,
            "scenario_id": self.scenario_id,
            "run_id": self.run_id,
            "mode": self.mode,
            "corpus_version": self.corpus_version,
            "started_at": self.started_at,
            "duration_seconds": round(self.duration_seconds, 4),
            "verdict": self.verdict,
            "totals": totals,
            "call_log": list(self.call_log),
            "assertion_results": {
                category: [asdict(r) for r in results]
                for category, results in self.assertion_results.items()
            },
        }

    def write(self, path: Any) -> None:
        """Write the result file to ``path`` (str or ``pathlib.Path``)."""
        from pathlib import Path

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_jsonable(), f, indent=2, sort_keys=False)
            f.write("\n")

    @classmethod
    def from_jsonable(cls, payload: dict[str, Any]) -> "ScenarioResult":
        """Rehydrate from a previously-written result-file dict."""
        totals = ScenarioTotals(**payload["totals"])
        assertion_results: dict[str, list[AssertionResult]] = {}
        for category, items in payload.get("assertion_results", {}).items():
            assertion_results[category] = [AssertionResult(**item) for item in items]
        return cls(
            scenario_id=payload["scenario_id"],
            run_id=payload["run_id"],
            mode=payload["mode"],
            corpus_version=payload["corpus_version"],
            started_at=payload["started_at"],
            duration_seconds=float(payload["duration_seconds"]),
            verdict=payload["verdict"],
            totals=totals,
            call_log=list(payload.get("call_log", [])),
            assertion_results=assertion_results,
            schema_version=payload.get("schema_version", SCHEMA_VERSION),
        )


__all__ = ["ScenarioResult", "ScenarioTotals", "SCHEMA_VERSION"]
