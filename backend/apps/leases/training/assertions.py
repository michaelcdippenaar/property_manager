"""Assertion taxonomy implementations.

Pure functions returning ``AssertionResult`` per plan §4 (Day 1-2 subset).

Five categories live in the plan:
    1. structural
    2. citation_correctness
    3. reviewer_pipeline   (Day 1-2: stub — Phase 2 wires the Reviewer)
    4. cost_and_latency    (Day 1-2: stub — no real budget data on a
                            single dispatched Drafter call)
    5. semantic (judge)    (Day 1-2: stub — Phase 2 brings the judge)

Day 1-2 implements structural + citation_correctness for real and emits
``skipped`` stubs for the other three.

Implementations are deliberately small, regex-driven, and dependency-light
so they remain correct as the surrounding harness evolves.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from apps.leases.management.commands.verify_caselaw_citations import (
    CANONICAL_CITATIONS,
    CITATION_RE,
    KNOWN_WRONG_CITATIONS,
    normalise,
)


# ── Result type ──────────────────────────────────────────────────────── #


@dataclass(frozen=True)
class AssertionResult:
    """Outcome of one assertion.

    ``category`` is one of:
        structural | citation_correctness | reviewer_pipeline |
        cost_and_latency | semantic.

    ``detail`` is a short human-readable explanation — what failed, or
    "skipped — Phase 1 Day 1-2 stub" for unimplemented categories.
    """

    name: str
    passed: bool
    detail: str
    category: str


# ── Structural ───────────────────────────────────────────────────────── #


# Matches the four placeholder patterns called out in plan §4.1 + decision
# 21's rationale: ``[needs completion]``, ``TBD``, ``TODO``, ``XXX``.
# Match ``[needs completion]`` as a literal substring (case-insensitive).
_PLACEHOLDER_LITERAL = "[needs completion]"
# Whole-word match for the bareword forms so we don't false-positive on
# ``methodology`` containing ``TODO``-like substrings.
_PLACEHOLDER_WORDS_RE = re.compile(r"\b(?:TBD|TODO|XXX)\b")


def no_placeholder_text(html: str) -> AssertionResult:
    """Structural assertion: zero placeholder markers in the rendered HTML.

    Fails if any of ``[needs completion]`` (case-insensitive substring),
    ``TBD``, ``TODO``, or ``XXX`` (whole-word) appear anywhere in
    ``html``. Catches plan §2 failure 1 (placeholder leakage).
    """
    haystack = html or ""
    hits: list[str] = []
    if _PLACEHOLDER_LITERAL in haystack.lower():
        hits.append(_PLACEHOLDER_LITERAL)
    for match in _PLACEHOLDER_WORDS_RE.findall(haystack):
        hits.append(match)
    if hits:
        return AssertionResult(
            name="no_placeholder_text",
            passed=False,
            detail=f"placeholders found: {sorted(set(hits))}",
            category="structural",
        )
    return AssertionResult(
        name="no_placeholder_text",
        passed=True,
        detail="no placeholder markers in rendered html",
        category="structural",
    )


# Regex used to detect merge-field tokens in the rendered HTML. We accept
# optional whitespace inside the braces — matching the Jinja-style
# ``{{ field }}`` convention used by ``apps.leases.merge_fields``.
def _merge_field_regex(field: str) -> re.Pattern[str]:
    return re.compile(r"\{\{\s*" + re.escape(field) + r"\s*\}\}")


def merge_field_absent(html: str, fields: list[str]) -> AssertionResult:
    """Structural assertion: none of ``fields`` appear as merge tokens.

    Fails if any ``{{ field }}`` token (with optional surrounding
    whitespace) for any item in ``fields`` is present in ``html``.
    Catches plan §2 failure 2 (phantom tenant-field expansion).
    """
    found: list[str] = []
    for field in fields or []:
        if _merge_field_regex(field).search(html or ""):
            found.append(field)
    if found:
        return AssertionResult(
            name="merge_field_absent",
            passed=False,
            detail=f"unexpected merge fields present: {found}",
            category="structural",
        )
    return AssertionResult(
        name="merge_field_absent",
        passed=True,
        detail=f"none of {fields} present",
        category="structural",
    )


def merge_field_present(html: str, fields: list[str]) -> AssertionResult:
    """Structural assertion: every item in ``fields`` appears as a merge token.

    Fails if any ``{{ field }}`` token is missing from ``html``. The
    inverse of ``merge_field_absent`` — used to assert canonical
    party/property/financial fields landed in the lease body.
    """
    missing: list[str] = []
    for field in fields or []:
        if not _merge_field_regex(field).search(html or ""):
            missing.append(field)
    if missing:
        return AssertionResult(
            name="merge_field_present",
            passed=False,
            detail=f"required merge fields missing: {missing}",
            category="structural",
        )
    return AssertionResult(
        name="merge_field_present",
        passed=True,
        detail=f"all of {fields} present",
        category="structural",
    )


def has_section(html: str, sections: list[str]) -> AssertionResult:
    """Structural assertion: every section heading in ``sections`` is present.

    Match is case-insensitive substring against the rendered HTML — we
    don't parse the DOM here because the harness's structural checks live
    upstream of the Formatter and the heading hierarchy is not stable in
    early Drafter output.
    """
    haystack = (html or "").lower()
    missing = [s for s in (sections or []) if s.lower() not in haystack]
    if missing:
        return AssertionResult(
            name="has_section",
            passed=False,
            detail=f"missing sections: {missing}",
            category="structural",
        )
    return AssertionResult(
        name="has_section",
        passed=True,
        detail=f"all of {sections} present",
        category="structural",
    )


# ── Citation-correctness ─────────────────────────────────────────────── #


def all_citations_resolve_in_canonical_map(html: str) -> AssertionResult:
    """Citation assertion: every cite scraped from ``html`` is canonical.

    Uses the same ``CITATION_RE`` and ``normalise()`` as
    ``verify_caselaw_citations`` so the harness assertion stays in
    lockstep with the static-markdown gate. Returns ``passed=False`` if
    any cite is missing from ``CANONICAL_CITATIONS``.

    Catches plan §2 failure 4 (citation drift in generated output).
    """
    unresolved: list[str] = []
    seen: set[str] = set()
    for match in CITATION_RE.finditer(html or ""):
        statute, section = match.group(1), match.group(2)
        canonical = normalise(statute, section)
        if canonical in seen:
            continue
        seen.add(canonical)
        if canonical not in CANONICAL_CITATIONS:
            unresolved.append(canonical)
    if unresolved:
        return AssertionResult(
            name="all_citations_resolve_in_canonical_map",
            passed=False,
            detail=f"unresolved citations: {unresolved}",
            category="citation_correctness",
        )
    return AssertionResult(
        name="all_citations_resolve_in_canonical_map",
        passed=True,
        detail=f"all {len(seen)} unique citations resolve in canonical map",
        category="citation_correctness",
    )


# Pattern → canonical citation key — used to spot the bareword "Tribunal
# established under s13" type of mistake that ``KNOWN_WRONG_CITATIONS``
# encodes. Day 1-2 implementation: substring scan for the known-wrong
# canonical citation form. The richer "context-aware" version (e.g. "s13
# … tribunal established") is a Phase 2 enhancement.
def known_wrong_citations_zero(html: str) -> AssertionResult:
    """Citation assertion: no ``KNOWN_WRONG_CITATIONS`` keys appear.

    Each key in ``KNOWN_WRONG_CITATIONS`` is of the form
    ``"<STATUTE>:<section>|<context-tag>"``. The statute+section half is
    a canonical citation; if it lands in the HTML at all we treat it as a
    candidate hit and report it. The ``context-tag`` half is a hint about
    the misuse pattern, included in the failure detail.

    This is the inverse of ``all_citations_resolve_in_canonical_map``: it
    catches citations that ARE canonical-looking but encode known
    historical mistakes. Catches the Tribunal-s13-vs-s7 regression and
    similar.
    """
    hits: list[tuple[str, str]] = []
    for wrong_key, hint in KNOWN_WRONG_CITATIONS.items():
        canonical_form, _, _ = wrong_key.partition("|")
        # canonical_form is like "RHA:s13" — convert back to source form
        # "RHA s13" for the substring scan.
        statute, _, section = canonical_form.partition(":")
        source_form = f"{statute} {section}"
        if source_form.lower() in (html or "").lower():
            hits.append((wrong_key, hint))
    if hits:
        details = "; ".join(f"{k}: {v}" for k, v in hits)
        return AssertionResult(
            name="known_wrong_citations_zero",
            passed=False,
            detail=f"known-wrong citation patterns present: {details}",
            category="citation_correctness",
        )
    return AssertionResult(
        name="known_wrong_citations_zero",
        passed=True,
        detail="no known-wrong citation patterns",
        category="citation_correctness",
    )


# ── Stubs (Phase 2+) ─────────────────────────────────────────────────── #


_STUB_DETAIL = "skipped — Phase 1 Day 1-2 stub"


def stub_reviewer_pipeline(name: str) -> AssertionResult:
    """Stub Reviewer-pipeline assertion. Always passes.

    Phase 2 wires the Reviewer; until then any reviewer-pipeline check
    declared in a scenario is acknowledged but not enforced.
    """
    return AssertionResult(
        name=name,
        passed=True,
        detail=_STUB_DETAIL,
        category="reviewer_pipeline",
    )


def stub_cost_and_latency(name: str) -> AssertionResult:
    """Stub cost-and-latency assertion. Always passes.

    Day 1-2 dispatches a single Drafter call from a hand-crafted
    cassette; per-scenario budget ceilings are checked once Phase 2
    wires the realistic 3-4 call pipeline.
    """
    return AssertionResult(
        name=name,
        passed=True,
        detail=_STUB_DETAIL,
        category="cost_and_latency",
    )


def stub_semantic(name: str) -> AssertionResult:
    """Stub LLM-as-judge assertion. Always passes.

    Phase 2 of the plan brings ``judge.py``; the smoke battery never
    invokes the judge per plan §8.1.
    """
    return AssertionResult(
        name=name,
        passed=True,
        detail=_STUB_DETAIL,
        category="semantic",
    )


__all__ = [
    "AssertionResult",
    "all_citations_resolve_in_canonical_map",
    "has_section",
    "known_wrong_citations_zero",
    "merge_field_absent",
    "merge_field_present",
    "no_placeholder_text",
    "stub_cost_and_latency",
    "stub_reviewer_pipeline",
    "stub_semantic",
]
