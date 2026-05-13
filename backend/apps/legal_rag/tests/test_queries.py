"""Tests for the public read-API in ``apps.legal_rag.queries``.

We seed a temp YAML fixture tree and let ``sync_legal_facts --path``
populate the test database. This is faster than handcrafting ORM rows
because it exercises the same upsert pipeline real callers go through.
"""
from __future__ import annotations

import shutil
import tempfile
import textwrap
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from apps.legal_rag import queries
from apps.legal_rag.exceptions import LegalFactNotFound
from apps.legal_rag.models import LegalCorpusVersion


REPO_ROOT = Path(settings.BASE_DIR).parent
LEGAL_SCHEMA_PATH = REPO_ROOT / "content" / "legal" / "_schema" / "legal_fact.schema.json"


def _fact_yaml(
    *,
    concept_id: str,
    citation: str,
    section: str,
    summary: str = "Summary placeholder.",
    statute: str = "RHA",
    type_: str = "statute_provision",
    citation_confidence: str = "high",
    legal_provisional: bool = False,
    provisional_reason: str | None = None,
    topic_tags: list[str] | None = None,
    verification_status: str = "mc_reviewed",
    effective_from: str = "2014-08-01",
) -> str:
    """Build a schema-conformant YAML body. Optional fields wired below."""
    if topic_tags is None:
        topic_tags = ["test", "tribunal"]
    extras: list[str] = []
    if legal_provisional:
        reason = provisional_reason or "Source disagreement; flag for lawyer."
        extras.append(f"provisional_reason: \"{reason}\"")
    extras_block = "\n".join(extras)

    return textwrap.dedent(
        f"""\
        ---
        concept_id: {concept_id}
        type: {type_}
        version: 1
        effective_from: {effective_from}
        last_verified_at: 2026-05-12
        last_changed_at: 2026-05-12

        statute: {statute}
        statute_full_title: "Rental Housing Act 50 of 1999"
        section: "{section}"
        subsection_letter: null
        parent_section: "{section}"
        citation_string: "{citation}"

        statute_text: "Statute text body."
        statute_text_verbatim: false

        plain_english_summary: |
          {summary}

        citation_confidence: {citation_confidence}
        legal_provisional: {"true" if legal_provisional else "false"}
        {extras_block}

        verification_status: {verification_status}
        attestation_id: null
        attested_by: null
        attested_at: null
        attestation_method: null

        applicability:
          property_types: [apartment]
          tenant_counts: [any]
          lease_types: [fixed_term]
          jurisdictions: [za-national]

        topic_tags: {topic_tags}

        related_concepts:
          - related-fact

        sources:
          - type: statute
            title: "Rental Housing Act 50 of 1999"
            accessed_at: 2026-05-12

        disclaimers:
          - "Not legal advice."
        """
    )


class QueryFixtureMixin:
    """Set up a tiny corpus via the sync command for each query test."""

    fixture_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.fixture_root = Path(tempfile.mkdtemp(prefix="legal_rag_query_test_"))
        (cls.fixture_root / "_schema").mkdir(parents=True)
        (cls.fixture_root / "statutes" / "rha").mkdir(parents=True)
        shutil.copyfile(
            LEGAL_SCHEMA_PATH,
            cls.fixture_root / "_schema" / "legal_fact.schema.json",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.fixture_root, ignore_errors=True)
        super().tearDownClass()

    def _write(self, name: str, body: str) -> None:
        (self.fixture_root / "statutes" / "rha" / name).write_text(body)

    def _sync(self) -> None:
        call_command("sync_legal_facts", "--path", str(self.fixture_root))

    def _seed_default_corpus(self) -> None:
        # Three facts: one high-confidence non-provisional, one
        # low-confidence provisional, one mid-confidence non-provisional.
        # Distinct topic tags so the filter tests can assert precisely.
        self._write(
            "s7.yaml",
            _fact_yaml(
                concept_id="rha-s7-tribunal-establishment",
                citation="RHA s7",
                section="s7",
                summary="Each provincial MEC for housing establishes a Tribunal.",
                topic_tags=["tribunal", "enforcement"],
            ),
        )
        self._write(
            "s5_3_f.yaml",
            _fact_yaml(
                concept_id="rha-s5-3-f-deposit-interest-bearing-account",
                citation="RHA s5(3)(f)",
                section="s5(3)(f)",
                summary="Deposit must be held in an interest-bearing account.",
                citation_confidence="low",
                legal_provisional=True,
                provisional_reason="Sub-section letter disputed by audit.",
                topic_tags=["deposit", "interest"],
            ),
        )
        self._write(
            "s5_3_a.yaml",
            _fact_yaml(
                concept_id="rha-s5-3-a-parties",
                citation="RHA s5(3)(a)",
                section="s5(3)(a)",
                summary="Lease must name parties + addresses.",
                citation_confidence="medium",
                topic_tags=["deposit", "parties"],
            ),
        )
        self._sync()


class TestQueryStatute(QueryFixtureMixin, TestCase):
    """``query_statute`` happy path + miss path."""

    def setUp(self) -> None:
        # Clean any prior test's fixtures + reseed.
        for child in (self.fixture_root / "statutes" / "rha").iterdir():
            child.unlink()
        self._seed_default_corpus()

    def test_returns_dataclass_with_expected_fields(self) -> None:
        fact = queries.query_statute("RHA s7")
        # Stable contract: returns the queries.LegalFact dataclass, not the
        # ORM model. Make this explicit so anyone refactoring sees the test.
        self.assertIsInstance(fact, queries.LegalFact)
        self.assertEqual(fact.concept_id, "rha-s7-tribunal-establishment")
        self.assertEqual(fact.citation_confidence, "high")
        self.assertFalse(fact.legal_provisional)
        self.assertIn("MEC for housing establishes a Tribunal", fact.plain_english_summary)
        self.assertIn("Not legal advice.", fact.disclaimers)

    def test_query_statute_returns_dataclass_not_orm_model(self) -> None:
        """Guard against accidental ORM-leak across the public surface."""
        from apps.legal_rag.models import LegalFact as LegalFactModel

        fact = queries.query_statute("RHA s7")
        self.assertIsInstance(fact, queries.LegalFact)
        self.assertNotIsInstance(fact, LegalFactModel)

    def test_query_statute_case_and_whitespace_insensitive(self) -> None:
        # Mixed-case + extra whitespace should still match.
        fact = queries.query_statute("  rha s7  ")
        self.assertEqual(fact.concept_id, "rha-s7-tribunal-establishment")

    def test_raises_for_unknown_citation(self) -> None:
        with self.assertRaises(LegalFactNotFound):
            queries.query_statute("RHA s99(z)")


class TestQueryConcept(QueryFixtureMixin, TestCase):
    def setUp(self) -> None:
        for child in (self.fixture_root / "statutes" / "rha").iterdir():
            child.unlink()
        self._seed_default_corpus()

    def test_happy_path(self) -> None:
        fact = queries.query_concept("rha-s7-tribunal-establishment")
        self.assertEqual(fact.citation_string, "RHA s7")

    def test_unknown_concept_id_raises(self) -> None:
        with self.assertRaises(LegalFactNotFound):
            queries.query_concept("does-not-exist")


class TestQueryFactsByTopic(QueryFixtureMixin, TestCase):
    def setUp(self) -> None:
        for child in (self.fixture_root / "statutes" / "rha").iterdir():
            child.unlink()
        self._seed_default_corpus()

    def test_query_facts_by_topic_excludes_provisional_by_default(self) -> None:
        # ``deposit`` is shared by the provisional s5(3)(f) (low) and the
        # non-provisional s5(3)(a) (medium). Default behaviour excludes
        # provisional rows, so only s5(3)(a) returns.
        results = queries.query_facts_by_topic(["deposit"])
        ids = [r.concept_id for r in results]
        self.assertIn("rha-s5-3-a-parties", ids)
        self.assertNotIn(
            "rha-s5-3-f-deposit-interest-bearing-account", ids
        )

    def test_query_facts_by_topic_includes_provisional_when_flagged(self) -> None:
        # With ``include_provisional=True`` AND ``min_confidence="low"``
        # the provisional s5(3)(f) row must come back.
        results = queries.query_facts_by_topic(
            ["deposit"], include_provisional=True, min_confidence="low"
        )
        ids = [r.concept_id for r in results]
        self.assertIn("rha-s5-3-f-deposit-interest-bearing-account", ids)
        self.assertIn("rha-s5-3-a-parties", ids)

    def test_query_facts_by_topic_filters_by_statute(self) -> None:
        # Same statute prefix → all match.
        results = queries.query_facts_by_topic(["tribunal"], statute="RHA")
        ids = [r.concept_id for r in results]
        self.assertEqual(ids, ["rha-s7-tribunal-establishment"])

    def test_query_facts_by_topic_invalid_min_confidence_raises(self) -> None:
        with self.assertRaises(ValueError):
            queries.query_facts_by_topic(["tribunal"], min_confidence="bogus")  # type: ignore[arg-type]


class TestQueryCaseLaw(QueryFixtureMixin, TestCase):
    def setUp(self) -> None:
        for child in (self.fixture_root / "statutes" / "rha").iterdir():
            child.unlink()
        self._seed_default_corpus()

    def test_query_case_law_empty_when_no_case_law_seeded(self) -> None:
        """Day 3 seed has no case_law rows — must return [] cleanly."""
        results = queries.query_case_law(topic_tags=["deposit"])
        self.assertEqual(results, [])


class TestListPitfallPatterns(QueryFixtureMixin, TestCase):
    def setUp(self) -> None:
        for child in (self.fixture_root / "statutes" / "rha").iterdir():
            child.unlink()
        self._seed_default_corpus()

    def test_list_pitfall_patterns_empty(self) -> None:
        self.assertEqual(queries.list_pitfall_patterns(), [])


class TestListFactsAtVersion(QueryFixtureMixin, TestCase):
    def setUp(self) -> None:
        for child in (self.fixture_root / "statutes" / "rha").iterdir():
            child.unlink()
        self._seed_default_corpus()

    def test_list_facts_at_version_filters_correctly(self) -> None:
        active = LegalCorpusVersion.objects.filter(is_active=True).first()
        self.assertIsNotNone(active)
        results = queries.list_facts_at_version(active.version)
        ids = sorted(r.concept_id for r in results)
        self.assertEqual(
            ids,
            [
                "rha-s5-3-a-parties",
                "rha-s5-3-f-deposit-interest-bearing-account",
                "rha-s7-tribunal-establishment",
            ],
        )

    def test_list_facts_at_version_unknown_version_returns_empty(self) -> None:
        self.assertEqual(queries.list_facts_at_version("does-not-exist"), [])


class TestQuerySemantic(QueryFixtureMixin, TestCase):
    """``query_semantic`` is exercised in a stub mode here.

    Real semantic retrieval needs the ChromaDB index to exist on-disk,
    which is the indexer's job and is tested separately. This test only
    verifies that an empty or unbuilt index returns ``[]`` cleanly
    (no exceptions leak), matching the plan's "fail-soft on missing
    index" contract.
    """

    def setUp(self) -> None:
        for child in (self.fixture_root / "statutes" / "rha").iterdir():
            child.unlink()
        self._seed_default_corpus()

    def test_query_semantic_empty_query_returns_empty(self) -> None:
        self.assertEqual(queries.query_semantic("   "), [])

    def test_query_semantic_invalid_min_confidence_raises(self) -> None:
        with self.assertRaises(ValueError):
            queries.query_semantic("deposit", min_confidence="bogus")  # type: ignore[arg-type]
