"""Sync YAML legal-fact files from ``content/legal/`` into PostgreSQL.

Walks ``content/legal/statutes/**/*.yaml`` and ``content/legal/concepts/**/*.yaml``
(the latter is optional in Phase A — skipped if absent), validates each file
against the locked JSON Schema in ``content/legal/_schema/legal_fact.schema.json``,
and upserts a :class:`apps.legal_rag.models.LegalFact` row per file.

Behaviour locked by ``content/cto/centralised-legal-rag-store-plan.md`` §8 step 3.

  - **Idempotency key** is ``(concept_id, effective_from, content_hash)``.
    Same triple → skip (no DB write). Same ``(concept_id, effective_from)``
    but a new ``content_hash`` → spawn a new :class:`LegalFactVersion` and
    bump the parent fact. A new ``effective_from`` → a new ``LegalFact``
    row entirely (history preserved).
  - **Schema failures are per-file**, not fatal. A bad file logs CRITICAL
    and is skipped; the remaining files still sync.
  - **FK cycle handling**: ``LegalFact.current_version`` is nullable. The
    upsert is wrapped in ``transaction.atomic`` and does
    INSERT-fact (current_version=NULL) → INSERT-version → UPDATE fact.current_version.
  - **Concurrency**: acquires ``pg_advisory_lock(hashtext('sync_legal_facts'))``
    for the full run.
  - After all files: writes a :class:`LegalCorpusVersion` row, flips the
    previously-active one to ``is_active=False``.

Usage::

    python manage.py sync_legal_facts
    python manage.py sync_legal_facts --dry-run --verbose
    python manage.py sync_legal_facts --path /tmp/legal_fixtures   # for tests
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from apps.legal_rag.models import (
    LegalCorpusVersion,
    LegalFact,
    LegalFactVersion,
)
from apps.legal_rag.yaml_loader import load_safe_yaml

logger = logging.getLogger(__name__)


# ── Constants ────────────────────────────────────────────────────────── #


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
ADVISORY_LOCK_KEY = "sync_legal_facts"

_SCHEMA_REL = "content/legal/_schema/legal_fact.schema.json"
_STATUTES_REL = "content/legal/statutes"
_CONCEPTS_REL = "content/legal/concepts"


# ── Parsed-file dataclass ───────────────────────────────────────────── #


@dataclass
class ParsedFact:
    """One YAML legal-fact file, parsed and hashed."""

    path: Path
    data: dict[str, Any]
    content_hash: str
    concept_id: str
    effective_from: str  # ISO date string — kept as string for stable hashing.


# ── Command ─────────────────────────────────────────────────────────── #


class Command(BaseCommand):
    """Sync ``content/legal/*.yaml`` → PostgreSQL ``legal_rag_*`` tables."""

    help = (
        "Sync canonical legal-fact YAML files from content/legal/ into the "
        "legal_rag_* PostgreSQL tables (LegalFact, LegalFactVersion, "
        "LegalCorpusVersion). Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Parse + validate every YAML; print what would be written; "
                "do NOT touch the database."
            ),
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print one line per file processed (created/updated/skipped).",
        )
        parser.add_argument(
            "--path",
            type=str,
            default=None,
            help=(
                "Override the content/legal root directory (used by tests "
                "to point at a temporary fixture tree). Must contain a "
                "statutes/ subdirectory; concepts/ is optional."
            ),
        )

    # ── Entry point ─────────────────────────────────────────────────── #

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        verbose: bool = options["verbose"]
        custom_path: str | None = options["path"]

        legal_root, schema_path = self._resolve_roots(custom_path)
        if not legal_root.is_dir():
            raise CommandError(f"content/legal root not found: {legal_root}")
        if not schema_path.is_file():
            raise CommandError(f"JSON Schema not found: {schema_path}")

        validator = self._load_validator(schema_path)
        yaml_files = self._iter_yaml_files(legal_root)
        if not yaml_files:
            self.stdout.write(
                self.style.WARNING(
                    f"No YAML files found under {legal_root}/statutes or "
                    f"{legal_root}/concepts. Nothing to do."
                )
            )
            return

        parsed, parse_failures = self._parse_and_validate(
            yaml_files=yaml_files,
            validator=validator,
            verbose=verbose,
        )

        if dry_run:
            self._print_dry_run(parsed, parse_failures)
            return

        # Acquire the advisory lock for the entire write window.
        try:
            self._acquire_advisory_lock()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(
                f"Could not acquire pg_advisory_lock for sync: {exc}"
            ) from exc

        try:
            stats = self._upsert_all(parsed, verbose=verbose)
            corpus_version = self._publish_corpus_version(parsed)
        finally:
            self._release_advisory_lock()

        self.stdout.write(
            self.style.SUCCESS(
                f"sync_legal_facts complete — "
                f"created={stats['created']} updated={stats['updated']} "
                f"skipped={stats['skipped']} failed={len(parse_failures)} "
                f"corpus_version={corpus_version.version}"
            )
        )

    # ── Path + validator setup ─────────────────────────────────────── #

    def _resolve_roots(self, custom_path: str | None) -> tuple[Path, Path]:
        """Return ``(legal_root, schema_path)``.

        ``legal_root`` defaults to ``<repo_root>/content/legal``. The schema
        always lives under that root at ``_schema/legal_fact.schema.json``.
        """
        if custom_path:
            legal_root = Path(custom_path).resolve()
        else:
            legal_root = Path(settings.BASE_DIR).parent / "content" / "legal"
        schema_path = legal_root / "_schema" / "legal_fact.schema.json"
        return legal_root, schema_path

    def _load_validator(self, schema_path: Path) -> Draft202012Validator:
        with schema_path.open("r", encoding="utf-8") as fh:
            schema = json.load(fh)
        try:
            return Draft202012Validator(schema)
        except SchemaError as exc:
            raise CommandError(
                f"JSON Schema at {schema_path} is itself invalid: {exc.message}"
            ) from exc

    def _iter_yaml_files(self, legal_root: Path) -> list[Path]:
        files: list[Path] = []
        statutes_root = legal_root / "statutes"
        if statutes_root.is_dir():
            files.extend(sorted(statutes_root.rglob("*.yaml")))
            files.extend(sorted(statutes_root.rglob("*.yml")))
        concepts_root = legal_root / "concepts"
        if concepts_root.is_dir():
            files.extend(sorted(concepts_root.rglob("*.yaml")))
            files.extend(sorted(concepts_root.rglob("*.yml")))
        return files

    # ── Parse + validate pass ──────────────────────────────────────── #

    def _parse_and_validate(
        self,
        *,
        yaml_files: list[Path],
        validator: Draft202012Validator,
        verbose: bool,
    ) -> tuple[list[ParsedFact], list[str]]:
        """Return ``(parsed, failures)``.

        A failure (parse error, schema error, missing required field) is
        logged CRITICAL and the file is skipped. The remaining files still
        sync — one bad apple does not abort the whole run.
        """
        parsed: list[ParsedFact] = []
        failures: list[str] = []
        for path in yaml_files:
            rel = self._rel_for_log(path)
            try:
                data = load_safe_yaml(path)
            except yaml.YAMLError as exc:
                msg = f"{rel}: YAML parse error: {exc}"
                logger.critical("sync_legal_facts: %s", msg)
                failures.append(msg)
                continue

            if data is None:
                msg = f"{rel}: file is empty."
                logger.critical("sync_legal_facts: %s", msg)
                failures.append(msg)
                continue
            if not isinstance(data, dict):
                msg = (
                    f"{rel}: YAML root must be a mapping, "
                    f"got {type(data).__name__}."
                )
                logger.critical("sync_legal_facts: %s", msg)
                failures.append(msg)
                continue

            errors = sorted(
                validator.iter_errors(data),
                key=lambda e: list(e.absolute_path),
            )
            if errors:
                for err in errors:
                    loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
                    msg = f"{rel}: schema violation at {loc}: {err.message}"
                    logger.critical("sync_legal_facts: %s", msg)
                    failures.append(msg)
                continue

            try:
                content_hash = _canonical_content_hash(data)
            except Exception as exc:  # noqa: BLE001 — surface as failure
                msg = f"{rel}: could not canonicalise YAML for hashing: {exc}"
                logger.critical("sync_legal_facts: %s", msg)
                failures.append(msg)
                continue

            parsed.append(
                ParsedFact(
                    path=path,
                    data=data,
                    content_hash=content_hash,
                    concept_id=str(data["concept_id"]),
                    effective_from=str(data["effective_from"]),
                )
            )
            if verbose:
                self.stdout.write(
                    f"  parsed  {data['concept_id']:<55} {content_hash[:12]}"
                )

        return parsed, failures

    # ── Upsert pass ────────────────────────────────────────────────── #

    def _upsert_all(
        self,
        parsed: list[ParsedFact],
        *,
        verbose: bool,
    ) -> dict[str, int]:
        """Run the upsert path for every parsed file. Returns counters."""
        # Create a placeholder LegalCorpusVersion to give us a stable FK for
        # any new LegalFact rows we insert during this run. The real version
        # row (with correct hashes) is published at the end; we update the
        # FK pointer in a single UPDATE pass after publish.
        placeholder = self._ensure_placeholder_corpus()

        stats = {"created": 0, "updated": 0, "skipped": 0}
        for pf in parsed:
            outcome = self._upsert_one(pf, placeholder=placeholder)
            stats[outcome] += 1
            if verbose:
                self.stdout.write(
                    f"  {outcome:<8} {pf.concept_id:<55} {pf.content_hash[:12]}"
                )
        return stats

    @transaction.atomic
    def _upsert_one(
        self,
        pf: ParsedFact,
        *,
        placeholder: LegalCorpusVersion,
    ) -> str:
        """Apply the idempotency-keyed upsert for a single parsed file.

        Returns one of ``"created" | "updated" | "skipped"``.
        """
        existing = LegalFact.objects.filter(concept_id=pf.concept_id).first()

        if existing is not None:
            # Same content_hash AND same effective_from → no-op.
            # (effective_from sits in JSONField on LegalFactVersion.content;
            # we look it up via the version row to avoid drift.)
            current_eff = self._effective_from_for(existing)
            if (
                existing.content_hash == pf.content_hash
                and current_eff == pf.effective_from
            ):
                return "skipped"

            # New effective_from: a fresh law version. Spawn a NEW LegalFact
            # row (history preserved on the old one). The old row keeps its
            # is_active=True for now — Phase A doesn't yet have a soft-delete
            # path. The renderer/queries pick the newest by effective_from.
            if current_eff != pf.effective_from:
                self._create_new_fact(pf, placeholder=placeholder)
                return "created"

            # Same effective_from, new content_hash → bump version.
            self._bump_fact_version(pf, fact=existing, placeholder=placeholder)
            return "updated"

        # No existing row → first create.
        self._create_new_fact(pf, placeholder=placeholder)
        return "created"

    def _create_new_fact(
        self,
        pf: ParsedFact,
        *,
        placeholder: LegalCorpusVersion,
    ) -> LegalFact:
        """Insert a LegalFact + LegalFactVersion pair atomically.

        Handles the FK cycle by inserting fact with ``current_version=None``,
        inserting the version, then UPDATE'ing fact.current_version.
        """
        fact = LegalFact.objects.create(
            concept_id=pf.concept_id,
            type=pf.data["type"],
            citation_string=pf.data["citation_string"],
            plain_english_summary=pf.data["plain_english_summary"],
            statute_text=pf.data.get("statute_text", "") or "",
            statute_text_verbatim=bool(pf.data.get("statute_text_verbatim", False)),
            citation_confidence=pf.data["citation_confidence"],
            legal_provisional=bool(pf.data.get("legal_provisional", False)),
            verification_status=pf.data["verification_status"],
            corpus_version=placeholder,
            fact_version=1,
            content_hash=pf.content_hash,
            current_version=None,
            applicability=pf.data.get("applicability") or {},
            topic_tags=list(pf.data.get("topic_tags") or []),
            disclaimers=list(pf.data.get("disclaimers") or []),
            is_active=True,
        )
        version = LegalFactVersion.objects.create(
            fact=fact,
            version=1,
            content=pf.data,
            content_hash=pf.content_hash,
        )
        fact.current_version = version
        fact.save(update_fields=["current_version"])
        return fact

    def _bump_fact_version(
        self,
        pf: ParsedFact,
        *,
        fact: LegalFact,
        placeholder: LegalCorpusVersion,
    ) -> LegalFact:
        """Bump an existing LegalFact: write a new version row, update head."""
        next_version_num = fact.fact_version + 1
        version = LegalFactVersion.objects.create(
            fact=fact,
            version=next_version_num,
            content=pf.data,
            content_hash=pf.content_hash,
        )

        fact.type = pf.data["type"]
        fact.citation_string = pf.data["citation_string"]
        fact.plain_english_summary = pf.data["plain_english_summary"]
        fact.statute_text = pf.data.get("statute_text", "") or ""
        fact.statute_text_verbatim = bool(pf.data.get("statute_text_verbatim", False))
        fact.citation_confidence = pf.data["citation_confidence"]
        fact.legal_provisional = bool(pf.data.get("legal_provisional", False))
        fact.verification_status = pf.data["verification_status"]
        fact.corpus_version = placeholder
        fact.fact_version = next_version_num
        fact.content_hash = pf.content_hash
        fact.current_version = version
        fact.applicability = pf.data.get("applicability") or {}
        fact.topic_tags = list(pf.data.get("topic_tags") or [])
        fact.disclaimers = list(pf.data.get("disclaimers") or [])
        fact.is_active = True
        fact.save()
        return fact

    def _effective_from_for(self, fact: LegalFact) -> str | None:
        """Return the ``effective_from`` of the fact's current version, or None."""
        cv = fact.current_version
        if cv is None:
            return None
        content = cv.content or {}
        eff = content.get("effective_from")
        return str(eff) if eff is not None else None

    # ── Placeholder + corpus version handling ──────────────────────── #

    def _ensure_placeholder_corpus(self) -> LegalCorpusVersion:
        """Get-or-create a ``placeholder`` LegalCorpusVersion row.

        We need a FK target for new LegalFact rows during the upsert pass —
        the real corpus_version row (with the correct merkle hash) is
        published at the end. We re-point all touched facts in a single
        UPDATE after publish.
        """
        placeholder, _ = LegalCorpusVersion.objects.get_or_create(
            version="placeholder-sync-pending",
            defaults={
                "merkle_root": "0" * 64,
                "embedding_model": _embedding_model_name(),
                "fact_count": 0,
                "is_active": False,
            },
        )
        return placeholder

    def _publish_corpus_version(
        self, parsed: list[ParsedFact]
    ) -> LegalCorpusVersion:
        """Compute + persist the final ``LegalCorpusVersion``.

        - ``version`` = ``"legal-rag-v0.1-" + sha256(...)[:12]``
        - ``merkle_root`` = sha256 over all fact content_hashes, ordered by concept_id
        - flips the previously-active version to ``is_active=False``
        - re-points every LegalFact's ``corpus_version`` to the new row
        """
        # Pull every active fact, not just the ones touched this run, so the
        # corpus_version reflects the whole present-day corpus state.
        rows = list(
            LegalFact.objects.filter(is_active=True)
            .order_by("concept_id")
            .values("concept_id", "content_hash")
        )
        manifest = ",".join(
            f"{row['concept_id']}:{row['content_hash']}" for row in rows
        )
        manifest_hash = hashlib.sha256(manifest.encode("utf-8")).hexdigest()
        version_string = f"legal-rag-v0.1-{manifest_hash[:12]}"
        merkle_root = hashlib.sha256(
            "".join(row["content_hash"] for row in rows).encode("utf-8")
        ).hexdigest()

        with transaction.atomic():
            # Deactivate previous active version(s).
            LegalCorpusVersion.objects.filter(is_active=True).update(is_active=False)

            corpus, created = LegalCorpusVersion.objects.get_or_create(
                version=version_string,
                defaults={
                    "merkle_root": merkle_root,
                    "embedding_model": _embedding_model_name(),
                    "fact_count": len(rows),
                    "is_active": True,
                },
            )
            if not created:
                # Idempotent re-runs land here when nothing has changed.
                # Ensure the row is marked active.
                corpus.merkle_root = merkle_root
                corpus.fact_count = len(rows)
                corpus.is_active = True
                corpus.save(
                    update_fields=["merkle_root", "fact_count", "is_active"]
                )

            # Re-point every fact at the freshly-published version.
            LegalFact.objects.filter(is_active=True).update(corpus_version=corpus)

        return corpus

    # ── Advisory lock ──────────────────────────────────────────────── #

    def _acquire_advisory_lock(self) -> None:
        """``pg_advisory_lock(hashtext('sync_legal_facts'))`` — held across the run."""
        if connection.vendor != "postgresql":
            logger.warning(
                "sync_legal_facts: not running on PostgreSQL (vendor=%r) — "
                "skipping advisory lock. Tests / SQLite envs only.",
                connection.vendor,
            )
            return
        with connection.cursor() as cur:
            cur.execute(
                "SELECT pg_advisory_lock(hashtext(%s))", [ADVISORY_LOCK_KEY]
            )

    def _release_advisory_lock(self) -> None:
        if connection.vendor != "postgresql":
            return
        with connection.cursor() as cur:
            cur.execute(
                "SELECT pg_advisory_unlock(hashtext(%s))", [ADVISORY_LOCK_KEY]
            )

    # ── Dry-run output ─────────────────────────────────────────────── #

    def _print_dry_run(
        self,
        parsed: list[ParsedFact],
        failures: list[str],
    ) -> None:
        for pf in parsed:
            rel = self._rel_for_log(pf.path)
            self.stdout.write(
                f"  [dry-run] {pf.concept_id:<55} "
                f"{pf.content_hash[:12]}  {rel}"
            )
        if failures:
            for line in failures:
                self.stderr.write(self.style.ERROR(f"  [skip]    {line}"))
        # Compute the would-be corpus version using parsed values only —
        # idempotent preview that does not require DB state.
        manifest = ",".join(
            f"{pf.concept_id}:{pf.content_hash}"
            for pf in sorted(parsed, key=lambda p: p.concept_id)
        )
        manifest_hash = hashlib.sha256(manifest.encode("utf-8")).hexdigest()
        version_string = f"legal-rag-v0.1-{manifest_hash[:12]}"
        self.stdout.write(
            self.style.SUCCESS(
                f"Dry-run complete — would write {len(parsed)} fact(s), "
                f"skip {len(failures)} bad file(s). "
                f"Would-be corpus_version: {version_string}"
            )
        )

    # ── Utilities ──────────────────────────────────────────────────── #

    def _rel_for_log(self, path: Path) -> str:
        try:
            return str(path.relative_to(Path(settings.BASE_DIR).parent))
        except ValueError:
            return str(path)


# ── Module-level helpers (kept importable for tests) ────────────────── #


def _canonical_content_hash(data: dict[str, Any]) -> str:
    """Compute the SHA256 of a canonical YAML serialisation of ``data``.

    Canonicalisation = ``yaml.safe_dump(sort_keys=True, allow_unicode=True,
    default_flow_style=False)``. This makes whitespace + key-order
    differences in the source file invisible to the hash, so idempotent
    re-runs are stable.
    """
    # Drop any author-set content_hash before canonicalising so the
    # hash never depends on a previously-computed hash.
    body = {k: v for k, v in data.items() if k != "content_hash"}
    body = _to_jsonable(body)
    canonical = yaml.safe_dump(
        body,
        sort_keys=True,
        allow_unicode=True,
        default_flow_style=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _to_jsonable(value: Any) -> Any:
    """Convert any date/datetime values to ISO strings so dumps are stable.

    The StringDateLoader leaves dates as strings, but defensive normalisation
    handles cases where an upstream caller passes a dict with real dates.
    """
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _embedding_model_name() -> str:
    """Resolve the embedding model name.

    Locked to ``text-embedding-3-small`` to match ``reindex_lease_corpus``
    (same ChromaDB infra; same embedder choice). The mock embedder used
    when ``OPENAI_API_KEY`` is unset still records this name on the
    LegalCorpusVersion row — drift between the recorded model and the
    actual embedder is detected by the indexer at re-deploy time.
    """
    return DEFAULT_EMBEDDING_MODEL


__all__ = ["Command", "ParsedFact"]
