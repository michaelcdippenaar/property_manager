"""Unit tests for tenant AI JSON parsing and training fixture (no API calls)."""
import pytest
import json

from django.test import SimpleTestCase

from apps.ai.parsing import (
    parse_maintenance_draft_response,
    parse_tenant_ai_response,
    strip_json_fence,
)
from apps.ai.training_validate import load_training_cases, validate_all_cases

pytestmark = [pytest.mark.integration, pytest.mark.green]


class StripJsonFenceTests(SimpleTestCase):
    def test_plain_json_unchanged(self):
        s = '{"a": 1}'
        self.assertEqual(strip_json_fence(s), s)

    def test_strips_fence(self):
        s = "```json\n{\"x\": 1}\n```"
        self.assertEqual(strip_json_fence(s), '{"x": 1}')


class ParseTenantAiResponseTests(SimpleTestCase):
    def test_valid_json(self):
        raw = (
            '{"reply": "Hello", "conversation_title": "Test", '
            '"maintenance_ticket": {"title": "Leak", "description": "Tap", "priority": "medium"}}'
        )
        reply, mt, ok, title = parse_tenant_ai_response(raw)
        self.assertTrue(ok)
        self.assertEqual(reply, "Hello")
        self.assertEqual(title, "Test")
        self.assertIsNotNone(mt)
        self.assertEqual(mt.get("title"), "Leak")

    def test_markdown_fence(self):
        raw = '```\n{"reply": "Hi", "maintenance_ticket": null, "conversation_title": null}\n```'
        reply, mt, ok, title = parse_tenant_ai_response(raw)
        self.assertTrue(ok)
        self.assertEqual(reply, "Hi")
        self.assertIsNone(mt)
        self.assertIsNone(title)

    def test_invalid_json_returns_raw_reply_path(self):
        raw = "not json at all"
        reply, mt, ok, title = parse_tenant_ai_response(raw)
        self.assertFalse(ok)
        self.assertEqual(reply, raw)
        self.assertIsNone(mt)
        self.assertIsNone(title)

    def test_non_object_maintenance_ticket_dropped(self):
        raw = '{"reply": "x", "maintenance_ticket": "oops", "conversation_title": null}'
        _, mt, ok, _ = parse_tenant_ai_response(raw)
        self.assertTrue(ok)
        self.assertIsNone(mt)


class ParseMaintenanceDraftTests(SimpleTestCase):
    def test_valid(self):
        raw = json.dumps(
            {
                "title": "Leaking kitchen tap",
                "description": "Drip in main kitchen",
                "priority": "medium",
                "category": "plumbing",
            }
        )
        d = parse_maintenance_draft_response(raw)
        self.assertIsNotNone(d)
        self.assertEqual(d["title"], "Leaking kitchen tap")
        self.assertEqual(d["category"], "plumbing")
        self.assertEqual(d["priority"], "medium")

    def test_unknown_category_maps_to_other(self):
        raw = '{"title": "Thing", "description": "d", "priority": "low", "category": "quantum"}'
        d = parse_maintenance_draft_response(raw)
        self.assertEqual(d["category"], "other")

    def test_unknown_priority_maps_to_medium(self):
        raw = '{"title": "Thing", "description": "d", "priority": "mega", "category": "other"}'
        d = parse_maintenance_draft_response(raw)
        self.assertEqual(d["priority"], "medium")

    def test_empty_title_returns_none(self):
        raw = '{"title": "", "description": "d", "priority": "low", "category": "other"}'
        self.assertIsNone(parse_maintenance_draft_response(raw))


class TrainingFixtureTests(SimpleTestCase):
    """Ensure the training JSON file stays valid and documents expected shapes."""

    def test_training_fixture_loads(self):
        data = load_training_cases()
        self.assertIn("cases", data)
        self.assertIsInstance(data["cases"], list)
        for c in data["cases"]:
            self.assertIn("id", c)

    def test_training_fixture_parse_regressions(self):
        """All embedded sample_*_raw + expect_* blocks must match our parsers."""
        data = load_training_cases()
        errors = validate_all_cases(data)
        self.assertEqual(
            errors,
            [],
            "Training fixture parse regressions failed:\n" + "\n".join(errors),
        )
