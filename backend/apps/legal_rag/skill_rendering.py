"""Jinja2 rendering helpers for ``manage.py render_legal_skills``.

The renderer reads canonical legal-fact YAML via the legal_rag query API,
applies a per-target Jinja2 template, and emits the auto-generated section
that lives between ``<!-- BEGIN AUTO-GENERATED legal-facts -->`` and
``<!-- END AUTO-GENERATED legal-facts -->`` markers in each skill ``.md``.

Behaviour locked by ``content/cto/centralised-legal-rag-store-plan.md`` §7
— authors edit YAML; ``.md`` files are downstream views; CI fails on drift.

Why this is a separate module:
    - The management command (``render_legal_skills``) is a thin Django
      shim that handles CLI parsing, advisory locking, drift diffs, and
      file IO. The pure-Python rendering logic — template environment,
      helper functions, marker extraction/replacement — lives here so
      tests can target it without standing up a full Django CLI.
"""
from __future__ import annotations

import datetime as _dt
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import jinja2
from django.conf import settings

from apps.legal_rag.exceptions import LegalFactNotFound
from apps.legal_rag.queries import (
    LegalFact,
    query_concept,
    query_facts_by_topic,
)

logger = logging.getLogger(__name__)


# ── Constants ─────────────────────────────────────────────────────────── #


#: Marker pair used to bracket the auto-generated region inside each skill
#: ``.md`` file. Anything outside the markers is preserved verbatim across
#: renders (per plan §7 "Skills that are NOT generated").
BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED legal-facts -->"
END_MARKER = "<!-- END AUTO-GENERATED legal-facts -->"

#: Compiled regex that captures the content between the markers. The
#: ``DOTALL`` flag lets ``.`` match newlines so we capture multi-line
#: generated blocks.
_MARKER_RE = re.compile(
    rf"({re.escape(BEGIN_MARKER)})(.*?)({re.escape(END_MARKER)})",
    re.DOTALL,
)

#: Default template root — backend/apps/legal_rag/skill_templates/.
_DEFAULT_TEMPLATE_ROOT: Path = (
    Path(__file__).resolve().parent / "skill_templates"
)


# ── Result dataclass ──────────────────────────────────────────────────── #


@dataclass(frozen=True)
class RenderResult:
    """The output of rendering a single skill target.

    ``rendered_section`` is the content that belongs between the two
    marker comments, WITHOUT the markers themselves. The management
    command splices it into the on-disk file (write mode) or compares it
    against the on-disk extract (check mode).
    """

    target_path: Path
    rendered_section: str
    corpus_version: str
    facts_used: tuple[str, ...]


# ── Jinja environment ─────────────────────────────────────────────────── #


def build_environment(
    template_root: Path | None = None,
) -> jinja2.Environment:
    """Build a Jinja2 environment for the skill templates.

    ``autoescape`` is intentionally off — we render Markdown, not HTML.
    ``trim_blocks`` + ``lstrip_blocks`` keep loop output tidy without
    forcing template authors to micromanage whitespace.
    """
    root = template_root or _DEFAULT_TEMPLATE_ROOT
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(root)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=jinja2.StrictUndefined,
    )


# ── Template helpers ──────────────────────────────────────────────────── #


def _fact_helper(concept_id: str) -> LegalFact:
    """Look up a fact by ``concept_id``. Raises ``LegalFactNotFound``.

    Exposed to templates as ``fact(concept_id)``. Failure surfaces as a
    template-level exception so the command exits non-zero rather than
    silently writing a half-rendered file with a stale citation.
    """
    if not concept_id:
        raise LegalFactNotFound(
            "fact(concept_id) called with an empty concept_id"
        )
    return query_concept(concept_id)


def _facts_by_topic_helper(
    *topic_tags: str,
    statute: str | None = None,
    k: int = 10,
    include_provisional: bool = True,
    min_confidence: str = "low",
) -> list[LegalFact]:
    """Tag-and-filter retrieval, exposed as ``facts_by_topic`` in templates.

    Defaults are deliberately permissive (``include_provisional=True``,
    ``min_confidence="low"``) because the renderer's job is to surface every
    fact — including LOW-confidence ones, which the template marks
    explicitly as ``provisional``. Consumers tighten these in their own
    code paths via the query API directly.
    """
    if not topic_tags:
        return []
    return query_facts_by_topic(
        list(topic_tags),
        statute=statute,
        k=k,
        include_provisional=include_provisional,
        min_confidence=min_confidence,  # type: ignore[arg-type]
    )


def _concept_helper(concept_id: str) -> LegalFact:
    """Alias for :func:`_fact_helper` — kept for template readability.

    Some templates conceptually retrieve "the concept" rather than "the
    fact"; same underlying lookup.
    """
    return _fact_helper(concept_id)


def _verification_label(fact: LegalFact) -> str:
    """Render a one-line provenance label for a fact.

    Per plan §7, every rendered fact carries a ``verification_status``
    annotation. We resolve it here so templates stay declarative.
    """
    status = fact.verification_status
    if status == "lawyer_reviewed":
        attested = fact.attested_by or "admitted attorney"
        when = fact.attested_at.isoformat() if fact.attested_at else "date unknown"
        return f"Lawyer-attested by {attested} on {when}"
    if status == "mc_reviewed":
        return "Verified by Klikk"
    return "AI-curated"


# ── Public rendering API ──────────────────────────────────────────────── #


def render_target(
    template_name: str,
    *,
    corpus_version: str,
    env: jinja2.Environment | None = None,
    extra_context: dict | None = None,
) -> RenderResult:
    """Render one skill template and return its generated section.

    Caller (the management command) wraps this in a write-or-diff
    decision. The returned ``rendered_section`` does NOT include the
    BEGIN/END markers — the command keeps the on-disk markers stable
    and splices content between them.

    Args:
        template_name: path relative to the template root, e.g.
            ``"klikk-legal-POPIA-RHA/06-rha-core-and-s5.md.j2"``.
        corpus_version: the active ``LegalCorpusVersion.version`` to
            stamp into the rendered footer.
        env: pre-built Jinja2 environment; if ``None`` a default
            environment rooted at ``skill_templates/`` is built.
        extra_context: optional dict merged into the template context.

    Returns:
        :class:`RenderResult` with the rendered section text + the list
        of ``concept_id`` values the template touched (for logging).
    """
    env = env or build_environment()
    try:
        template = env.get_template(template_name)
    except jinja2.TemplateNotFound as exc:
        raise FileNotFoundError(
            f"Skill template {template_name!r} not found under "
            f"{_DEFAULT_TEMPLATE_ROOT}"
        ) from exc

    facts_seen: list[str] = []

    def tracked_fact(concept_id: str) -> LegalFact:
        fact = _fact_helper(concept_id)
        facts_seen.append(fact.concept_id)
        return fact

    def tracked_facts_by_topic(
        *topic_tags: str,
        statute: str | None = None,
        k: int = 10,
        include_provisional: bool = True,
        min_confidence: str = "low",
    ) -> list[LegalFact]:
        results = _facts_by_topic_helper(
            *topic_tags,
            statute=statute,
            k=k,
            include_provisional=include_provisional,
            min_confidence=min_confidence,
        )
        facts_seen.extend(r.concept_id for r in results)
        return results

    context: dict = {
        "fact": tracked_fact,
        "facts_by_topic": tracked_facts_by_topic,
        "concept": _concept_helper,
        "verification_label": _verification_label,
        "corpus_version": corpus_version,
        "now": _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }
    if extra_context:
        context.update(extra_context)

    rendered = template.render(**context)

    return RenderResult(
        target_path=Path(template_name),
        rendered_section=rendered,
        corpus_version=corpus_version,
        facts_used=tuple(facts_seen),
    )


# ── Marker extraction + replacement ──────────────────────────────────── #


def extract_section(content: str) -> str | None:
    """Return the text between the BEGIN/END markers, or ``None`` if absent.

    The leading + trailing newline characters are preserved as-is so the
    diff against the rendered output is byte-for-byte. A missing pair
    returns ``None`` so the command can fall back to either failing in
    check mode or appending the markers in write mode.
    """
    match = _MARKER_RE.search(content)
    if match is None:
        return None
    return match.group(2)


def replace_section(content: str, rendered_section: str) -> str:
    """Return ``content`` with the section between markers replaced.

    The markers themselves are preserved. If markers are missing the
    function raises ``ValueError`` — the caller should ensure markers
    exist before calling.
    """
    match = _MARKER_RE.search(content)
    if match is None:
        raise ValueError(
            "Cannot replace auto-generated section: markers "
            f"{BEGIN_MARKER!r} / {END_MARKER!r} not found in target."
        )
    return (
        content[: match.start()]
        + BEGIN_MARKER
        + rendered_section
        + END_MARKER
        + content[match.end() :]
    )


def default_template_root() -> Path:
    """Return the default template root.

    Exposed so the management command can list available templates
    without importing the private module-level constant.
    """
    # When running under tests the project layout might differ; allow
    # an override via Django settings for parity with sync_legal_facts.
    override = getattr(settings, "LEGAL_RAG_SKILL_TEMPLATE_ROOT", None)
    if override:
        return Path(override).resolve()
    return _DEFAULT_TEMPLATE_ROOT


__all__ = [
    "BEGIN_MARKER",
    "END_MARKER",
    "RenderResult",
    "build_environment",
    "render_target",
    "extract_section",
    "replace_section",
    "default_template_root",
]
