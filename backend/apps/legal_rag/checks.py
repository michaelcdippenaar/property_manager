"""Django system checks for the centralised legal RAG store.

Validates every YAML file in ``content/legal/statutes/`` against the JSON
Schema in ``content/legal/_schema/legal_fact.schema.json``. Returns
``Warning`` (not ``Error``) for invalid files in Day 1-2 — the codebase
is fail-soft until ``sync_legal_facts`` lands in Day 3 and the loader
becomes the hard gate.

Hooked from ``apps.legal_rag.apps.LegalRagConfig.ready()``. Runs on
``manage.py check`` and at app startup.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.checks import Tags, Warning as CheckWarning, register

logger = logging.getLogger(__name__)


# ── Constants ─────────────────────────────────────────────────────────── #


# Relative to repo_root. settings.BASE_DIR is `backend/`, so the repo root
# is its parent — same pattern used by verify_caselaw_citations.
_CONTENT_LEGAL_REL = "content/legal"
_SCHEMA_REL = "content/legal/_schema/legal_fact.schema.json"
_STATUTES_REL = "content/legal/statutes"
_MERGE_FIELD_SCHEMA_REL = "content/legal/_schema/merge_field.schema.json"
_MERGE_FIELDS_REL = "content/legal/merge_fields"


# ── Helpers ───────────────────────────────────────────────────────────── #


def _repo_root() -> Path:
    """Repo root = backend's parent (matches verify_caselaw_citations)."""
    return Path(settings.BASE_DIR).parent


@lru_cache(maxsize=1)
def _load_schema() -> dict[str, Any] | None:
    """Load the legal_fact JSON schema once per process.

    Returns None if the schema file is missing — the check then yields
    a single Warning rather than blowing up app startup.
    """
    schema_path = _repo_root() / _SCHEMA_REL
    if not schema_path.is_file():
        return None
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.error("legal_rag: failed to parse JSON schema at %s: %s", schema_path, exc)
        return None


def _iter_statute_yaml_files() -> list[Path]:
    """Yield every YAML file under content/legal/statutes/."""
    statutes_root = _repo_root() / _STATUTES_REL
    if not statutes_root.is_dir():
        return []
    return sorted(statutes_root.rglob("*.yaml")) + sorted(statutes_root.rglob("*.yml"))


@lru_cache(maxsize=1)
def _load_merge_field_schema() -> dict[str, Any] | None:
    """Load the merge_field JSON schema once per process. None on missing."""
    schema_path = _repo_root() / _MERGE_FIELD_SCHEMA_REL
    if not schema_path.is_file():
        return None
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.error(
            "legal_rag: failed to parse merge_field JSON schema at %s: %s",
            schema_path,
            exc,
        )
        return None


def _iter_merge_field_yaml_files() -> list[Path]:
    """Yield every YAML file under content/legal/merge_fields/."""
    root = _repo_root() / _MERGE_FIELDS_REL
    if not root.is_dir():
        return []
    return sorted(root.glob("*.yaml")) + sorted(root.glob("*.yml"))


# ── Check ─────────────────────────────────────────────────────────────── #


@register(Tags.compatibility)
def check_legal_facts_schema(app_configs, **kwargs) -> list[CheckWarning]:
    """Validate every content/legal/statutes/**/*.yaml + content/legal/merge_fields/*.yaml.

    Two validation passes:
        1. legal_fact schema → content/legal/statutes/**/*.yaml
        2. merge_field schema → content/legal/merge_fields/*.yaml

    Day 1-2 contract: emit ``CheckWarning`` (not ``CheckError``) so the
    check is fail-soft. Day 3+ ``sync_legal_facts`` + the merge_fields
    loader become the hard gates (refuse to load on schema failure).
    """
    warnings: list[CheckWarning] = []

    # Defer imports — keeps app startup cheap when checks are not invoked.
    try:
        import yaml  # type: ignore[import-untyped]
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import SchemaError

        from apps.legal_rag.yaml_loader import StringDateLoader
    except ImportError as exc:
        warnings.append(
            CheckWarning(
                f"legal_rag: optional dependency missing — {exc}. "
                "Install `pyyaml` and `jsonschema` to enable YAML schema validation.",
                id="legal_rag.W001",
            )
        )
        return warnings

    string_date_loader = StringDateLoader

    # ── Pass 1: legal_fact schema → statutes/ ──────────────────────── #
    schema = _load_schema()
    if schema is None:
        warnings.append(
            CheckWarning(
                f"legal_rag: schema file missing or unreadable at {_SCHEMA_REL}. "
                "YAML facts are not being validated.",
                id="legal_rag.W002",
            )
        )
    else:
        try:
            validator = Draft202012Validator(schema)
        except SchemaError as exc:
            warnings.append(
                CheckWarning(
                    f"legal_rag: JSON schema itself is invalid — {exc.message}. "
                    f"Path: {list(exc.absolute_path)}",
                    id="legal_rag.W003",
                )
            )
        else:
            warnings.extend(
                _validate_yaml_files(
                    yaml,
                    string_date_loader,
                    validator,
                    files=_iter_statute_yaml_files(),
                    record_is_list=False,
                )
            )

    # ── Pass 2: merge_field schema → merge_fields/ ─────────────────── #
    mf_schema = _load_merge_field_schema()
    if mf_schema is None:
        warnings.append(
            CheckWarning(
                f"legal_rag: merge_field schema missing or unreadable at "
                f"{_MERGE_FIELD_SCHEMA_REL}. Merge-field YAML is not being "
                "validated.",
                id="legal_rag.W007",
            )
        )
    else:
        try:
            mf_validator = Draft202012Validator(mf_schema)
        except SchemaError as exc:
            warnings.append(
                CheckWarning(
                    f"legal_rag: merge_field JSON schema is invalid — {exc.message}. "
                    f"Path: {list(exc.absolute_path)}",
                    id="legal_rag.W008",
                )
            )
        else:
            warnings.extend(
                _validate_yaml_files(
                    yaml,
                    string_date_loader,
                    mf_validator,
                    files=_iter_merge_field_yaml_files(),
                    record_is_list=True,
                )
            )

    # ── Pass 3: skill-render drift (fail-soft) ─────────────────────── #
    warnings.extend(_check_skill_render_drift())

    return warnings


def _check_skill_render_drift() -> list[CheckWarning]:
    """Emit a fail-soft warning when ``render_legal_skills --check`` would fail.

    Lives in the system-checks pipeline so CI (or a developer running
    ``manage.py check``) gets an early ping when a skill ``.md`` has
    drifted from the canonical YAML. Fail-soft: returns ``CheckWarning``
    only — the hard gate is ``manage.py render_legal_skills --check``
    invoked explicitly in CI.

    Conservative on import failures (Jinja2 missing, ORM not ready):
    those scenarios return an empty list rather than raising.
    """
    warnings_out: list[CheckWarning] = []

    try:
        from apps.legal_rag.management.commands.render_legal_skills import (
            DEFAULT_TARGETS,
        )
        from apps.legal_rag.models import LegalCorpusVersion
        from apps.legal_rag.skill_rendering import (
            BEGIN_MARKER,
            END_MARKER,
            build_environment,
            render_target,
            replace_section,
        )
    except Exception:  # noqa: BLE001 — never fail the check pipeline
        return warnings_out

    # Skip the DB read if the table doesn't exist yet (early migrations).
    try:
        active = LegalCorpusVersion.objects.filter(is_active=True).first()
    except Exception:  # noqa: BLE001
        return warnings_out
    corpus_version = active.version if active is not None else "unsynced"

    try:
        env = build_environment()
    except Exception as exc:  # noqa: BLE001
        warnings_out.append(
            CheckWarning(
                f"legal_rag: could not build Jinja2 environment for skill "
                f"render check: {exc}",
                id="legal_rag.W010",
            )
        )
        return warnings_out

    repo_root = _repo_root()
    for rel_path, template_name in DEFAULT_TARGETS.items():
        target_path = repo_root / rel_path
        if not target_path.is_file():
            warnings_out.append(
                CheckWarning(
                    f"legal_rag: skill target missing — {rel_path}. "
                    "Run `manage.py render_legal_skills --write` after "
                    "creating the .md file with BEGIN/END markers.",
                    id="legal_rag.W011",
                )
            )
            continue
        on_disk = target_path.read_text(encoding="utf-8")
        if BEGIN_MARKER not in on_disk or END_MARKER not in on_disk:
            warnings_out.append(
                CheckWarning(
                    f"legal_rag: skill target {rel_path} missing auto-generated "
                    f"markers. Insert {BEGIN_MARKER}/{END_MARKER} pair.",
                    id="legal_rag.W012",
                )
            )
            continue
        try:
            result = render_target(
                template_name, corpus_version=corpus_version, env=env
            )
            new_content = replace_section(on_disk, result.rendered_section)
        except Exception as exc:  # noqa: BLE001
            warnings_out.append(
                CheckWarning(
                    f"legal_rag: skill render failed for {rel_path}: {exc}",
                    id="legal_rag.W013",
                )
            )
            continue
        if new_content != on_disk:
            warnings_out.append(
                CheckWarning(
                    f"legal_rag: skill target {rel_path} has drifted from "
                    f"canonical YAML. Run `manage.py render_legal_skills "
                    "--write` to refresh.",
                    id="legal_rag.W014",
                )
            )

    return warnings_out


def _validate_yaml_files(
    yaml_mod,
    string_date_loader,
    validator,
    *,
    files: list[Path],
    record_is_list: bool,
) -> list[CheckWarning]:
    """Validate a batch of YAML files against ``validator``.

    Args:
        yaml_mod: the imported ``yaml`` module.
        string_date_loader: the loader class that keeps ISO dates as strings.
        validator: a ``Draft202012Validator`` instance.
        files: list of YAML file paths to validate.
        record_is_list: if True, each file is a list of records and the
            validator is applied to each list element; if False, each
            file is a single object validated whole. Drives whether we
            iterate records inside a file (merge_field pattern) or
            validate the file's root document (legal_fact pattern).
    """
    warnings: list[CheckWarning] = []
    if not files:
        return warnings

    for path in files:
        rel = path.relative_to(_repo_root())
        try:
            data = yaml_mod.load(
                path.read_text(encoding="utf-8"), Loader=string_date_loader
            )
        except yaml_mod.YAMLError as exc:
            warnings.append(
                CheckWarning(
                    f"legal_rag: {rel} — YAML parse error: {exc}",
                    id="legal_rag.W004",
                )
            )
            continue

        if data is None:
            warnings.append(
                CheckWarning(
                    f"legal_rag: {rel} — file is empty.",
                    id="legal_rag.W005",
                )
            )
            continue

        if record_is_list:
            if not isinstance(data, list):
                warnings.append(
                    CheckWarning(
                        f"legal_rag: {rel} — expected a YAML list of records, "
                        f"got {type(data).__name__}.",
                        id="legal_rag.W009",
                    )
                )
                continue
            for idx, record in enumerate(data):
                for err in validator.iter_errors(record):
                    location = "/".join(str(p) for p in err.absolute_path) or "<root>"
                    name = (
                        record.get("name", f"<record {idx}>")
                        if isinstance(record, dict)
                        else f"<record {idx}>"
                    )
                    warnings.append(
                        CheckWarning(
                            f"legal_rag: {rel} — schema violation at "
                            f"{name}/{location}: {err.message}",
                            id="legal_rag.W006",
                        )
                    )
        else:
            for err in validator.iter_errors(data):
                location = "/".join(str(p) for p in err.absolute_path) or "<root>"
                warnings.append(
                    CheckWarning(
                        f"legal_rag: {rel} — schema violation at {location}: "
                        f"{err.message}",
                        id="legal_rag.W006",
                    )
                )

    return warnings
