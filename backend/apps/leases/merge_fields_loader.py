"""YAML-backed loader for the Klikk lease merge-fields catalogue.

Source of truth: ``content/legal/merge_fields/<category>.yaml`` (one file per
category). Validated against ``content/legal/_schema/merge_field.schema.json``.

This module is the foundation for the lease-AI Front Door's cached
merge-fields system block (see
``docs/system/lease-ai-agent-architecture.md`` §6.6 + decision 18) and the
fix for §2 failure mode 2 (AI pulls ``tenant_2_*`` even with one tenant).
``filter_by_context()`` materialises the context-aware subset; the Drafter
never sees inapplicable fields.

Public API:

    load_all_fields()
        Read + validate every YAML file under
        ``content/legal/merge_fields/``. Returns a sorted, deduplicated
        list of ``MergeField`` records. Cached via ``lru_cache``.

    filter_by_context(*, tenant_count, property_type, lease_type)
        Return the subset of ``load_all_fields()`` applicable to the given
        request context. Drops ``tenant_2_*`` for single-tenant requests,
        sectional-title-only fields for freehold, etc.

    render_for_drafter_system_block(fields)
        Compact human-readable rendering suitable for inlining into the
        Drafter's cached system block (§6.6). Deterministic — same input
        always produces the same string, so the block is fully cacheable.

The companion shim at ``apps.leases.merge_fields`` preserves the legacy
``CANONICAL_MERGE_FIELDS`` tuple list by reading from this loader. The
shim is scheduled for retirement in lease-AI Phase 2.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings

logger = logging.getLogger(__name__)


# ── Constants ─────────────────────────────────────────────────────────── #


MERGE_FIELDS_DIR_REL = "content/legal/merge_fields"
SCHEMA_REL = "content/legal/_schema/merge_field.schema.json"


# ── String-date YAML loader ────────────────────────────────────────────── #


class StringDateSafeLoader(yaml.SafeLoader):
    """PyYAML SafeLoader that DOES NOT auto-resolve ISO date strings.

    The default SafeLoader maps ``"2026-05-12"`` to ``datetime.date(2026, 5, 12)``,
    which then trips JSON Schema ``format: date`` validation (expects a string).
    This subclass strips the timestamp implicit resolver so dates stay as
    strings end-to-end. Same trick used by
    ``apps.legal_rag.checks.check_legal_facts_schema``.
    """


# Build the resolver dict once per class — the SafeLoader's class-level dict
# is mutable so we must snapshot before assigning the filtered version.
StringDateSafeLoader.yaml_implicit_resolvers = {
    first_char: [
        (tag, regex)
        for tag, regex in resolvers
        if tag != "tag:yaml.org,2002:timestamp"
    ]
    for first_char, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


# ── Dataclass ─────────────────────────────────────────────────────────── #


@dataclass(frozen=True)
class MergeField:
    """A single canonical merge field, normalised from YAML.

    ``tenant_counts`` / ``property_types`` / ``lease_types`` use ``None`` to
    mean "any" — the loader explodes that into the canonical iterable at
    filter time. ``frozenset`` is used so the dataclass stays hashable.
    """

    name: str
    label: str
    category: str
    type: str
    required: bool
    tenant_counts: frozenset[int] | None
    property_types: frozenset[str] | None
    lease_types: frozenset[str] | None
    validation_regex: str | None
    example: str
    plain_english: str
    related_legal_facts: tuple[str, ...]
    enum_values: tuple[str, ...] | None
    deprecated_in: str | None
    replacement: str | None


# ── Helpers ───────────────────────────────────────────────────────────── #


def _repo_root() -> Path:
    """Repo root = backend's parent (matches legal_rag.checks)."""
    return Path(settings.BASE_DIR).parent


def _merge_fields_dir() -> Path:
    return _repo_root() / MERGE_FIELDS_DIR_REL


def _schema_path() -> Path:
    return _repo_root() / SCHEMA_REL


@lru_cache(maxsize=1)
def _load_schema() -> dict[str, Any]:
    """Read the JSON Schema once per process. Loud failure on missing."""
    path = _schema_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"merge_fields_loader: schema not found at {path}. "
            "Ensure content/legal/_schema/merge_field.schema.json exists."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _coerce_listish(
    value: Any,
) -> frozenset[Any] | None:
    """Normalise an applicability field to a frozenset or None.

    YAML emits ``"any"`` as a string and lists as ``list``. We collapse:
        "any"        → None (means: no restriction)
        list[X]      → frozenset(list)
    """
    if value == "any":
        return None
    if isinstance(value, list):
        return frozenset(value)
    raise ValueError(
        f"merge_fields_loader: invalid applicability value {value!r}; "
        f"expected 'any' or list."
    )


def _record_to_merge_field(record: dict[str, Any]) -> MergeField:
    """Convert a validated YAML record into a ``MergeField`` instance."""
    applicability = record["applicability"]
    deprecation = record.get("deprecation") or {}
    enum_values = record.get("enum_values")
    return MergeField(
        name=record["name"],
        label=record["label"],
        category=record["category"],
        type=record["type"],
        required=record["required"],
        tenant_counts=_coerce_listish(applicability["tenant_counts"]),
        property_types=_coerce_listish(applicability["property_types"]),
        lease_types=_coerce_listish(applicability["lease_types"]),
        validation_regex=record.get("validation_regex"),
        example=record["example"],
        plain_english=record["plain_english"].strip(),
        related_legal_facts=tuple(record.get("related_legal_facts") or ()),
        enum_values=tuple(enum_values) if enum_values else None,
        deprecated_in=deprecation.get("deprecated_in"),
        replacement=deprecation.get("replacement"),
    )


def _validate_records(records: list[dict[str, Any]], schema: dict[str, Any]) -> None:
    """Validate each record against the merge_field schema. Raises on failure."""
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for idx, record in enumerate(records):
        for err in validator.iter_errors(record):
            location = "/".join(str(p) for p in err.absolute_path) or "<root>"
            name = record.get("name", f"<record {idx}>")
            errors.append(f"{name} at {location}: {err.message}")
    if errors:
        joined = "\n  - ".join(errors)
        raise ValueError(
            f"merge_fields_loader: schema validation failed for "
            f"{len(errors)} record(s):\n  - {joined}"
        )


# ── Public API ────────────────────────────────────────────────────────── #


@lru_cache(maxsize=1)
def load_all_fields() -> list[MergeField]:
    """Read + validate every YAML file under ``content/legal/merge_fields/``.

    Returns a list sorted by ``(category, name)``. Cached for the process
    lifetime via ``lru_cache``; call ``load_all_fields.cache_clear()`` in
    tests that need a fresh read.

    Raises:
        FileNotFoundError: directory or schema missing.
        ValueError: YAML parse / schema validation / duplicate name.
    """
    root = _merge_fields_dir()
    if not root.is_dir():
        raise FileNotFoundError(
            f"merge_fields_loader: directory not found at {root}. "
            "Ensure content/legal/merge_fields/ exists with one YAML "
            "file per category."
        )

    schema = _load_schema()
    records: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.yaml")):
        try:
            data = yaml.load(path.read_text(encoding="utf-8"), Loader=StringDateSafeLoader)
        except yaml.YAMLError as exc:
            raise ValueError(
                f"merge_fields_loader: YAML parse error in {path.name}: {exc}"
            ) from exc
        if data is None:
            continue
        if not isinstance(data, list):
            raise ValueError(
                f"merge_fields_loader: {path.name} must be a YAML list of "
                f"records (got {type(data).__name__})."
            )
        records.extend(data)

    _validate_records(records, schema)

    fields = [_record_to_merge_field(r) for r in records]

    # Duplicate-name guard: every name is globally unique across categories.
    seen: set[str] = set()
    for field in fields:
        if field.name in seen:
            raise ValueError(
                f"merge_fields_loader: duplicate field name '{field.name}' "
                f"in category '{field.category}'."
            )
        seen.add(field.name)

    fields.sort(key=lambda f: (f.category, f.name))
    return fields


def filter_by_context(
    *,
    tenant_count: int,
    property_type: str,
    lease_type: str,
) -> list[MergeField]:
    """Return the subset of merge fields applicable to a request context.

    The Front Door calls this once per request to build the cached
    merge-fields system block (architecture doc §6.6). Filters:

      - ``tenant_counts``: drop fields whose ``tenant_counts`` set doesn't
        include the request's ``tenant_count``.
      - ``property_types``: drop fields whose ``property_types`` set doesn't
        include the request's ``property_type``.
      - ``lease_types``: drop fields whose ``lease_types`` set doesn't
        include the request's ``lease_type``.

    A field with ``None`` for any of those three is treated as "any" and
    not filtered on that dimension.

    THIS IS THE LITERAL FIX for ``docs/system/lease-ai-agent-architecture.md``
    §2 failure mode 2: when called with ``tenant_count=1``, no
    ``tenant_2_*`` or ``tenant_3_*`` field passes the gate.
    """
    fields = load_all_fields()
    return [
        f
        for f in fields
        if (f.tenant_counts is None or tenant_count in f.tenant_counts)
        and (f.property_types is None or property_type in f.property_types)
        and (f.lease_types is None or lease_type in f.lease_types)
    ]


# ``string`` is the default merge-field type. Omitting it for non-required
# fields shaves the rendered Drafter system block by ~10 chars per line
# without losing semantic content (the field name already implies the
# shape, and the structured Context Object carries the typed value).
_DEFAULT_FIELD_TYPE = "string"


def render_for_drafter_system_block(fields: list[MergeField]) -> str:
    """Render a compact list of fields for the Drafter system block.

    Output shape per the architecture doc §6.6 — grouped by category, one
    line per field, with required fields tagged ``*`` and rendered with a
    short gloss; non-required fields render in a denser one-liner (name +
    optional type) to fit comfortably inside the cached system block
    budget.

    Same Context Object produces the same string — fully cacheable.

    **Budget invariant** (Day 3 G.3): the rendered block stays under
    3900 chars across every supported ``(tenant_count, property_type,
    lease_type)`` combination — leaving ≥100 chars of headroom under the
    plan §6.6 ``cache_control: ephemeral`` 4000-char ceiling so future
    field additions cannot silently bust the budget. The 4086-char
    over-run on the worst-case (3-tenant + sectional-title + fixed-term)
    path observed on 2026-05-13 is the regression this rendering avoids.

    Line shapes:

      * ``* `name` (type) — <gloss>`` for required fields. The example
        value is intentionally omitted; the gloss carries the meaning and
        the Drafter receives the concrete example via the structured
        Context Object, not this catalogue.
      * ``- `name` (type)`` for non-default-typed non-required fields.
      * ``- `name``` for non-required fields whose type is ``string``
        (the default; type label adds no information).
    """
    if not fields:
        return "## Available merge fields\n\n_(none applicable for this context)_"

    category_order = [
        "landlord",
        "landlord_bank",
        "property",
        "tenant",
        "tenant_1",
        "tenant_2",
        "tenant_3",
        "co_tenants",
        "occupant_1",
        "occupant_2",
        "occupant_3",
        "occupant_4",
        "lease_terms",
        "deposit",
        "dates",
        "services",
    ]
    grouped: dict[str, list[MergeField]] = {}
    for field in fields:
        grouped.setdefault(field.category, []).append(field)

    lines = [
        "## Available merge fields",
        "Syntax `{{ field_name }}`. `*` = required.",
    ]
    for cat in category_order:
        cat_fields = grouped.get(cat, [])
        if not cat_fields:
            continue
        cat_fields_sorted = sorted(cat_fields, key=lambda f: f.name)
        lines.append(f"### {cat}")
        for field in cat_fields_sorted:
            if field.required:
                # Required fields earn a one-clause gloss; the example is
                # omitted on purpose (G.3 budget tightening — the gloss
                # already conveys intent and the concrete value is in the
                # request Context Object).
                gloss = _short_gloss(field.plain_english, max_chars=50)
                lines.append(
                    f"* `{field.name}` ({field.type}) — {gloss}"
                )
            elif field.type != _DEFAULT_FIELD_TYPE:
                # Non-default type: keep the annotation for AI clarity.
                lines.append(f"- `{field.name}` ({field.type})")
            else:
                # Default ``string`` type: name alone is enough.
                lines.append(f"- `{field.name}`")

    return "\n".join(lines) + "\n"


_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")


def _short_gloss(plain_english: str, max_chars: int = 80) -> str:
    """Return the first sentence of ``plain_english``, capped to ``max_chars``.

    Whitespace is squashed. Sentence boundary is ``.``, ``!``, or ``?``
    followed by whitespace. Falls back to a hard char-truncation with an
    ellipsis when no sentence boundary fits inside the cap.
    """
    squashed = re.sub(r"\s+", " ", plain_english).strip()
    if not squashed:
        return ""
    parts = _SENTENCE_END_RE.split(squashed, maxsplit=1)
    first = parts[0]
    if len(first) <= max_chars:
        return first
    return first[: max_chars - 1].rstrip() + "…"


def field_by_name(name: str) -> MergeField | None:
    """Lookup helper — None if not present. Cached via ``load_all_fields``."""
    for field in load_all_fields():
        if field.name == name:
            return field
    return None
