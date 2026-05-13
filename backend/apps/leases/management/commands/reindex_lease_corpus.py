"""
Reindex the lease-AI clauses corpus into ChromaDB.

Walks ``backend/apps/leases/lease_law_corpus/clauses/**/*.yml``, validates
each YAML against ``_schema/clause_chunk.schema.json``, computes a content
hash, and upserts the chunk into the ``klikk_lease_clauses_v1`` collection
under ``settings.LEASE_AI_CHROMA_PATH``.

Behaviour locked by ``docs/system/lease-ai-agent-architecture.md`` §6.3
(decisions 5, 6, 8):

  - NOT invoked at app startup. Either the deploy release hook, a manual
    run, or CI calls this command.
  - Concurrency safety: acquires ``pg_advisory_lock(hashtext(
    'reindex_lease_corpus'))`` before writing.
  - Idempotent: chunks whose ``content_hash`` already match are skipped.
  - Statutes / case_law / pitfalls are owned by ``apps.legal_rag`` per
    ``content/cto/centralised-legal-rag-store-plan.md`` §8 step 6 — this
    command only indexes ``clauses/**/*.yml``.

Usage:
    python manage.py reindex_lease_corpus
    python manage.py reindex_lease_corpus --dry-run
    python manage.py reindex_lease_corpus --check   # schema only; CI gate
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from jsonschema import Draft202012Validator

logger = logging.getLogger(__name__)


CORPUS_ROOT = Path(__file__).resolve().parents[2] / "lease_law_corpus"
SCHEMA_PATH = CORPUS_ROOT / "_schema" / "clause_chunk.schema.json"
CLAUSES_ROOT = CORPUS_ROOT / "clauses"
LAST_INDEX_PATH = CORPUS_ROOT / ".last_index.json"

COLLECTION_NAME = "klikk_lease_clauses_v1"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
MOCK_EMBEDDING_MODEL = "klikk-mock-deterministic-v1"
MOCK_EMBED_DIM = 1536  # match text-embedding-3-small so swap is dimension-stable


@dataclass
class ParsedChunk:
    """One YAML clause file, parsed and hashed."""

    path: Path
    data: dict[str, Any]
    canonical_yaml: str
    content_hash: str


class Command(BaseCommand):
    help = (
        "Reindex the lease-AI clauses corpus into the "
        f"{COLLECTION_NAME!r} ChromaDB collection."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Parse and validate every YAML; print what would be indexed; "
                "do NOT write to ChromaDB and do NOT update .last_index.json."
            ),
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help=(
                "Schema-only mode. Validates every YAML against the schema. "
                "Exits non-zero on the first failure. Skips indexing entirely. "
                "Used in CI."
            ),
        )

    # ── Entry point ──────────────────────────────────────────────── #

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        check_only: bool = options["check"]

        if not CORPUS_ROOT.is_dir():
            raise CommandError(f"Corpus root not found: {CORPUS_ROOT}")
        if not SCHEMA_PATH.is_file():
            raise CommandError(f"Schema file not found: {SCHEMA_PATH}")
        if not CLAUSES_ROOT.is_dir():
            raise CommandError(f"Clauses directory not found: {CLAUSES_ROOT}")

        validator = self._load_validator()

        yaml_files = sorted(CLAUSES_ROOT.rglob("*.yml"))
        if not yaml_files:
            self.stdout.write(
                self.style.WARNING(
                    f"No clause YAML files found under {CLAUSES_ROOT}. Nothing to do."
                )
            )
            return

        # ── Parse + validate every file (used in all modes) ──────── #
        parsed: list[ParsedChunk] = []
        failures: list[str] = []
        for path in yaml_files:
            try:
                chunk = self._parse_and_hash(path)
            except Exception as exc:  # noqa: BLE001 — surface as CLI failure
                failures.append(f"{path.relative_to(CORPUS_ROOT)}: parse error: {exc}")
                continue

            errors = sorted(
                validator.iter_errors(chunk.data),
                key=lambda e: list(e.absolute_path),
            )
            if errors:
                for err in errors:
                    loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
                    failures.append(
                        f"{path.relative_to(CORPUS_ROOT)}: schema error at {loc}: {err.message}"
                    )
                continue

            # Cross-check: id suffix must encode the same version
            id_version = chunk.data["id"].rsplit("-v", 1)[-1]
            if id_version != str(chunk.data["version"]):
                failures.append(
                    f"{path.relative_to(CORPUS_ROOT)}: id ends with "
                    f"v{id_version} but version field is {chunk.data['version']}."
                )
                continue

            # Cross-check: every merge field in clause_body is declared.
            undeclared = _placeholders_not_in_declared(
                chunk.data["clause_body"], chunk.data["merge_fields_used"]
            )
            if undeclared:
                failures.append(
                    f"{path.relative_to(CORPUS_ROOT)}: clause_body uses "
                    f"undeclared merge fields: {sorted(undeclared)}."
                )
                continue

            parsed.append(chunk)

        if failures:
            for line in failures:
                self.stderr.write(self.style.ERROR(line))
            self.stderr.write(
                self.style.ERROR(
                    f"\nCorpus validation FAILED: {len(failures)} issue(s) "
                    f"across {len(yaml_files)} file(s)."
                )
            )
            sys.exit(1)

        if check_only:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Schema check PASSED for {len(parsed)} clause file(s)."
                )
            )
            return

        # ── Index (dry-run or real) ──────────────────────────────── #
        if dry_run:
            self._print_dry_run_preview(parsed)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry-run complete. {len(parsed)} clause(s) would be indexed."
                )
            )
            return

        try:
            self._acquire_advisory_lock()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(
                f"Could not acquire pg_advisory_lock for reindex: {exc}"
            ) from exc

        try:
            indexer = _ChromaIndexer(
                persist_path=Path(settings.LEASE_AI_CHROMA_PATH),
                collection_name=COLLECTION_NAME,
                stdout=self.stdout,
                style=self.style,
            )
            embedder, model_name = _build_embedder(stdout=self.stdout, style=self.style)

            indexed, skipped = indexer.upsert_chunks(parsed, embedder=embedder)
        finally:
            self._release_advisory_lock()

        self._write_last_index_record(
            parsed=parsed,
            embedding_model=model_name,
            indexed=indexed,
            skipped=skipped,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Indexed {indexed} new/changed clause(s); "
                f"skipped {skipped} unchanged. "
                f"Collection: {COLLECTION_NAME} at {settings.LEASE_AI_CHROMA_PATH}."
            )
        )

    # ── Helpers ──────────────────────────────────────────────────── #

    def _load_validator(self) -> Draft202012Validator:
        with SCHEMA_PATH.open("r", encoding="utf-8") as fh:
            schema = json.load(fh)
        return Draft202012Validator(schema)

    def _parse_and_hash(self, path: Path) -> ParsedChunk:
        raw = path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        if not isinstance(data, dict):
            raise ValueError(
                f"YAML root must be a mapping, got {type(data).__name__}."
            )

        # Authors may not set content_hash; the indexer owns it. Pop any
        # value present in source so validation + canonical-yaml are stable.
        data.pop("content_hash", None)

        canonical_yaml = yaml.safe_dump(
            data,
            sort_keys=True,
            allow_unicode=True,
            default_flow_style=False,
        )
        content_hash = hashlib.sha256(canonical_yaml.encode("utf-8")).hexdigest()
        data["content_hash"] = content_hash
        return ParsedChunk(
            path=path,
            data=data,
            canonical_yaml=canonical_yaml,
            content_hash=content_hash,
        )

    def _print_dry_run_preview(self, parsed: list[ParsedChunk]) -> None:
        for chunk in parsed:
            rel = chunk.path.relative_to(CORPUS_ROOT)
            self.stdout.write(
                f"  [dry-run] {chunk.data['id']:<55} "
                f"({chunk.content_hash[:12]})  {rel}"
            )

    def _acquire_advisory_lock(self) -> None:
        """``pg_advisory_lock(hashtext('reindex_lease_corpus'))`` — held
        for the lifetime of the connection used here. Released explicitly
        by ``_release_advisory_lock`` in the finally block."""
        if connection.vendor != "postgresql":
            logger.warning(
                "reindex_lease_corpus: not running on PostgreSQL "
                "(vendor=%r) — skipping advisory lock. "
                "Tests / SQLite envs only.",
                connection.vendor,
            )
            return
        with connection.cursor() as cur:
            cur.execute("SELECT pg_advisory_lock(hashtext(%s))", ["reindex_lease_corpus"])

    def _release_advisory_lock(self) -> None:
        if connection.vendor != "postgresql":
            return
        with connection.cursor() as cur:
            cur.execute(
                "SELECT pg_advisory_unlock(hashtext(%s))", ["reindex_lease_corpus"]
            )

    def _write_last_index_record(
        self,
        *,
        parsed: list[ParsedChunk],
        embedding_model: str,
        indexed: int,
        skipped: int,
    ) -> None:
        hashes_sorted = sorted(c.content_hash for c in parsed)
        corpus_hash = hashlib.sha256(
            "".join(hashes_sorted).encode("utf-8")
        ).hexdigest()
        record = {
            "run_at": datetime.now(tz=timezone.utc).isoformat(),
            "chunk_count": len(parsed),
            "corpus_hash": corpus_hash,
            "embedding_model": embedding_model,
            "indexed": indexed,
            "skipped": skipped,
            "collection_name": COLLECTION_NAME,
        }
        LAST_INDEX_PATH.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


# ── Embedder ─────────────────────────────────────────────────────── #


def _build_embedder(
    *, stdout, style
) -> tuple[Any, str]:
    """Return ``(embed_callable, model_name)``.

    Uses OpenAI ``text-embedding-3-small`` when ``OPENAI_API_KEY`` is set,
    otherwise a deterministic mock embedder useful for Day 1-2 + CI.
    """
    api_key = os.environ.get("OPENAI_API_KEY") or getattr(
        settings, "OPENAI_API_KEY", ""
    )
    if not api_key:
        stdout.write(
            style.WARNING(
                "OPENAI_API_KEY not set — using deterministic mock embedder. "
                "ChromaDB will hold real chunks, but vector similarity is "
                "hash-based, not semantic. Set OPENAI_API_KEY for production."
            )
        )
        return _mock_embed, MOCK_EMBEDDING_MODEL

    try:
        from openai import OpenAI  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        stdout.write(
            style.WARNING(
                f"openai SDK import failed ({exc}); falling back to mock embedder."
            )
        )
        return _mock_embed, MOCK_EMBEDDING_MODEL

    client = OpenAI(api_key=api_key)

    def _openai_embed(texts: list[str]) -> list[list[float]]:
        resp = client.embeddings.create(
            model=DEFAULT_EMBEDDING_MODEL, input=texts
        )
        return [item.embedding for item in resp.data]

    return _openai_embed, DEFAULT_EMBEDDING_MODEL


def _mock_embed(texts: list[str]) -> list[list[float]]:
    """Deterministic hash-based mock embedder.

    Produces a stable float vector per input via sha256 expansion. NOT
    semantic — just enough to round-trip through ChromaDB and let metadata
    filters work in tests without an API key.
    """
    vectors: list[list[float]] = []
    for text in texts:
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        # Tile the 32-byte digest out to MOCK_EMBED_DIM bytes,
        # normalise to [-1, 1].
        repeats = (MOCK_EMBED_DIM + len(seed) - 1) // len(seed)
        tiled = (seed * repeats)[:MOCK_EMBED_DIM]
        vec = [(b / 127.5) - 1.0 for b in tiled]
        vectors.append(vec)
    return vectors


# ── ChromaDB upsert ─────────────────────────────────────────────── #


class _ChromaIndexer:
    """Thin wrapper around chromadb.PersistentClient for the clauses corpus."""

    def __init__(
        self,
        *,
        persist_path: Path,
        collection_name: str,
        stdout,
        style,
    ):
        self.persist_path = persist_path
        self.collection_name = collection_name
        self.stdout = stdout
        self.style = style
        self._client = None
        self._col = None

    def _ensure_collection(self):
        if self._col is not None:
            return self._col
        import chromadb  # type: ignore[import-not-found]

        self.persist_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self.persist_path))
        # No embedding_function — we provide vectors explicitly so the
        # collection is embedder-agnostic.
        self._col = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        return self._col

    def upsert_chunks(
        self,
        chunks: list[ParsedChunk],
        *,
        embedder,
    ) -> tuple[int, int]:
        """Upsert chunks whose ``content_hash`` does not already match.

        Returns ``(indexed, skipped)``.
        """
        col = self._ensure_collection()

        # Fetch existing content_hashes by id in one round-trip.
        ids = [c.data["id"] for c in chunks]
        try:
            existing = col.get(ids=ids, include=["metadatas"])
        except Exception as exc:  # noqa: BLE001 — empty collection edge case
            logger.warning("ChromaDB get(ids=…) failed: %s; treating all as new.", exc)
            existing = {"ids": [], "metadatas": []}

        existing_hash_by_id: dict[str, str] = {}
        for cid, meta in zip(existing.get("ids") or [], existing.get("metadatas") or []):
            if meta:
                existing_hash_by_id[cid] = str(meta.get("content_hash") or "")

        to_index: list[ParsedChunk] = [
            c
            for c in chunks
            if existing_hash_by_id.get(c.data["id"]) != c.content_hash
        ]
        skipped = len(chunks) - len(to_index)

        if not to_index:
            return 0, skipped

        documents = [
            f"{c.data['clause_title']} {c.data['clause_body']}".strip()
            for c in to_index
        ]
        embeddings = embedder(documents)

        col.upsert(
            ids=[c.data["id"] for c in to_index],
            documents=documents,
            embeddings=embeddings,
            metadatas=[_metadata_for(c) for c in to_index],
        )
        return len(to_index), skipped


def _metadata_for(chunk: ParsedChunk) -> dict[str, Any]:
    """Flatten the YAML into ChromaDB metadata.

    ChromaDB metadata values must be scalar (str / int / float / bool / None),
    so list-valued YAML fields are serialised as comma-separated strings.
    """
    data = chunk.data
    applicability = data.get("applicability") or {}
    return {
        "id": data["id"],
        "type": data["type"],
        "version": int(data["version"]),
        "content_hash": chunk.content_hash,
        "clause_title": data["clause_title"],
        "topic_tags": _csv(data.get("topic_tags")),
        "property_types": _csv(applicability.get("property_types")),
        "tenant_counts": _csv(applicability.get("tenant_counts")),
        "lease_types": _csv(applicability.get("lease_types")),
        "related_citations": _csv(data.get("related_citations")),
        "merge_fields_used": _csv(data.get("merge_fields_used")),
        "citation_confidence": data.get("citation_confidence") or "",
        "legal_provisional": bool(data.get("legal_provisional", False)),
        "confidence_level": data.get("confidence_level") or "",
        "curator": data.get("curator") or "",
        "source_path": str(chunk.path.relative_to(CORPUS_ROOT)),
    }


def _csv(values: Iterable[Any] | None) -> str:
    if not values:
        return ""
    return ",".join(str(v) for v in values)


# ── Merge-field cross-check ─────────────────────────────────────── #

import re  # noqa: E402 — placed late to keep public surface near top

_MERGE_FIELD_RE = re.compile(r"{{\s*([a-z][a-z0-9_]*)\s*}}")


def _placeholders_not_in_declared(
    clause_body: str, declared: list[str]
) -> set[str]:
    """Return the set of ``{{ name }}`` placeholders in ``clause_body`` that
    are not in ``declared``. Returns an empty set when all placeholders are
    declared (or no placeholders are used)."""
    used = set(_MERGE_FIELD_RE.findall(clause_body or ""))
    return used - set(declared or [])
