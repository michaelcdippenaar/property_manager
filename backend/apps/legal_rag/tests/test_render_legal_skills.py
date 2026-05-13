"""Tests for ``manage.py render_legal_skills`` + helper module.

Each test seeds a minimal YAML corpus via ``sync_legal_facts --path``,
points the renderer at temp target files (with the BEGIN/END markers
already inserted), and asserts on the rendered output.

The tests target the helper functions in
:mod:`apps.legal_rag.skill_rendering` directly where possible — this
keeps the surface area under test small and lets us drive Jinja2 helper
behaviour without booting the Django management-command machinery.
"""
from __future__ import annotations

import io
import shutil
import tempfile
import textwrap
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.legal_rag.exceptions import LegalFactNotFound
from apps.legal_rag.skill_rendering import (
    BEGIN_MARKER,
    END_MARKER,
    build_environment,
    render_target,
)

REPO_ROOT = Path(settings.BASE_DIR).parent
LEGAL_SCHEMA_PATH = (
    REPO_ROOT / "content" / "legal" / "_schema" / "legal_fact.schema.json"
)


# ── Fixture helpers ──────────────────────────────────────────────────── #


def _fact_yaml(
    *,
    concept_id: str,
    citation: str,
    section: str,
    summary: str,
    citation_confidence: str = "high",
    legal_provisional: bool = False,
    provisional_reason: str | None = None,
    topic_tags: list[str] | None = None,
    verification_status: str = "mc_reviewed",
    effective_from: str = "2014-08-01",
) -> str:
    """Build a schema-conformant YAML body for fixtures."""
    if topic_tags is None:
        topic_tags = ["test"]
    extras: list[str] = []
    if legal_provisional:
        reason = provisional_reason or "Source disagreement; lawyer review pending."
        extras.append(f'provisional_reason: "{reason}"')
    extras_block = "\n".join(extras)

    return textwrap.dedent(
        f"""\
        ---
        concept_id: {concept_id}
        type: statute_provision
        version: 1
        effective_from: {effective_from}
        last_verified_at: 2026-05-12
        last_changed_at: 2026-05-12

        statute: RHA
        statute_full_title: "Rental Housing Act 50 of 1999"
        section: "{section}"
        subsection_letter: null
        parent_section: "{section}"
        citation_string: "{citation}"

        statute_text: "Statute body."
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

        sources:
          - type: statute
            title: "Rental Housing Act 50 of 1999"
            accessed_at: 2026-05-12

        disclaimers:
          - "Not legal advice."
        """
    )


def _required_facts_for_06() -> list[tuple[str, str]]:
    """Concept ids + YAML body for the s06 template's required facts."""
    return [
        (
            "rha-s5-2-right-to-written-lease",
            _fact_yaml(
                concept_id="rha-s5-2-right-to-written-lease",
                citation="RHA s5(2)",
                section="s5(2)",
                summary="Tenant has right to a written lease on request.",
                topic_tags=["written_lease", "tenant_right"],
            ),
        ),
        (
            "rha-s5-3-a-parties",
            _fact_yaml(
                concept_id="rha-s5-3-a-parties",
                citation="RHA s5(3)(a)",
                section="s5(3)(a)",
                summary="Lease must name parties + addresses for service.",
                topic_tags=["mandatory_clause", "parties"],
            ),
        ),
        (
            "rha-s5-3-b-dwelling",
            _fact_yaml(
                concept_id="rha-s5-3-b-dwelling",
                citation="RHA s5(3)(b)",
                section="s5(3)(b)",
                summary="Lease must describe the dwelling.",
                citation_confidence="low",
                legal_provisional=True,
                provisional_reason="Description ambit pending lawyer review.",
                topic_tags=["mandatory_clause", "dwelling"],
            ),
        ),
        (
            "rha-s5-a-landlord-duties",
            _fact_yaml(
                concept_id="rha-s5-a-landlord-duties",
                citation="RHA s5A",
                section="s5A",
                summary="Landlord must keep dwelling habitable + give receipts.",
                topic_tags=["landlord_duty"],
            ),
        ),
        (
            "rha-s5-b-tenant-duties",
            _fact_yaml(
                concept_id="rha-s5-b-tenant-duties",
                citation="RHA s5B",
                section="s5B",
                summary="Tenant must pay rent + avoid damage + obey house rules.",
                topic_tags=["tenant_duty"],
            ),
        ),
        (
            "rha-s7-tribunal-establishment",
            _fact_yaml(
                concept_id="rha-s7-tribunal-establishment",
                citation="RHA s7",
                section="s7",
                summary="Each provincial MEC establishes a Rental Housing Tribunal.",
                topic_tags=["tribunal", "enforcement"],
            ),
        ),
    ]


def _required_facts_for_07() -> list[tuple[str, str]]:
    """Facts the 07 template needs in addition to 06's set."""
    return [
        (
            "rha-s4-a-unfair-practices",
            _fact_yaml(
                concept_id="rha-s4-a-unfair-practices",
                citation="RHA s4A",
                section="s4A",
                summary="Minister may prescribe unfair practices; Tribunal hears complaints.",
                topic_tags=["unfair_practices", "tribunal"],
            ),
        ),
        (
            "rha-s13-tribunal-powers",
            _fact_yaml(
                concept_id="rha-s13-tribunal-powers",
                citation="RHA s13",
                section="s13",
                summary="Tribunal rulings have effect of Magistrate's Court order.",
                topic_tags=["tribunal", "enforcement"],
            ),
        ),
    ]


# ── Common base ──────────────────────────────────────────────────────── #


class _RendererFixtureMixin:
    """Set up a tiny YAML corpus + temp target files for renderer tests."""

    fixture_root: Path
    target_dir: Path

    def setUp(self) -> None:
        # Each test gets isolated dirs so YAML / target / template state does not leak.
        self.fixture_root = Path(tempfile.mkdtemp(prefix="render_skills_yaml_"))
        self.target_dir = Path(tempfile.mkdtemp(prefix="render_skills_targets_"))
        (self.fixture_root / "_schema").mkdir(parents=True)
        (self.fixture_root / "statutes" / "rha").mkdir(parents=True)
        shutil.copyfile(
            LEGAL_SCHEMA_PATH,
            self.fixture_root / "_schema" / "legal_fact.schema.json",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.fixture_root, ignore_errors=True)
        shutil.rmtree(self.target_dir, ignore_errors=True)

    # ── helpers ─────────────────────────────────────────────────── #

    def _write_yaml(self, name: str, body: str) -> None:
        (self.fixture_root / "statutes" / "rha" / name).write_text(
            body, encoding="utf-8"
        )

    def _seed_corpus_for_06(self) -> None:
        for cid, body in _required_facts_for_06():
            self._write_yaml(f"{cid}.yaml", body)
        call_command("sync_legal_facts", "--path", str(self.fixture_root))

    def _seed_corpus_for_06_and_07(self) -> None:
        for cid, body in _required_facts_for_06():
            self._write_yaml(f"{cid}.yaml", body)
        for cid, body in _required_facts_for_07():
            self._write_yaml(f"{cid}.yaml", body)
        call_command("sync_legal_facts", "--path", str(self.fixture_root))

    def _make_target_at(self, rel_path: str) -> Path:
        """Write a minimal .md target with markers + outside-marker prose."""
        target = self.target_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "# RHA — header preserved\n\n"
            "Some intro prose that must survive the render.\n\n"
            f"{BEGIN_MARKER}\n"
            "<!-- placeholder -->\n"
            f"{END_MARKER}\n\n"
            "## Footer that must survive\n",
            encoding="utf-8",
        )
        return target


# ── Direct helper tests (no command runner) ──────────────────────────── #


class TestRenderHelpers(_RendererFixtureMixin, TestCase):
    """Drive ``skill_rendering.render_target`` directly."""

    def test_render_06_rha_core_includes_s5_2_summary(self) -> None:
        """The 06 template must emit the s5(2) plain_english_summary."""
        self._seed_corpus_for_06()
        env = build_environment()
        result = render_target(
            "klikk-legal-POPIA-RHA/06-rha-core-and-s5.md.j2",
            corpus_version="test-corpus-v1",
            env=env,
        )
        self.assertIn(
            "Tenant has right to a written lease on request",
            result.rendered_section,
        )
        # Footer carries the corpus_version stamp.
        self.assertIn("test-corpus-v1", result.rendered_section)
        # Every required concept_id was touched.
        for cid, _ in _required_facts_for_06():
            self.assertIn(
                cid, result.facts_used,
                f"Expected template to reference {cid}",
            )

    def test_render_marks_low_confidence_facts_provisional(self) -> None:
        """LOW-confidence facts must be flagged with the provisional admonition.

        Our 06 fixture sets ``rha-s5-3-b-dwelling`` LOW + provisional. The
        rendered section should surface the ``provisional_reason``.
        """
        self._seed_corpus_for_06()
        env = build_environment()
        result = render_target(
            "klikk-legal-POPIA-RHA/06-rha-core-and-s5.md.j2",
            corpus_version="test-corpus-v1",
            env=env,
        )
        self.assertIn(
            "Description ambit pending lawyer review",
            result.rendered_section,
        )
        # The provisional row in the s5(3) table is marked too.
        self.assertIn("(provisional)", result.rendered_section)

    def test_render_idempotent(self) -> None:
        """Two consecutive renders against the same corpus produce equal output.

        We strip the dynamic ``generated <iso-now>Z`` line before comparing
        — the rest of the body is purely a function of the YAML.
        """
        self._seed_corpus_for_06()
        env = build_environment()
        r1 = render_target(
            "klikk-legal-POPIA-RHA/06-rha-core-and-s5.md.j2",
            corpus_version="test-corpus-v1",
            env=env,
        )
        r2 = render_target(
            "klikk-legal-POPIA-RHA/06-rha-core-and-s5.md.j2",
            corpus_version="test-corpus-v1",
            env=env,
        )
        def _strip_now(text: str) -> str:
            return "\n".join(
                line for line in text.splitlines() if "generated " not in line
            )
        self.assertEqual(_strip_now(r1.rendered_section), _strip_now(r2.rendered_section))

    def test_render_includes_corpus_version_in_footer(self) -> None:
        """``corpus_version`` appears in the rendered footer line."""
        self._seed_corpus_for_06()
        env = build_environment()
        result = render_target(
            "klikk-legal-POPIA-RHA/06-rha-core-and-s5.md.j2",
            corpus_version="legal-rag-v0.1-abc123",
            env=env,
        )
        self.assertIn("legal-rag-v0.1-abc123", result.rendered_section)
        self.assertIn("corpus_version", result.rendered_section)

    def test_unknown_concept_id_raises_clearly(self) -> None:
        """Calling ``fact()`` with an unknown id raises ``LegalFactNotFound``.

        The renderer must fail loudly rather than silently writing a
        rendered file with stale or empty citations.
        """
        # Seed an empty corpus (no facts) — every fact() call will miss.
        call_command("sync_legal_facts", "--path", str(self.fixture_root))
        env = build_environment()
        with self.assertRaises(LegalFactNotFound):
            render_target(
                "klikk-legal-POPIA-RHA/06-rha-core-and-s5.md.j2",
                corpus_version="test-corpus-v1",
                env=env,
            )


# ── Command-runner tests ─────────────────────────────────────────────── #


class TestRenderCommand(_RendererFixtureMixin, TestCase):
    """Drive the management command end-to-end via ``call_command``.

    Uses ``LEGAL_RAG_RENDER_REPO_ROOT`` to point the command at a temp
    repo root, and patches ``DEFAULT_TARGETS`` so the command renders our
    minimal stub ``.md`` files rather than the real skill references.
    """

    def setUp(self) -> None:
        super().setUp()
        self._seed_corpus_for_06_and_07()

        # Two stub targets, both under self.target_dir (which we hand to
        # the command as its repo_root). The DEFAULT_TARGETS keys are
        # relative paths from that root.
        rel_06 = "stubs/06-rha-core-and-s5.md"
        rel_07 = "stubs/07-rha-s4a-unfair-practices.md"
        self.target_06 = self._make_target_at(rel_06)
        self.target_07 = self._make_target_at(rel_07)

        from apps.legal_rag.management.commands import render_legal_skills

        self._render_module = render_legal_skills
        self._original_targets = dict(render_legal_skills.DEFAULT_TARGETS)
        render_legal_skills.DEFAULT_TARGETS.clear()
        render_legal_skills.DEFAULT_TARGETS.update({
            rel_06: "klikk-legal-POPIA-RHA/06-rha-core-and-s5.md.j2",
            rel_07: "klikk-legal-POPIA-RHA/07-rha-s4a-unfair-practices.md.j2",
        })

    def tearDown(self) -> None:
        self._render_module.DEFAULT_TARGETS.clear()
        self._render_module.DEFAULT_TARGETS.update(self._original_targets)
        super().tearDown()

    def _run(self, *extra_args: str) -> tuple[int, str, str]:
        """Run the command via ``call_command``, capturing IO + exit code."""
        out = io.StringIO()
        err = io.StringIO()
        exit_code = 0
        with override_settings(
            LEGAL_RAG_RENDER_REPO_ROOT=str(self.target_dir)
        ):
            with redirect_stdout(out), redirect_stderr(err):
                try:
                    call_command(
                        "render_legal_skills",
                        *extra_args,
                        stdout=out,
                        stderr=err,
                    )
                except SystemExit as exc:
                    code = exc.code
                    exit_code = int(code) if code is not None else 0
        return exit_code, out.getvalue(), err.getvalue()

    def test_check_mode_exits_zero_when_drift_zero(self) -> None:
        """After a successful --write, --check returns 0 with clean output."""
        code, _out, _err = self._run("--write")
        self.assertEqual(code, 0)
        # Second run in check mode should be clean.
        code2, out2, _err2 = self._run("--check")
        self.assertEqual(code2, 0)
        self.assertIn("clean", out2)

    def test_check_mode_exits_one_when_drift_detected(self) -> None:
        """Stale on-disk content vs YAML → check mode exits 1 + emits diff."""
        code, _out, err = self._run("--check")
        self.assertEqual(code, 1)
        # Expect a unified-diff hunk or DRIFT marker on stderr.
        self.assertTrue(
            "DRIFT" in err or "@@" in err,
            f"Expected unified diff or DRIFT marker on stderr; got: {err!r}",
        )


__all__ = [
    "TestRenderHelpers",
    "TestRenderCommand",
]
