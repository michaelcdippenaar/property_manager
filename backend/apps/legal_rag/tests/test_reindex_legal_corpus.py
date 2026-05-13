"""Tests for ``manage.py reindex_legal_corpus``.

We do **not** hit the real ChromaDB persistent path. ``_ChromaIndexer``
is patched so we can observe ``upsert_facts`` invocations and the
.last_index.json record without an on-disk vector store.
"""
from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.legal_rag.management.commands.reindex_legal_corpus import (
    COLLECTION_NAME,
    DEFAULT_EMBEDDING_MODEL,
    _embedded_text_for,
    _metadata_for,
    IndexedFact,
)
from apps.legal_rag.models import LegalCorpusVersion, LegalFact, LegalFactVersion


def _make_active_corpus_with_facts(*, fact_count: int = 2) -> LegalCorpusVersion:
    """Create a minimal active corpus + N fact rows for the indexer to read."""
    corpus = LegalCorpusVersion.objects.create(
        version="legal-rag-v0.1-deadbeef0000",
        merkle_root="cafe" * 16,
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        fact_count=fact_count,
        is_active=True,
    )
    for i in range(fact_count):
        fact = LegalFact.objects.create(
            concept_id=f"rha-test-{i}",
            type="statute_provision",
            citation_string=f"RHA s{10 + i}",
            plain_english_summary=f"Summary for fact {i}.",
            citation_confidence="high",
            legal_provisional=False,
            verification_status="mc_reviewed",
            corpus_version=corpus,
            fact_version=1,
            content_hash=f"{i:064d}",
            applicability={
                "property_types": ["apartment"],
                "tenant_counts": ["any"],
                "lease_types": ["fixed_term"],
                "jurisdictions": ["za-national"],
            },
            topic_tags=["test", f"tag_{i}"],
            disclaimers=["Not legal advice."],
            is_active=True,
        )
        version = LegalFactVersion.objects.create(
            fact=fact,
            version=1,
            content={"effective_from": "2014-08-01"},
            content_hash=f"{i:064d}",
        )
        fact.current_version = version
        fact.save(update_fields=["current_version"])
    return corpus


class TestReindexLegalCorpus(TestCase):

    def setUp(self) -> None:
        # Point the persistent ChromaDB path at a per-test temp directory so
        # the .last_index.json write side-effect lands in tmp, not the repo.
        import tempfile

        self._tmp_path = Path(tempfile.mkdtemp(prefix="legal_rag_chroma_test_"))
        self._settings_override = override_settings(
            LEGAL_RAG_CHROMA_PATH=self._tmp_path
        )
        self._settings_override.enable()

    def tearDown(self) -> None:
        import shutil

        self._settings_override.disable()
        shutil.rmtree(self._tmp_path, ignore_errors=True)

    # ── tests ───────────────────────────────────────────────────── #

    @patch(
        "apps.legal_rag.management.commands.reindex_legal_corpus._ChromaIndexer"
    )
    def test_dry_run_no_chroma_writes(self, mock_indexer_cls: MagicMock) -> None:
        """Dry-run must NOT construct an indexer or write .last_index.json."""
        _make_active_corpus_with_facts(fact_count=2)
        out = StringIO()

        call_command("reindex_legal_corpus", "--dry-run", stdout=out)

        mock_indexer_cls.assert_not_called()
        self.assertFalse((self._tmp_path / ".last_index.json").exists())
        self.assertIn("Dry-run complete", out.getvalue())

    @patch(
        "apps.legal_rag.management.commands.reindex_legal_corpus._ChromaIndexer"
    )
    def test_reindex_writes_one_record_per_active_fact(
        self, mock_indexer_cls: MagicMock
    ) -> None:
        """The indexer is invoked once with every active fact."""
        _make_active_corpus_with_facts(fact_count=3)

        mock_instance = MagicMock()
        mock_instance.upsert_facts.return_value = (3, 0)
        mock_indexer_cls.return_value = mock_instance

        out = StringIO()
        call_command("reindex_legal_corpus", stdout=out)

        mock_indexer_cls.assert_called_once()
        # ``upsert_facts`` should receive an iterable with one entry per fact.
        _, kwargs = mock_instance.upsert_facts.call_args
        # Positional args first.
        args, _ = mock_instance.upsert_facts.call_args
        facts_arg = args[0]
        self.assertEqual(len(facts_arg), 3)
        self.assertEqual(
            sorted(f.concept_id for f in facts_arg),
            ["rha-test-0", "rha-test-1", "rha-test-2"],
        )

        # .last_index.json should be written.
        record_path = self._tmp_path / ".last_index.json"
        self.assertTrue(record_path.exists())
        record = json.loads(record_path.read_text())
        self.assertEqual(record["fact_count"], 3)
        self.assertEqual(record["collection_name"], COLLECTION_NAME)
        self.assertEqual(record["indexed"], 3)
        self.assertEqual(record["corpus_version"], "legal-rag-v0.1-deadbeef0000")

    @patch(
        "apps.legal_rag.management.commands.reindex_legal_corpus._ChromaIndexer"
    )
    def test_skip_when_content_hash_unchanged(
        self, mock_indexer_cls: MagicMock
    ) -> None:
        """When the indexer reports 0 indexed / N skipped, the command exits ok."""
        _make_active_corpus_with_facts(fact_count=2)
        mock_instance = MagicMock()
        mock_instance.upsert_facts.return_value = (0, 2)
        mock_indexer_cls.return_value = mock_instance

        out = StringIO()
        call_command("reindex_legal_corpus", stdout=out)

        record = json.loads((self._tmp_path / ".last_index.json").read_text())
        self.assertEqual(record["indexed"], 0)
        self.assertEqual(record["skipped"], 2)

    @patch(
        "apps.legal_rag.management.commands.reindex_legal_corpus._ChromaIndexer"
    )
    def test_full_rebuild_clears_collection(
        self, mock_indexer_cls: MagicMock
    ) -> None:
        """``--full-rebuild`` invokes ``wipe_collection`` before upsert."""
        _make_active_corpus_with_facts(fact_count=1)
        mock_instance = MagicMock()
        mock_instance.upsert_facts.return_value = (1, 0)
        mock_indexer_cls.return_value = mock_instance

        out = StringIO()
        call_command("reindex_legal_corpus", "--full-rebuild", stdout=out)

        mock_instance.wipe_collection.assert_called_once()

    def test_metadata_includes_citation_confidence(self) -> None:
        """The ChromaDB metadata payload carries the consumer-required fields."""
        fact = IndexedFact(
            concept_id="rha-s7-tribunal-establishment",
            type="statute_provision",
            citation_string="RHA s7",
            plain_english_summary="Establishes Tribunal per province.",
            topic_tags=["tribunal", "enforcement"],
            citation_confidence="high",
            verification_status="mc_reviewed",
            legal_provisional=False,
            content_hash="aabbccddeeff",
            corpus_version="legal-rag-v0.1-deadbeef0000",
        )
        meta = _metadata_for(fact)
        self.assertEqual(meta["citation_confidence"], "high")
        self.assertEqual(meta["verification_status"], "mc_reviewed")
        self.assertEqual(meta["legal_provisional"], False)
        self.assertEqual(meta["corpus_version"], "legal-rag-v0.1-deadbeef0000")
        self.assertEqual(meta["content_hash"], "aabbccddeeff")
        self.assertEqual(meta["topic_tags"], "tribunal,enforcement")
        self.assertEqual(meta["statute"], "RHA")

        text = _embedded_text_for(fact)
        self.assertIn("RHA s7", text)
        self.assertIn("Establishes Tribunal per province.", text)
        self.assertIn("tribunal enforcement", text)
