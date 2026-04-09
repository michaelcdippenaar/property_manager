"""
Unit tests for the pure helpers in ``apps/leases/parse_view.py``.

Source file under test: apps/leases/parse_view.py

Covers the string / JSON plumbing that powers the lease-document extractor:
  - _message_text           — concatenates text blocks from a Claude response
  - _strip_markdown_fence    — removes ```json ... ``` wrappers
  - _extract_json_object     — brace-aware, string-aware JSON slicing
  - _relax_json              — trailing-comma cleanup
  - _parse_extracted_json    — full parse pipeline
  - normalize_extracted_lease — flattens nested `property` blobs into top-level
    keys the admin UI expects

These are pure functions — no HTTP layer, no Claude, no database.
"""
from unittest import mock

import pytest

from apps.leases.parse_view import (
    _extract_json_object,
    _message_text,
    _parse_extracted_json,
    _relax_json,
    _strip_markdown_fence,
    normalize_extracted_lease,
)

pytestmark = [pytest.mark.unit, pytest.mark.green]


# ─────────────────────────────────────────────────────────────────────────────
# _message_text
# ─────────────────────────────────────────────────────────────────────────────
class TestMessageText:
    def _text_block(self, text):
        b = mock.MagicMock()
        b.type = "text"
        b.text = text
        return b

    def _tool_block(self):
        b = mock.MagicMock()
        b.type = "tool_use"
        # No .text attribute — must be ignored
        del b.text
        return b

    def test_concatenates_single_text_block(self):
        msg = mock.MagicMock()
        msg.content = [self._text_block("hello")]
        assert _message_text(msg) == "hello"

    def test_concatenates_multiple_text_blocks(self):
        msg = mock.MagicMock()
        msg.content = [self._text_block("foo "), self._text_block("bar")]
        assert _message_text(msg) == "foo bar"

    def test_ignores_non_text_blocks(self):
        msg = mock.MagicMock()
        msg.content = [self._text_block("keep "), self._tool_block(), self._text_block("me")]
        assert _message_text(msg) == "keep me"

    def test_strips_surrounding_whitespace(self):
        msg = mock.MagicMock()
        msg.content = [self._text_block("   padded   ")]
        assert _message_text(msg) == "padded"

    def test_empty_content_returns_empty_string(self):
        msg = mock.MagicMock()
        msg.content = []
        assert _message_text(msg) == ""


# ─────────────────────────────────────────────────────────────────────────────
# _strip_markdown_fence
# ─────────────────────────────────────────────────────────────────────────────
class TestStripMarkdownFence:
    def test_strips_json_fenced_block(self):
        raw = '```json\n{"a": 1}\n```'
        assert _strip_markdown_fence(raw) == '{"a": 1}'

    def test_strips_plain_fenced_block(self):
        raw = '```\n{"a": 1}\n```'
        assert _strip_markdown_fence(raw) == '{"a": 1}'

    def test_case_insensitive_json_tag(self):
        raw = '```JSON\n{"a": 1}\n```'
        assert _strip_markdown_fence(raw) == '{"a": 1}'

    def test_no_fences_returns_input(self):
        assert _strip_markdown_fence('{"a": 1}') == '{"a": 1}'

    def test_leading_prose_before_fence_is_stripped(self):
        """LLM chatter before the fence should also be dropped."""
        raw = 'Here is the extracted data:\n```json\n{"ok": true}\n```'
        assert _strip_markdown_fence(raw) == '{"ok": true}'

    def test_empty_string_passes_through(self):
        assert _strip_markdown_fence("") == ""


# ─────────────────────────────────────────────────────────────────────────────
# _extract_json_object
# ─────────────────────────────────────────────────────────────────────────────
class TestExtractJsonObject:
    def test_simple_object(self):
        assert _extract_json_object('{"a": 1}') == '{"a": 1}'

    def test_ignores_prose_before_and_after(self):
        assert _extract_json_object('prose {"a": 1} more prose') == '{"a": 1}'

    def test_nested_braces(self):
        raw = '{"a": {"b": {"c": 1}}}'
        assert _extract_json_object(raw) == raw

    def test_braces_inside_strings_are_ignored(self):
        """A '}' inside a JSON string must not close the top-level object."""
        raw = '{"note": "curly } inside"}'
        assert _extract_json_object(raw) == raw

    def test_escaped_quotes_inside_strings(self):
        raw = '{"quote": "she said \\"hi\\""}'
        assert _extract_json_object(raw) == raw

    def test_returns_none_if_no_opening_brace(self):
        assert _extract_json_object("no json here") is None

    def test_returns_none_if_unbalanced(self):
        """Missing closing brace must not return a partial slice."""
        assert _extract_json_object('{"a": {"b": 1}') is None

    def test_extracts_first_object_only(self):
        """Only the first top-level object is returned even if two exist."""
        raw = '{"a": 1} {"b": 2}'
        assert _extract_json_object(raw) == '{"a": 1}'


# ─────────────────────────────────────────────────────────────────────────────
# _relax_json
# ─────────────────────────────────────────────────────────────────────────────
class TestRelaxJson:
    def test_removes_trailing_comma_before_close_brace(self):
        assert _relax_json('{"a": 1, }') == '{"a": 1 }'

    def test_removes_trailing_comma_before_close_bracket(self):
        assert _relax_json('[1, 2, 3, ]') == '[1, 2, 3 ]'

    def test_handles_nested_trailing_commas(self):
        raw = '{"a": [1, 2, ], "b": {"c": 3, }}'
        result = _relax_json(raw)
        assert ",  ]" not in result and ", }" not in result
        # The cleaned text should be valid JSON
        import json as _json
        _json.loads(result)

    def test_no_trailing_commas_unchanged(self):
        good = '{"a": 1, "b": 2}'
        assert _relax_json(good) == good


# ─────────────────────────────────────────────────────────────────────────────
# _parse_extracted_json — the full pipeline
# ─────────────────────────────────────────────────────────────────────────────
class TestParseExtractedJson:
    def test_plain_json(self):
        assert _parse_extracted_json('{"monthly_rent": 5000}') == {"monthly_rent": 5000}

    def test_fenced_json(self):
        raw = '```json\n{"monthly_rent": 5000}\n```'
        assert _parse_extracted_json(raw) == {"monthly_rent": 5000}

    def test_json_with_trailing_commas(self):
        raw = '{"monthly_rent": 5000, "deposit": 5000, }'
        result = _parse_extracted_json(raw)
        assert result == {"monthly_rent": 5000, "deposit": 5000}

    def test_fenced_json_with_leading_prose(self):
        raw = (
            "Here is the extracted lease data:\n"
            '```json\n{"start_date": "2026-01-01"}\n```\n'
            "Let me know if you need anything else."
        )
        assert _parse_extracted_json(raw) == {"start_date": "2026-01-01"}

    def test_returns_none_for_garbage(self):
        assert _parse_extracted_json("definitely not json") is None

    def test_returns_none_for_truncated_json(self):
        """Broken mid-string → first pass fails, relax pass fails → None."""
        assert _parse_extracted_json('{"a": "hello, world') is None

    def test_returns_none_for_non_object_json(self):
        """The extractor must return a dict; arrays and scalars are rejected."""
        assert _parse_extracted_json('[1, 2, 3]') is None

    def test_parses_nested_object_with_curly_in_string(self):
        raw = '{"note": "pay R{5000} monthly", "rent": 5000}'
        result = _parse_extracted_json(raw)
        assert result == {"note": "pay R{5000} monthly", "rent": 5000}


# ─────────────────────────────────────────────────────────────────────────────
# normalize_extracted_lease
# ─────────────────────────────────────────────────────────────────────────────
class TestNormalizeExtractedLease:
    def test_flattens_nested_property_address(self):
        d = {
            "property": {
                "address": "12 Vine Street, Stellenbosch",
                "name": "Vine Cottage",
                "city": "Stellenbosch",
                "province": "Western Cape",
                "postal_code": "7600",
            },
            "monthly_rent": 5000,
        }
        out = normalize_extracted_lease(d)
        assert out["property_address"] == "12 Vine Street, Stellenbosch"
        assert out["property_name"] == "Vine Cottage"
        assert out["property_city"] == "Stellenbosch"
        assert out["property_province"] == "Western Cape"
        assert out["property_postal_code"] == "7600"
        # Original keys preserved
        assert out["monthly_rent"] == 5000

    def test_nested_property_does_not_overwrite_top_level(self):
        """Top-level keys always win — don't clobber explicit values."""
        d = {
            "property_address": "Explicit Street 1",
            "property": {"address": "Nested Street 99"},
        }
        out = normalize_extracted_lease(d)
        assert out["property_address"] == "Explicit Street 1"

    def test_alternate_address_keys_promoted(self):
        """premises_address / leased_premises / premises / etc. → property_address."""
        alt_keys = [
            "premises_address",
            "leased_premises",
            "premises",
            "dwelling_address",
            "address_of_premises",
            "property_full_address",
            "full_address",
            "address",
        ]
        for key in alt_keys:
            d = {key: "18 Irene Park, La Colline"}
            out = normalize_extracted_lease(d)
            assert out["property_address"] == "18 Irene Park, La Colline", (
                f"{key} was not promoted to property_address"
            )

    def test_fallback_property_name_from_first_comma_segment(self):
        """When property_name is missing but property_address is set, the
        first comma-separated segment becomes the name."""
        d = {"property_address": "4 Otterkuil Street, Karindal, Stellenbosch"}
        out = normalize_extracted_lease(d)
        assert out["property_name"] == "4 Otterkuil Street"

    def test_explicit_property_name_is_kept(self):
        d = {
            "property_name": "Bosch en Dal Unit 3",
            "property_address": "Main Road, Franschhoek",
        }
        out = normalize_extracted_lease(d)
        assert out["property_name"] == "Bosch en Dal Unit 3"

    def test_non_dict_input_passes_through(self):
        """Defensive: pass through lists / None / strings unchanged."""
        assert normalize_extracted_lease([1, 2, 3]) == [1, 2, 3]
        assert normalize_extracted_lease(None) is None
        assert normalize_extracted_lease("hello") == "hello"

    def test_property_alt_name_keys_are_respected(self):
        d = {"property": {"label": "Erf 1234", "address": "Main Rd"}}
        out = normalize_extracted_lease(d)
        assert out["property_name"] == "Erf 1234"

    def test_property_alt_postal_keys_are_respected(self):
        """postal / postcode variants should all be promoted."""
        for key in ("postal_code", "postal", "postcode"):
            d = {"property": {key: "7600"}}
            out = normalize_extracted_lease(d)
            assert out["property_postal_code"] == "7600", f"key {key} not promoted"

    def test_empty_dict_returns_empty_dict(self):
        assert normalize_extracted_lease({}) == {}
