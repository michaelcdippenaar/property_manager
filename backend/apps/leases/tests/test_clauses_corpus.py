"""Tests for the lease-AI clauses corpus (Phase 1 Day 1-2 scaffold).

Covers:
    - ``manage.py reindex_lease_corpus --dry-run`` exits 0 with output.
    - Every seed YAML parses, validates against the JSON Schema, and
      produces a stable sha256 ``content_hash``.
    - ``query_clauses(topic_tags=["deposit"])`` returns at least one
      ``ClauseChunk`` against a mocked ChromaDB.

Run:
    cd backend && .venv/bin/python -m pytest \
        apps/leases/tests/test_clauses_corpus.py -q
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from unittest.mock import patch

import yaml
from django.core.management import call_command
from django.test import TestCase
from jsonschema import Draft202012Validator

from apps.leases.lease_law_corpus_queries import ClauseChunk, query_clauses

CORPUS_ROOT = (
    Path(__file__).resolve().parents[1] / "lease_law_corpus"
)
SCHEMA_PATH = CORPUS_ROOT / "_schema" / "clause_chunk.schema.json"
CLAUSES_ROOT = CORPUS_ROOT / "clauses"


class LeaseClausesCorpusSchemaTests(TestCase):
    """Every seed YAML must satisfy the schema and hash deterministically."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with SCHEMA_PATH.open("r", encoding="utf-8") as fh:
            schema = json.load(fh)
        cls.validator = Draft202012Validator(schema)

    def test_schema_file_exists(self):
        self.assertTrue(SCHEMA_PATH.is_file(), f"Missing schema: {SCHEMA_PATH}")

    def test_at_least_three_seed_clauses_present(self):
        files = sorted(CLAUSES_ROOT.rglob("*.yml"))
        self.assertGreaterEqual(
            len(files), 3, "Expected at least three seed clause YAML files."
        )

    def test_every_seed_clause_validates_and_hashes(self):
        files = sorted(CLAUSES_ROOT.rglob("*.yml"))
        self.assertTrue(files, "No clause YAML files discovered.")

        seen_ids: set[str] = set()
        for path in files:
            with self.subTest(path=str(path.relative_to(CORPUS_ROOT))):
                raw = path.read_text(encoding="utf-8")
                data = yaml.safe_load(raw)
                self.assertIsInstance(data, dict, f"{path}: YAML root must be a mapping.")
                # The indexer owns content_hash; authors must not hand-set it.
                data.pop("content_hash", None)

                errors = sorted(
                    self.validator.iter_errors(data),
                    key=lambda e: list(e.absolute_path),
                )
                self.assertFalse(
                    errors,
                    msg="\n".join(f"{e.absolute_path}: {e.message}" for e in errors),
                )

                # Hash must be a stable sha256 over the canonical YAML form.
                canonical = yaml.safe_dump(
                    data,
                    sort_keys=True,
                    allow_unicode=True,
                    default_flow_style=False,
                )
                content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                self.assertRegex(content_hash, r"^[0-9a-f]{64}$")

                # id uniqueness across the seed set.
                self.assertNotIn(
                    data["id"], seen_ids, f"Duplicate clause id: {data['id']}"
                )
                seen_ids.add(data["id"])

                # id is the filename stem prefixed with "clause-".
                expected_id = f"clause-{path.stem}"
                self.assertEqual(
                    data["id"],
                    expected_id,
                    f"{path}: id {data['id']!r} != expected {expected_id!r}",
                )


class ReindexLeaseCorpusDryRunTests(TestCase):
    """``manage.py reindex_lease_corpus --dry-run`` is the CI smoke test."""

    def test_dry_run_exits_zero_with_output(self):
        out = io.StringIO()
        err = io.StringIO()
        try:
            call_command("reindex_lease_corpus", "--dry-run", stdout=out, stderr=err)
        except SystemExit as exc:  # CommandError → SystemExit
            self.fail(f"reindex_lease_corpus --dry-run raised SystemExit({exc.code}).")

        stdout = out.getvalue()
        self.assertIn("[dry-run]", stdout)
        self.assertIn("Dry-run complete", stdout)
        self.assertEqual(err.getvalue(), "")

    def test_check_mode_passes_schema_validation(self):
        out = io.StringIO()
        err = io.StringIO()
        try:
            call_command("reindex_lease_corpus", "--check", stdout=out, stderr=err)
        except SystemExit as exc:
            self.fail(
                f"reindex_lease_corpus --check exited non-zero "
                f"({exc.code}); stderr:\n{err.getvalue()}"
            )

        self.assertIn("Schema check PASSED", out.getvalue())
        self.assertEqual(err.getvalue(), "")


class QueryClausesFilterTests(TestCase):
    """``query_clauses`` must hit a mocked ChromaDB and return ClauseChunks."""

    def _fake_collection_with_deposit_chunks(self):
        """Build a fake Chroma collection whose ``get`` returns one deposit chunk."""

        class _FakeCol:
            def get(self, *, where=None, limit=None, include=None):
                # Mimic Chroma's response shape.
                meta = {
                    "id": "clause-deposit-interest-bearing-account-v1",
                    "type": "clause",
                    "version": 1,
                    "content_hash": "a" * 64,
                    "clause_title": "Deposit — Interest-Bearing Account",
                    "topic_tags": "deposit,mandatory_clause,interest",
                    "property_types": "sectional_title,freehold,apartment,townhouse",
                    "tenant_counts": "any",
                    "lease_types": "fixed_term,month_to_month",
                    "related_citations": "rha-s5-3-f-deposit-interest-bearing-account",
                    "merge_fields_used": "deposit,deposit_words,deposit_account_bank_name,deposit_account_holder",
                    "citation_confidence": "low",
                    "legal_provisional": True,
                    "confidence_level": "ai_curated",
                    "curator": "claude+mc",
                    "source_path": "clauses/deposit/deposit-interest-bearing-account-v1.yml",
                }
                return {
                    "ids": [meta["id"]],
                    "documents": [
                        f"{meta['clause_title']} The deposit shall be held…"
                    ],
                    "metadatas": [meta],
                }

            def query(self, *args, **kwargs):  # not used here
                raise AssertionError(
                    "query() should not be called in filter-only path."
                )

        return _FakeCol()

    def test_query_by_topic_tag_returns_chunk(self):
        fake_col = self._fake_collection_with_deposit_chunks()
        with patch(
            "apps.leases.lease_law_corpus_queries._get_collection",
            return_value=fake_col,
        ):
            results = query_clauses(topic_tags=["deposit"])

        self.assertEqual(len(results), 1)
        chunk = results[0]
        self.assertIsInstance(chunk, ClauseChunk)
        self.assertEqual(chunk.id, "clause-deposit-interest-bearing-account-v1")
        self.assertIn("deposit", chunk.topic_tags)
        self.assertIn("sectional_title", chunk.property_types)
        self.assertTrue(chunk.legal_provisional)
        self.assertEqual(
            chunk.related_citations,
            ("rha-s5-3-f-deposit-interest-bearing-account",),
        )

    def test_query_returns_empty_list_when_chroma_unavailable(self):
        with patch(
            "apps.leases.lease_law_corpus_queries._get_collection",
            return_value=None,
        ):
            results = query_clauses(topic_tags=["deposit"])
        self.assertEqual(results, [])
