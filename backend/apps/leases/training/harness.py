"""Lease-AI training harness orchestrator.

Per plan §16 Phase 1 Day 1-2: load a scenario YAML, dispatch ONE Drafter
call through ``LeaseAgentRunner`` wrapped by ``CassetteAnthropicClient``,
run the Day-1-2 subset of assertions, and emit a ``ScenarioResult``.

The pipeline beyond a single Drafter call (Front Door → Drafter →
Reviewer → Formatter) lands in Phase 2. The Day-1-2 harness exists to
prove the cassette + assertion + result-file round-trip works.

Module shape:
    - ``Scenario`` — parsed YAML fixture.
    - ``LeaseTrainingHarness.run()`` — single public entry point.

Anthropic client construction is lazy and optional. In replay mode
(default) no live client is needed; the cassette client raises
``CassetteMissError`` if the recorded hash does not match. In record/live
mode the caller passes ``anthropic_client=anthropic.Anthropic(...)``.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import yaml

from apps.leases.agent_runner import LeaseAgentRunner
from apps.leases.training import assertions as A
from apps.leases.training.assertions import AssertionResult
from apps.leases.training.cassette import (
    DAY_1_2_CORPUS_HASH,
    CassetteAnthropicClient,
)
from apps.leases.training.result import ScenarioResult, ScenarioTotals

if TYPE_CHECKING:
    import anthropic

logger = logging.getLogger(__name__)


# ── Scenario container ───────────────────────────────────────────────── #


@dataclass
class Scenario:
    """In-memory representation of one scenario YAML fixture.

    Only the fields the Day-1-2 harness actually consumes are typed.
    Extra YAML keys land in ``raw`` for later phases (e.g. ``rubric_id``
    for the Phase 2 judge) without forcing schema churn now.
    """

    id: str
    title: str
    category: str            # happy | regression | adversarial
    priority: str            # smoke | full | nightly_only
    intent: str
    context: dict[str, Any]
    parties: dict[str, Any]
    property: dict[str, Any]
    dates: dict[str, Any]
    chat: list[dict[str, Any]]
    assertions_block: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "Scenario":
        """Parse a scenario YAML file. Raises ``ValueError`` on bad shape."""
        with open(path, "r", encoding="utf-8") as f:
            payload = yaml.safe_load(f) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"Scenario {path} did not parse to a mapping")
        try:
            return cls(
                id=str(payload["id"]),
                title=str(payload["title"]),
                category=str(payload["category"]),
                priority=str(payload.get("priority", "smoke")),
                intent=str(payload["intent"]),
                context=dict(payload.get("context") or {}),
                parties=dict(payload.get("parties") or {}),
                property=dict(payload.get("property") or {}),
                dates=dict(payload.get("dates") or {}),
                chat=list(payload.get("chat") or []),
                assertions_block=dict(payload.get("assertions") or {}),
                raw=payload,
            )
        except KeyError as exc:
            raise ValueError(
                f"Scenario {path} missing required field {exc}"
            ) from exc


# ── Harness ──────────────────────────────────────────────────────────── #


HarnessMode = Literal["replay", "record", "live"]


# Drafter model name — matches the cache_hit_spike default. Phase 2 will
# read this from ``settings.LEASE_AI_DRAFTER_MODEL``.
DRAFTER_MODEL_DEFAULT = "claude-sonnet-4-5"


class LeaseTrainingHarness:
    """Run one scenario end-to-end and return a ``ScenarioResult``.

    Day 1-2 scope:
      1. Load + validate scenario YAML.
      2. Construct a ``CassetteAnthropicClient`` wrapping the optional
         live ``anthropic.Anthropic`` client.
      3. Build a ``LeaseAgentRunner`` with the cassette client.
      4. Dispatch ONE Drafter call (Front Door / Reviewer / Formatter
         are Phase 2).
      5. Run the Day-1-2 assertion subset (structural +
         citation_correctness real; reviewer_pipeline +
         cost_and_latency + semantic stubbed).
      6. Build + return a ``ScenarioResult``.
    """

    def __init__(
        self,
        scenario_path: Path | str,
        *,
        mode: HarnessMode = "replay",
        judge_enabled: bool = False,
        anthropic_client: "anthropic.Anthropic | None" = None,
        corpus_hash: str | None = None,
    ):
        self.scenario_path = Path(scenario_path)
        self.mode = mode
        self.judge_enabled = judge_enabled
        self._anthropic_client = anthropic_client
        # Day 1-2: corpus hash is a placeholder. Phase A of the legal
        # RAG plan replaces this with the real
        # ``LeaseLawCorpusVersion.fingerprint`` (architecture doc §6.3).
        self.corpus_hash = corpus_hash or DAY_1_2_CORPUS_HASH

        if judge_enabled:
            logger.info(
                "LeaseTrainingHarness: judge_enabled=True but Day 1-2 stubs "
                "the semantic assertions. Phase 2 wires judge.py."
            )

    # ── Public surface ──────────────────────────────────────────────── #

    def run(self) -> ScenarioResult:
        """Execute one scenario end-to-end. Returns the result."""
        scenario = Scenario.load(self.scenario_path)

        run_id = self._build_run_id(scenario.id)
        started_at = datetime.now(tz=timezone.utc).isoformat()
        t0 = time.monotonic()

        cassette_client = self._build_cassette_client(scenario.id)

        runner = LeaseAgentRunner(
            request_id=run_id,
            intent=scenario.intent,
            anthropic_client=cassette_client,
            lease_id=None,
            corpus_version=self.corpus_hash,
        )

        rendered_html, call_responses = self._run_pipeline(
            runner=runner, scenario=scenario
        )

        duration = time.monotonic() - t0

        assertion_results = self._run_assertions(
            scenario=scenario, rendered_html=rendered_html
        )
        verdict = self._compute_verdict(assertion_results)

        totals = self._build_totals(runner=runner)
        call_log = [record.__dict__ for record in runner._call_log]

        return ScenarioResult(
            scenario_id=scenario.id,
            run_id=run_id,
            mode=self.mode,
            corpus_version=self.corpus_hash,
            started_at=started_at,
            duration_seconds=duration,
            verdict=verdict,
            totals=totals,
            call_log=call_log,
            assertion_results=assertion_results,
        )

    # ── Internals ───────────────────────────────────────────────────── #

    def _build_run_id(self, scenario_id: str) -> str:
        """Stable run ID: ISO8601 UTC + short uuid + scenario."""
        stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"{stamp}__{scenario_id}__{uuid.uuid4().hex[:8]}"

    def _build_cassette_client(self, scenario_id: str) -> CassetteAnthropicClient:
        """Resolve cassette path + construct the wrapper."""
        cassette_dir = (
            Path(__file__).resolve().parent / "fixtures" / "happy"
        )
        # Day 1-2 keeps cassette adjacent to its scenario fixture for
        # easy discovery; Phase 2 standardises on cassettes/<id>__<hash>.jsonl
        # per plan §6.2.
        cassette_path = cassette_dir / f"{scenario_id}__{self.corpus_hash}.jsonl"
        return CassetteAnthropicClient(
            scenario_id=scenario_id,
            cassette_path=cassette_path,
            mode=self.mode,  # type: ignore[arg-type]
            live_client=self._anthropic_client,
        )

    def _run_pipeline(
        self, *, runner: LeaseAgentRunner, scenario: Scenario
    ) -> tuple[str, list[Any]]:
        """Day 1-2 pipeline: ONE Drafter dispatch.

        Phase 2 of the testing plan reshapes this into the four-agent
        cluster (Front Door → Drafter → Reviewer → Formatter). For now
        we make the minimal call that proves the cassette + runner +
        assertion round-trip works.

        Returns ``(rendered_html, responses)`` where ``rendered_html`` is
        the text extracted from the final response and ``responses`` is
        the list of SDK ``Message`` objects (rehydrated namespaces in
        replay mode).
        """
        messages = self._build_messages(scenario)
        system = self._build_system_block(scenario)

        response = runner.dispatch(
            agent="drafter",
            model=DRAFTER_MODEL_DEFAULT,
            messages=messages,
            system=system,
        )

        rendered_html = self._extract_text(response)
        return rendered_html, [response]

    def _build_system_block(self, scenario: Scenario) -> list[dict[str, Any]]:
        """Construct a minimal Drafter system prompt.

        The real Phase 2 system block is assembled from PERSONA_DRAFTER +
        MERGE_FIELDS_BLOCK + RAG_CHUNKS_BLOCK with cache_control markers
        on each. Day 1-2 stays minimal — the cassette client matches on
        the hash of whatever we send here, so any change requires a
        cassette re-record.
        """
        return [
            {
                "type": "text",
                "text": (
                    "You are the lease-AI Drafter. Day 1-2 scaffold call. "
                    f"Scenario={scenario.id}. Intent={scenario.intent}. "
                    "Return rendered lease HTML."
                ),
            }
        ]

    def _build_messages(self, scenario: Scenario) -> list[dict[str, Any]]:
        """Convert the scenario ``chat`` block to ``messages.create`` form.

        The scenario's chat is already roughly in API shape — role +
        content. We just normalise the content into a plain string.
        """
        out: list[dict[str, Any]] = []
        for turn in scenario.chat:
            role = str(turn.get("role", "user"))
            content = turn.get("content", "")
            if isinstance(content, list):
                content_str = "\n".join(str(c) for c in content)
            else:
                content_str = str(content).strip()
            out.append({"role": role, "content": content_str})
        if not out:
            out.append({"role": "user", "content": "Generate the lease."})
        return out

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Concatenate every ``text`` block from a response.

        Tool-use blocks are ignored — the harness's Day-1-2 assertions
        run against the rendered prose. Phase 2 will inspect tool calls
        separately for the structural-tool assertions.
        """
        chunks: list[str] = []
        for block in getattr(response, "content", []) or []:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text = getattr(block, "text", "")
                if isinstance(text, str):
                    chunks.append(text)
        return "".join(chunks)

    def _run_assertions(
        self, *, scenario: Scenario, rendered_html: str
    ) -> dict[str, list[AssertionResult]]:
        """Map scenario assertions block to AssertionResult lists."""
        block = scenario.assertions_block
        structural = self._run_structural(block.get("structural"), rendered_html)
        citation = self._run_citation(
            block.get("citation_correctness"), rendered_html
        )
        reviewer = self._stub_category(
            block.get("reviewer_pipeline"), A.stub_reviewer_pipeline
        )
        cost = self._stub_category(
            block.get("cost_and_latency"), A.stub_cost_and_latency
        )
        semantic = self._stub_category(block.get("semantic"), A.stub_semantic)
        return {
            "structural": structural,
            "citation_correctness": citation,
            "reviewer_pipeline": reviewer,
            "cost_and_latency": cost,
            "semantic": semantic,
        }

    @staticmethod
    def _run_structural(
        items: list[Any] | None, rendered_html: str
    ) -> list[AssertionResult]:
        """Dispatch each structural assertion. Unknown keys → skipped stub.

        Each item in the YAML's ``structural`` list is a single-key
        mapping (e.g. ``{no_placeholder_text: true}``). We unwrap and
        route to the implementing function.
        """
        out: list[AssertionResult] = []
        for raw in items or []:
            if not isinstance(raw, dict) or len(raw) != 1:
                continue
            key, value = next(iter(raw.items()))
            if key == "no_placeholder_text" and value:
                out.append(A.no_placeholder_text(rendered_html))
            elif key == "merge_field_absent" and isinstance(value, list):
                out.append(A.merge_field_absent(rendered_html, value))
            elif key == "merge_field_present" and isinstance(value, list):
                out.append(A.merge_field_present(rendered_html, value))
            elif key == "has_section" and isinstance(value, list):
                out.append(A.has_section(rendered_html, value))
            else:
                out.append(
                    AssertionResult(
                        name=str(key),
                        passed=True,
                        detail="skipped — not implemented on Day 1-2",
                        category="structural",
                    )
                )
        return out

    @staticmethod
    def _run_citation(
        items: list[Any] | None, rendered_html: str
    ) -> list[AssertionResult]:
        """Dispatch citation assertions. Two implemented for Day 1-2."""
        out: list[AssertionResult] = []
        for raw in items or []:
            if not isinstance(raw, dict) or len(raw) != 1:
                continue
            key, value = next(iter(raw.items()))
            if key == "all_citations_resolve_in_canonical_map" and value:
                out.append(A.all_citations_resolve_in_canonical_map(rendered_html))
            elif key == "known_wrong_citations_zero" and value:
                out.append(A.known_wrong_citations_zero(rendered_html))
            else:
                out.append(
                    AssertionResult(
                        name=str(key),
                        passed=True,
                        detail="skipped — not implemented on Day 1-2",
                        category="citation_correctness",
                    )
                )
        return out

    @staticmethod
    def _stub_category(
        items: list[Any] | None, factory
    ) -> list[AssertionResult]:
        """Build skipped stubs for one category."""
        out: list[AssertionResult] = []
        for raw in items or []:
            if not isinstance(raw, dict) or len(raw) != 1:
                continue
            key = next(iter(raw.keys()))
            out.append(factory(str(key)))
        return out

    @staticmethod
    def _compute_verdict(
        assertion_results: dict[str, list[AssertionResult]],
    ) -> str:
        """Pass iff every assertion in every category passed."""
        for results in assertion_results.values():
            for r in results:
                if not r.passed:
                    return "fail"
        return "pass"

    @staticmethod
    def _build_totals(*, runner: LeaseAgentRunner) -> ScenarioTotals:
        """Aggregate runner counters into a ``ScenarioTotals``."""
        input_tokens = sum(r.input_tokens for r in runner._call_log)
        output_tokens = sum(r.output_tokens for r in runner._call_log)
        cache_read = sum(r.cache_read for r in runner._call_log)
        return ScenarioTotals(
            llm_call_count=runner.llm_call_count,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read=cache_read,
            cost_usd=round(runner.running_cost_usd, 6),
            retry_count=runner.retry_count,
            terminated_reason=runner.terminated_reason or "completed",
        )


__all__ = [
    "DRAFTER_MODEL_DEFAULT",
    "HarnessMode",
    "LeaseTrainingHarness",
    "Scenario",
]
