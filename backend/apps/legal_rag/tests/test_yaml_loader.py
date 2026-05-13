"""Tests for ``apps.legal_rag.yaml_loader``.

Pinning the contract: ISO-shaped strings stay strings, structure passes
through, parse errors propagate. The loader is shared by
``apps.legal_rag.checks`` and ``apps.legal_rag.management.commands.sync_legal_facts``;
a regression here corrupts schema validation across both surfaces.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import yaml
from django.test import SimpleTestCase

from apps.legal_rag.yaml_loader import (
    StringDateLoader,
    load_safe_yaml,
    load_safe_yaml_text,
)


class StringDateLoaderTests(SimpleTestCase):
    """The loader keeps ISO-8601 date strings as strings."""

    def test_iso_date_stays_string(self):
        data = load_safe_yaml_text("effective_from: 2026-05-13")
        self.assertEqual(data["effective_from"], "2026-05-13")
        self.assertIsInstance(data["effective_from"], str)

    def test_iso_datetime_stays_string(self):
        data = load_safe_yaml_text("created_at: '2026-05-13T10:00:00Z'")
        self.assertEqual(data["created_at"], "2026-05-13T10:00:00Z")
        self.assertIsInstance(data["created_at"], str)

    def test_unquoted_iso_datetime_also_stays_string(self):
        """The implicit resolver — not just quoted strings — is bypassed."""
        data = load_safe_yaml_text("created_at: 2026-05-13T10:00:00Z")
        self.assertIsInstance(data["created_at"], str)

    def test_default_safeloader_would_auto_resolve_date(self):
        """Sanity check: PyYAML's default SafeLoader does auto-resolve.

        This test exists so a future "let's just use SafeLoader" refactor
        causes a visible failure here, not a silent schema-validation bug.
        """
        from datetime import date as date_cls
        data = yaml.safe_load("effective_from: 2026-05-13")
        self.assertIsInstance(data["effective_from"], date_cls)

    def test_plain_strings_pass_through(self):
        data = load_safe_yaml_text("title: 'Klikk Lease v1'\ncount: 7")
        self.assertEqual(data, {"title": "Klikk Lease v1", "count": 7})

    def test_nested_structure_handled(self):
        text = (
            "concept_id: rha-s7\n"
            "version: 1\n"
            "applicability:\n"
            "  property_types: [sectional_title, freehold]\n"
            "  effective_from: 2014-08-01\n"
        )
        data = load_safe_yaml_text(text)
        self.assertEqual(data["applicability"]["effective_from"], "2014-08-01")
        self.assertIsInstance(data["applicability"]["effective_from"], str)
        self.assertEqual(
            data["applicability"]["property_types"], ["sectional_title", "freehold"]
        )

    def test_empty_text_returns_none(self):
        self.assertIsNone(load_safe_yaml_text(""))

    def test_parse_error_propagates(self):
        with self.assertRaises(yaml.YAMLError):
            load_safe_yaml_text("invalid: : :")


class LoadSafeYamlPathTests(SimpleTestCase):
    """Path-based loading works the same as text-based."""

    def test_load_from_path(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write("concept_id: rha-test\neffective_from: 2026-01-01\n")
            tmp_path = Path(f.name)
        try:
            data = load_safe_yaml(tmp_path)
            self.assertEqual(data["concept_id"], "rha-test")
            self.assertEqual(data["effective_from"], "2026-01-01")
            self.assertIsInstance(data["effective_from"], str)
        finally:
            tmp_path.unlink()

    def test_empty_file_returns_none(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            tmp_path = Path(f.name)
        try:
            self.assertIsNone(load_safe_yaml(tmp_path))
        finally:
            tmp_path.unlink()


class LoaderClassTests(SimpleTestCase):
    """The exported class has the expected resolver-table state."""

    def test_timestamp_resolver_removed(self):
        for first_char, resolvers in StringDateLoader.yaml_implicit_resolvers.items():
            for tag, _regex in resolvers:
                self.assertNotEqual(
                    tag,
                    "tag:yaml.org,2002:timestamp",
                    f"timestamp resolver present for first_char={first_char!r}",
                )

    def test_other_resolvers_preserved(self):
        """Bool/int/float resolvers still in place — we only stripped timestamp."""
        present = set()
        for resolvers in StringDateLoader.yaml_implicit_resolvers.values():
            for tag, _ in resolvers:
                present.add(tag)
        self.assertIn("tag:yaml.org,2002:bool", present)
        self.assertIn("tag:yaml.org,2002:int", present)
        self.assertIn("tag:yaml.org,2002:float", present)
