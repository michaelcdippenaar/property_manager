"""Tests for ``manage.py sync_legal_facts``.

Each test writes a tiny YAML fixture tree to a temp dir and invokes the
command with ``--path``. This keeps DB writes scoped, makes content-hash
changes simple to drive (one line edit), and avoids coupling tests to
the committed seed corpus.
"""
from __future__ import annotations

import json
import shutil
import textwrap
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from apps.legal_rag.models import (
    LegalCorpusVersion,
    LegalFact,
    LegalFactVersion,
)


REPO_ROOT = Path(settings.BASE_DIR).parent
LEGAL_SCHEMA_PATH = REPO_ROOT / "content" / "legal" / "_schema" / "legal_fact.schema.json"


def _minimal_fact_yaml(
    *,
    concept_id: str = "rha-s7-tribunal-establishment",
    summary: str = "Each provincial MEC for housing establishes a Tribunal.",
    effective_from: str = "2014-08-01",
    last_changed_at: str = "2026-05-12",
    statute: str = "RHA",
    citation: str = "RHA s7",
    section: str = "s7",
) -> str:
    """Build a schema-conformant fact YAML body for fixtures.

    Kept deliberately small — every test case needs one valid baseline
    and may then perturb a single field.
    """
    return textwrap.dedent(
        f"""\
        ---
        concept_id: {concept_id}
        type: statute_provision
        version: 1
        effective_from: {effective_from}
        last_verified_at: 2026-05-12
        last_changed_at: {last_changed_at}

        statute: {statute}
        statute_full_title: "Rental Housing Act 50 of 1999"
        section: "{section}"
        subsection_letter: null
        parent_section: "{section}"
        citation_string: "{citation}"

        statute_text: "Test statute body."
        statute_text_verbatim: false

        plain_english_summary: |
          {summary}

        citation_confidence: high
        legal_provisional: false

        verification_status: mc_reviewed
        attestation_id: null
        attested_by: null
        attested_at: null
        attestation_method: null

        applicability:
          property_types: [apartment]
          tenant_counts: [any]
          lease_types: [fixed_term]
          jurisdictions: [za-national]

        topic_tags: [tribunal, enforcement]

        sources:
          - type: statute
            title: "Rental Housing Act 50 of 1999"
            accessed_at: 2026-05-12

        disclaimers:
          - "Not legal advice."
        """
    )


class TestSyncLegalFacts(TestCase):
    """Cover the idempotency, schema-fail, and corpus-version contract."""

    def setUp(self) -> None:
        # Each test gets its own fixture tree so they don't bleed state
        # via the on-disk YAML store.
        self.fixture_root = Path(self._make_tmp_dir())
        self.statutes_dir = self.fixture_root / "statutes" / "rha"
        self.statutes_dir.mkdir(parents=True)
        (self.fixture_root / "_schema").mkdir(parents=True)
        shutil.copyfile(
            LEGAL_SCHEMA_PATH,
            self.fixture_root / "_schema" / "legal_fact.schema.json",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.fixture_root, ignore_errors=True)

    # ── helpers ─────────────────────────────────────────────────── #

    def _make_tmp_dir(self) -> str:
        import tempfile

        return tempfile.mkdtemp(prefix="legal_rag_sync_test_")

    def _write_fact(self, name: str, body: str) -> Path:
        path = self.statutes_dir / name
        path.write_text(body, encoding="utf-8")
        return path

    def _call_sync(self, *extra_args: str) -> None:
        call_command(
            "sync_legal_facts",
            "--path",
            str(self.fixture_root),
            *extra_args,
        )

    # ── tests ───────────────────────────────────────────────────── #

    def test_first_run_creates_all_facts_and_one_corpus_version(self) -> None:
        """Two YAMLs → 2 facts, 2 versions, 1 active corpus_version."""
        self._write_fact(
            "s7.yaml",
            _minimal_fact_yaml(
                concept_id="rha-s7-tribunal-establishment",
                citation="RHA s7",
                section="s7",
            ),
        )
        self._write_fact(
            "s13.yaml",
            _minimal_fact_yaml(
                concept_id="rha-s13-tribunal-powers",
                summary="Tribunal exercises powers under s13.",
                citation="RHA s13",
                section="s13",
            ),
        )

        self._call_sync()

        self.assertEqual(LegalFact.objects.count(), 2)
        self.assertEqual(LegalFactVersion.objects.count(), 2)

        active = LegalCorpusVersion.objects.filter(is_active=True).first()
        self.assertIsNotNone(active)
        self.assertEqual(active.fact_count, 2)
        self.assertEqual(active.embedding_model, "text-embedding-3-small")
        for fact in LegalFact.objects.all():
            self.assertEqual(fact.corpus_version_id, active.id)
            self.assertIsNotNone(fact.current_version_id)
            self.assertEqual(fact.fact_version, 1)

    def test_re_run_is_idempotent_no_changes(self) -> None:
        """Running twice with the same YAMLs does not bump versions."""
        self._write_fact(
            "s7.yaml",
            _minimal_fact_yaml(concept_id="rha-s7-tribunal-establishment"),
        )

        self._call_sync()
        before_versions = LegalFactVersion.objects.count()

        # Run again with no changes — should be a no-op.
        self._call_sync()
        after_versions = LegalFactVersion.objects.count()
        self.assertEqual(before_versions, after_versions)
        self.assertEqual(LegalFact.objects.count(), 1)

        fact = LegalFact.objects.get(concept_id="rha-s7-tribunal-establishment")
        self.assertEqual(fact.fact_version, 1)

    def test_content_hash_change_creates_new_version(self) -> None:
        """Editing the summary bumps the fact and writes a v2 version row."""
        self._write_fact(
            "s7.yaml",
            _minimal_fact_yaml(
                concept_id="rha-s7-tribunal-establishment",
                summary="Initial summary.",
            ),
        )
        self._call_sync()

        # Edit the summary — content_hash changes; effective_from unchanged.
        self._write_fact(
            "s7.yaml",
            _minimal_fact_yaml(
                concept_id="rha-s7-tribunal-establishment",
                summary="Edited summary covering more detail.",
            ),
        )
        self._call_sync()

        fact = LegalFact.objects.get(concept_id="rha-s7-tribunal-establishment")
        self.assertEqual(fact.fact_version, 2)
        versions = list(fact.versions.order_by("version"))
        self.assertEqual([v.version for v in versions], [1, 2])
        self.assertEqual(fact.current_version_id, versions[-1].id)
        # The old version is still there for replay.
        self.assertIn("Initial summary", json.dumps(versions[0].content))

    def test_effective_from_change_creates_new_fact_row(self) -> None:
        """A new ``effective_from`` spawns a NEW LegalFact row.

        Effective-from is a law-version axis: a renumbering or amendment
        with a different commencement date is logically a different row.
        Same ``concept_id`` would collide on the unique constraint, so the
        test uses a fresh concept_id per effective date — mirrors the
        intended migration pattern in real life (deprecate old slug,
        introduce dated successor).
        """
        self._write_fact(
            "s7-2014.yaml",
            _minimal_fact_yaml(
                concept_id="rha-s7-tribunal-establishment-2014",
                effective_from="2014-08-01",
            ),
        )
        self._call_sync()

        self._write_fact(
            "s7-2026.yaml",
            _minimal_fact_yaml(
                concept_id="rha-s7-tribunal-establishment-2026",
                effective_from="2026-01-01",
            ),
        )
        self._call_sync()

        self.assertEqual(LegalFact.objects.count(), 2)
        rows = list(
            LegalFact.objects.order_by("concept_id").values_list(
                "concept_id", "fact_version"
            )
        )
        self.assertEqual(
            rows,
            [
                ("rha-s7-tribunal-establishment-2014", 1),
                ("rha-s7-tribunal-establishment-2026", 1),
            ],
        )

    def test_invalid_yaml_logs_and_skips(self) -> None:
        """Bad files are skipped; good files in the same run still sync."""
        # Bad — missing required fields.
        bad_body = textwrap.dedent(
            """\
            ---
            concept_id: bad-fact
            type: statute_provision
            """
        )
        self._write_fact("bad.yaml", bad_body)
        # Good.
        self._write_fact(
            "good.yaml",
            _minimal_fact_yaml(concept_id="rha-s7-tribunal-establishment"),
        )

        # Capture the loggers so we can assert CRITICAL emission.
        with self.assertLogs(
            "apps.legal_rag.management.commands.sync_legal_facts",
            level="CRITICAL",
        ) as cm:
            self._call_sync()

        # Good file should have synced; bad file should have been skipped.
        self.assertEqual(LegalFact.objects.count(), 1)
        self.assertTrue(
            any("bad.yaml" in line for line in cm.output),
            f"Expected CRITICAL log to mention bad.yaml; got: {cm.output}",
        )

    def test_corpus_version_merkle_is_deterministic(self) -> None:
        """Same set of YAMLs → same corpus_version + merkle_root across runs."""
        self._write_fact(
            "s7.yaml",
            _minimal_fact_yaml(concept_id="rha-s7-tribunal-establishment"),
        )
        self._write_fact(
            "s13.yaml",
            _minimal_fact_yaml(
                concept_id="rha-s13-tribunal-powers",
                citation="RHA s13",
                section="s13",
            ),
        )
        self._call_sync()
        first = LegalCorpusVersion.objects.get(is_active=True)
        first_version_string = first.version
        first_merkle = first.merkle_root

        # Run the command again — should land on the same version + merkle.
        self._call_sync()
        again = LegalCorpusVersion.objects.get(is_active=True)
        self.assertEqual(again.version, first_version_string)
        self.assertEqual(again.merkle_root, first_merkle)
