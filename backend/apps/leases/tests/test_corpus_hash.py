"""Tests for ``apps.leases.training.corpus_hash``.

Locks the B.3 contract: a real corpus fingerprint is computed when both
indexers have run, otherwise ``compute_combined_corpus_hash`` returns
``None`` so the harness can fall back to its Day-1-2 stub. The
combined hash is deterministic, order-stable, and shape-stable across
the two indexers' slightly-different JSON key names.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.leases.training.corpus_hash import (
    IndexedCorpus,
    compute_combined_corpus_hash,
    describe_corpus_state,
)


def _write_index_file(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class ComputeCombinedCorpusHashTests(SimpleTestCase):
    """``compute_combined_corpus_hash()`` returns a deterministic, prefixed
    fingerprint when both indexers have run, ``None`` otherwise."""

    def test_returns_none_when_no_index_files_exist(self):
        with override_settings(
            LEASE_AI_CHROMA_PATH="/tmp/nonexistent-lease-ai-chroma-aaaa",
            LEGAL_RAG_CHROMA_PATH="/tmp/nonexistent-legal-rag-chroma-aaaa",
        ):
            self.assertIsNone(compute_combined_corpus_hash())

    def test_returns_none_when_only_one_side_indexed(self):
        with self.settings(
            LEASE_AI_CHROMA_PATH="/tmp/klikk-corpus-test-only-lease",
            LEGAL_RAG_CHROMA_PATH="/tmp/klikk-corpus-test-missing-legal",
        ):
            _write_index_file(
                Path("/tmp/klikk-corpus-test-only-lease/.last_index.json"),
                {"corpus_hash": "abc123", "chunk_count": 5},
            )
            try:
                self.assertIsNone(compute_combined_corpus_hash())
            finally:
                Path("/tmp/klikk-corpus-test-only-lease/.last_index.json").unlink(
                    missing_ok=True
                )

    def test_returns_prefixed_hash_when_both_sides_indexed(self):
        with self.settings(
            LEASE_AI_CHROMA_PATH="/tmp/klikk-corpus-test-both-lease",
            LEGAL_RAG_CHROMA_PATH="/tmp/klikk-corpus-test-both-legal",
        ):
            _write_index_file(
                Path("/tmp/klikk-corpus-test-both-lease/.last_index.json"),
                {"corpus_hash": "lease-abc123", "chunk_count": 3},
            )
            _write_index_file(
                Path("/tmp/klikk-corpus-test-both-legal/.last_index.json"),
                {"corpus_hash": "legal-xyz789", "fact_count": 10},
            )
            try:
                result = compute_combined_corpus_hash()
                self.assertIsNotNone(result)
                self.assertTrue(result.startswith("klikk-corpus-"))
                # 12-hex suffix → 25-char total
                self.assertEqual(len(result), len("klikk-corpus-") + 12)
            finally:
                Path("/tmp/klikk-corpus-test-both-lease/.last_index.json").unlink(
                    missing_ok=True
                )
                Path("/tmp/klikk-corpus-test-both-legal/.last_index.json").unlink(
                    missing_ok=True
                )

    def test_deterministic_across_calls(self):
        with self.settings(
            LEASE_AI_CHROMA_PATH="/tmp/klikk-corpus-test-det-lease",
            LEGAL_RAG_CHROMA_PATH="/tmp/klikk-corpus-test-det-legal",
        ):
            _write_index_file(
                Path("/tmp/klikk-corpus-test-det-lease/.last_index.json"),
                {"corpus_hash": "alpha", "chunk_count": 1},
            )
            _write_index_file(
                Path("/tmp/klikk-corpus-test-det-legal/.last_index.json"),
                {"corpus_hash": "beta", "fact_count": 1},
            )
            try:
                first = compute_combined_corpus_hash()
                second = compute_combined_corpus_hash()
                self.assertEqual(first, second)
            finally:
                Path("/tmp/klikk-corpus-test-det-lease/.last_index.json").unlink(
                    missing_ok=True
                )
                Path("/tmp/klikk-corpus-test-det-legal/.last_index.json").unlink(
                    missing_ok=True
                )

    def test_different_inputs_produce_different_hashes(self):
        """Hash must change when EITHER side's corpus_hash changes."""
        with self.settings(
            LEASE_AI_CHROMA_PATH="/tmp/klikk-corpus-test-diff-lease",
            LEGAL_RAG_CHROMA_PATH="/tmp/klikk-corpus-test-diff-legal",
        ):
            _write_index_file(
                Path("/tmp/klikk-corpus-test-diff-lease/.last_index.json"),
                {"corpus_hash": "v1", "chunk_count": 1},
            )
            _write_index_file(
                Path("/tmp/klikk-corpus-test-diff-legal/.last_index.json"),
                {"corpus_hash": "stable", "fact_count": 1},
            )
            try:
                hash_v1 = compute_combined_corpus_hash()
                _write_index_file(
                    Path("/tmp/klikk-corpus-test-diff-lease/.last_index.json"),
                    {"corpus_hash": "v2", "chunk_count": 1},
                )
                hash_v2 = compute_combined_corpus_hash()
                self.assertNotEqual(hash_v1, hash_v2)
            finally:
                Path("/tmp/klikk-corpus-test-diff-lease/.last_index.json").unlink(
                    missing_ok=True
                )
                Path("/tmp/klikk-corpus-test-diff-legal/.last_index.json").unlink(
                    missing_ok=True
                )

    def test_tolerates_alternative_hash_key_names(self):
        """Legal RAG indexer writes ``merkle_root``; lease-AI writes
        ``corpus_hash``. Helper accepts either."""
        with self.settings(
            LEASE_AI_CHROMA_PATH="/tmp/klikk-corpus-test-alt-lease",
            LEGAL_RAG_CHROMA_PATH="/tmp/klikk-corpus-test-alt-legal",
        ):
            _write_index_file(
                Path("/tmp/klikk-corpus-test-alt-lease/.last_index.json"),
                {"corpus_hash": "lease-x"},  # canonical key
            )
            _write_index_file(
                Path("/tmp/klikk-corpus-test-alt-legal/.last_index.json"),
                {"merkle_root": "legal-y"},  # alternative key
            )
            try:
                self.assertIsNotNone(compute_combined_corpus_hash())
            finally:
                Path("/tmp/klikk-corpus-test-alt-lease/.last_index.json").unlink(
                    missing_ok=True
                )
                Path("/tmp/klikk-corpus-test-alt-legal/.last_index.json").unlink(
                    missing_ok=True
                )

    def test_corrupt_json_treated_as_missing(self):
        with self.settings(
            LEASE_AI_CHROMA_PATH="/tmp/klikk-corpus-test-corrupt-lease",
            LEGAL_RAG_CHROMA_PATH="/tmp/klikk-corpus-test-corrupt-legal",
        ):
            Path("/tmp/klikk-corpus-test-corrupt-lease").mkdir(
                parents=True, exist_ok=True
            )
            Path("/tmp/klikk-corpus-test-corrupt-lease/.last_index.json").write_text(
                "{not valid json", encoding="utf-8"
            )
            _write_index_file(
                Path("/tmp/klikk-corpus-test-corrupt-legal/.last_index.json"),
                {"corpus_hash": "valid"},
            )
            try:
                # Corrupt JSON on one side → fall through to None
                self.assertIsNone(compute_combined_corpus_hash())
            finally:
                Path("/tmp/klikk-corpus-test-corrupt-lease/.last_index.json").unlink(
                    missing_ok=True
                )
                Path("/tmp/klikk-corpus-test-corrupt-legal/.last_index.json").unlink(
                    missing_ok=True
                )


class DescribeCorpusStateTests(SimpleTestCase):
    """Diagnostic accessor returns IndexedCorpus instances or None per side."""

    def test_describe_returns_dict_with_both_keys(self):
        with override_settings(
            LEASE_AI_CHROMA_PATH="/tmp/klikk-corpus-describe-missing-x",
            LEGAL_RAG_CHROMA_PATH="/tmp/klikk-corpus-describe-missing-y",
        ):
            state = describe_corpus_state()
            self.assertEqual(set(state.keys()), {"lease_law", "legal_rag"})
            self.assertIsNone(state["lease_law"])
            self.assertIsNone(state["legal_rag"])

    def test_describe_parses_fact_count_and_indexed_at(self):
        with self.settings(
            LEASE_AI_CHROMA_PATH="/tmp/klikk-corpus-describe-lease",
            LEGAL_RAG_CHROMA_PATH="/tmp/klikk-corpus-describe-legal",
        ):
            _write_index_file(
                Path("/tmp/klikk-corpus-describe-lease/.last_index.json"),
                {
                    "corpus_hash": "abc",
                    "chunk_count": 3,
                    "indexed_at": "2026-05-13T12:00:00Z",
                },
            )
            _write_index_file(
                Path("/tmp/klikk-corpus-describe-legal/.last_index.json"),
                {
                    "corpus_hash": "xyz",
                    "fact_count": 10,
                    "run_at": "2026-05-13T12:05:00Z",
                },
            )
            try:
                state = describe_corpus_state()
                self.assertIsInstance(state["lease_law"], IndexedCorpus)
                self.assertIsInstance(state["legal_rag"], IndexedCorpus)
                self.assertEqual(state["lease_law"].fact_count, 3)
                self.assertEqual(state["legal_rag"].fact_count, 10)
                self.assertEqual(
                    state["lease_law"].indexed_at, "2026-05-13T12:00:00Z"
                )
            finally:
                Path("/tmp/klikk-corpus-describe-lease/.last_index.json").unlink(
                    missing_ok=True
                )
                Path("/tmp/klikk-corpus-describe-legal/.last_index.json").unlink(
                    missing_ok=True
                )


class HarnessIntegrationTests(SimpleTestCase):
    """Harness consumes ``compute_combined_corpus_hash`` correctly."""

    def test_harness_uses_combined_hash_when_available(self):
        """When both indexers have run, the harness picks up the
        combined hash automatically — no explicit ``corpus_hash`` kwarg
        required. This is what Phase 2 of the architecture relies on."""
        from apps.leases.training.harness import LeaseTrainingHarness

        with patch(
            "apps.leases.training.harness.compute_combined_corpus_hash",
            return_value="klikk-corpus-deadbeef1234",
        ):
            # Pass a non-existent path; we only care about init-time
            # corpus_hash resolution, not execution.
            harness = LeaseTrainingHarness("/tmp/does-not-exist.yaml")
            self.assertEqual(harness.corpus_hash, "klikk-corpus-deadbeef1234")

    def test_harness_falls_back_to_stub_when_no_indexer_run(self):
        from apps.leases.training.cassette import DAY_1_2_CORPUS_HASH
        from apps.leases.training.harness import LeaseTrainingHarness

        with patch(
            "apps.leases.training.harness.compute_combined_corpus_hash",
            return_value=None,
        ):
            harness = LeaseTrainingHarness("/tmp/does-not-exist.yaml")
            self.assertEqual(harness.corpus_hash, DAY_1_2_CORPUS_HASH)

    def test_explicit_kwarg_wins_over_auto_compute(self):
        from apps.leases.training.harness import LeaseTrainingHarness

        with patch(
            "apps.leases.training.harness.compute_combined_corpus_hash",
            return_value="klikk-corpus-auto-aaaa",
        ):
            harness = LeaseTrainingHarness(
                "/tmp/does-not-exist.yaml",
                corpus_hash="explicit-from-test",
            )
            self.assertEqual(harness.corpus_hash, "explicit-from-test")
