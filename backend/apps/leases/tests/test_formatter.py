"""Formatter agent tests — Phase 3.

Nine test classes covering:

  * PageCssBuilder round-trip (parse → modify → write_back)
  * Individual tool implementations:
    - set_running_header
    - set_running_footer
    - set_per_page_initials (default + custom text)
    - insert_page_break
  * FormatterHandler via scripted fake client:
    - tool loop executes and applies changes
    - MAX_TOOL_CALLS budget cap
  * Integration: audit intent skips the Formatter route
  * Front Door route table: generate includes formatter, audit does not
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any

from apps.leases.agents.formatter_tools import (
    apply_insert_page_break,
    apply_set_per_page_initials,
    apply_set_running_footer,
    apply_set_running_header,
)
from apps.leases.agents.page_css_builder import PageCssBuilder


# ── Fixtures ─────────────────────────────────────────────────────────── #


MINIMAL_HTML = """<!DOCTYPE html>
<html><head><title>Test</title></head>
<body><h2 id="deposit">DEPOSIT</h2><p>Deposit clause.</p></body>
</html>"""

HTML_WITH_STYLE = """<!DOCTYPE html>
<html><head><style>
body { font-family: Arial; }
</style></head>
<body><h2 id="rent">RENT</h2><p>Rent clause.</p></body>
</html>"""

HTML_WITH_AT_PAGE = """<!DOCTYPE html>
<html><head><style>
@page {
        size: A4;
        margin: 2cm 2cm 3cm 2cm;

        @bottom-center {
            content: "Old footer";
            font-family: Arial, sans-serif;
            font-size: 8pt;
        }
    }
body { font-family: Arial; }
</style></head>
<body><p>Content</p></body>
</html>"""


# ── PageCssBuilder tests ──────────────────────────────────────────────── #


class PageCssBuilderRoundTripTests(unittest.TestCase):
    """test_page_css_builder_round_trip — parse → modify → write_back."""

    def test_from_html_no_existing_at_page(self):
        """Builder constructed from HTML without @page has blank header/footer."""
        builder = PageCssBuilder.from_html(MINIMAL_HTML)
        self.assertEqual(builder.running_header, "")
        self.assertEqual(builder.running_footer, "")
        self.assertEqual(builder.page_size, "A4")

    def test_from_html_parses_existing_bottom_center(self):
        """Builder extracts the existing @bottom-center content string."""
        builder = PageCssBuilder.from_html(HTML_WITH_AT_PAGE)
        self.assertEqual(builder.running_footer, "Old footer")

    def test_write_back_injects_style_tag_when_none_exists(self):
        """write_back injects a <style> block when the document has none."""
        bare_html = "<html><head></head><body><p>text</p></body></html>"
        builder = PageCssBuilder(running_footer="Footer text")
        result = builder.write_back(bare_html)
        self.assertIn("<style>", result)
        self.assertIn("@page", result)
        self.assertIn('"Footer text"', result)

    def test_write_back_replaces_existing_at_page_block(self):
        """write_back replaces an existing @page block in the <style> tag."""
        builder = PageCssBuilder.from_html(HTML_WITH_AT_PAGE)
        builder.running_footer = "New footer"
        result = builder.write_back(HTML_WITH_AT_PAGE)
        # The old content should be replaced.
        self.assertNotIn('"Old footer"', result)
        self.assertIn('"New footer"', result)
        # Should not have two @page blocks.
        self.assertEqual(result.count("@page"), 1)

    def test_write_back_prepends_at_page_when_style_has_none(self):
        """write_back prepends @page to a <style> tag that doesn't have one."""
        builder = PageCssBuilder(running_header="My Header")
        result = builder.write_back(HTML_WITH_STYLE)
        self.assertIn("@page", result)
        self.assertIn('"My Header"', result)
        # Existing body rule must still be present.
        self.assertIn("font-family: Arial", result)

    def test_placeholder_expansion_in_to_css(self):
        """to_css() expands {page} and {pages} to counter() expressions."""
        builder = PageCssBuilder(
            running_header="Lease page {page} of {pages}"
        )
        css = builder.to_css()
        self.assertIn("counter(page)", css)
        self.assertIn("counter(pages)", css)
        self.assertNotIn("{page}", css)
        self.assertNotIn("{pages}", css)

    def test_empty_header_omits_top_right_rule(self):
        """When running_header is empty, @top-right is not emitted."""
        builder = PageCssBuilder(running_footer="Footer only")
        css = builder.to_css()
        self.assertNotIn("@top-right", css)
        self.assertIn("@bottom-center", css)

    def test_empty_footer_omits_bottom_center_rule(self):
        """When running_footer is empty, @bottom-center is not emitted."""
        builder = PageCssBuilder(running_header="Header only")
        css = builder.to_css()
        self.assertIn("@top-right", css)
        self.assertNotIn("@bottom-center", css)


# ── Tool: set_running_header ─────────────────────────────────────────── #


class SetRunningHeaderTests(unittest.TestCase):
    """test_set_running_header_inserts_at_top_right."""

    def test_inserts_at_top_right(self):
        """set_running_header inserts @top-right with the given text."""
        result = apply_set_running_header({"text": "My Header"}, MINIMAL_HTML)
        self.assertTrue(result["ok"])
        self.assertIn("@top-right", result["new_html"])
        self.assertIn('"My Header"', result["new_html"])

    def test_counter_placeholders_expanded(self):
        """set_running_header expands {page}/{pages} to counter() calls."""
        result = apply_set_running_header(
            {"text": "Lease {page} of {pages}"}, MINIMAL_HTML
        )
        self.assertTrue(result["ok"])
        self.assertIn("counter(page)", result["new_html"])
        self.assertIn("counter(pages)", result["new_html"])

    def test_replaces_existing_header(self):
        """Calling set_running_header twice replaces the prior value."""
        first = apply_set_running_header({"text": "Old Header"}, MINIMAL_HTML)
        second = apply_set_running_header({"text": "New Header"}, first["new_html"])
        self.assertTrue(second["ok"])
        self.assertNotIn('"Old Header"', second["new_html"])
        self.assertIn('"New Header"', second["new_html"])
        self.assertEqual(second["new_html"].count("@page"), 1)

    def test_change_summary_mentions_text(self):
        result = apply_set_running_header({"text": "Test"}, MINIMAL_HTML)
        self.assertIn("Test", result["change_summary"])


# ── Tool: set_running_footer ─────────────────────────────────────────── #


class SetRunningFooterTests(unittest.TestCase):
    """test_set_running_footer_emits_correct_at_rule."""

    def test_emits_bottom_center(self):
        result = apply_set_running_footer({"text": "Footer text"}, MINIMAL_HTML)
        self.assertTrue(result["ok"])
        self.assertIn("@bottom-center", result["new_html"])
        self.assertIn('"Footer text"', result["new_html"])

    def test_empty_string_clears_footer(self):
        """Empty text string results in no @bottom-center rule."""
        # First set a footer, then clear it.
        with_footer = apply_set_running_footer({"text": "Footer"}, MINIMAL_HTML)
        cleared = apply_set_running_footer({"text": ""}, with_footer["new_html"])
        self.assertTrue(cleared["ok"])
        # The @bottom-center rule should be absent.
        self.assertNotIn("@bottom-center", cleared["new_html"])

    def test_change_summary_confirms_clear(self):
        result = apply_set_running_footer({"text": ""}, MINIMAL_HTML)
        self.assertIn("cleared", result["change_summary"])


# ── Tool: set_per_page_initials ──────────────────────────────────────── #


class SetPerPageInitialsTests(unittest.TestCase):
    """test_set_per_page_initials_uses_default_text +
       test_set_per_page_initials_accepts_custom_text."""

    def test_default_text(self):
        """set_per_page_initials uses the SA standard wording by default."""
        result = apply_set_per_page_initials({}, MINIMAL_HTML)
        self.assertTrue(result["ok"])
        self.assertIn("I have read this page", result["new_html"])
        self.assertIn("initials", result["new_html"])
        self.assertIn("@bottom-center", result["new_html"])

    def test_default_text_when_empty_string_passed(self):
        """An empty text= argument falls back to the SA default."""
        result = apply_set_per_page_initials({"text": ""}, MINIMAL_HTML)
        self.assertTrue(result["ok"])
        self.assertIn("I have read this page", result["new_html"])

    def test_custom_text(self):
        """set_per_page_initials accepts custom wording."""
        custom = "Initials: ___"
        result = apply_set_per_page_initials({"text": custom}, MINIMAL_HTML)
        self.assertTrue(result["ok"])
        self.assertIn(custom, result["new_html"])

    def test_change_summary_names_tool(self):
        result = apply_set_per_page_initials({}, MINIMAL_HTML)
        self.assertIn("set_per_page_initials", result["change_summary"])


# ── Tool: insert_page_break ──────────────────────────────────────────── #


class InsertPageBreakTests(unittest.TestCase):
    """test_insert_page_break_adds_div_after_section."""

    def test_inserts_break_after_matched_h2(self):
        """insert_page_break inserts the break div after <h2 id="deposit">."""
        result = apply_insert_page_break(
            {"after_section_id": "deposit"}, MINIMAL_HTML
        )
        self.assertTrue(result["ok"])
        html = result["new_html"]
        self.assertIn('page-break-after: always', html)
        # The break must come AFTER the </h2> of the matched heading.
        deposit_pos = html.find('id="deposit"')
        h2_close_pos = html.find("</h2>", deposit_pos)
        break_pos = html.find("page-break-after", h2_close_pos)
        self.assertGreater(break_pos, h2_close_pos)

    def test_missing_section_id_returns_ok_false(self):
        """insert_page_break returns ok=False when the id is not in the HTML."""
        result = apply_insert_page_break(
            {"after_section_id": "nonexistent-section"}, MINIMAL_HTML
        )
        self.assertFalse(result["ok"])
        # HTML must be unchanged.
        self.assertEqual(result["new_html"], MINIMAL_HTML)
        self.assertIn("nonexistent-section", result["change_summary"])

    def test_missing_after_section_id_arg(self):
        """insert_page_break returns ok=False when after_section_id is empty."""
        result = apply_insert_page_break({}, MINIMAL_HTML)
        self.assertFalse(result["ok"])

    def test_change_summary_names_section(self):
        result = apply_insert_page_break(
            {"after_section_id": "deposit"}, MINIMAL_HTML
        )
        self.assertIn("deposit", result["change_summary"])


# ── FormatterHandler via scripted fake client ────────────────────────── #


def _fake_usage() -> SimpleNamespace:
    return SimpleNamespace(
        input_tokens=100,
        output_tokens=50,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )


def _fake_response(
    content: list[dict[str, Any]],
    *,
    stop_reason: str = "end_turn",
) -> SimpleNamespace:
    blocks = [SimpleNamespace(**c) for c in content]
    return SimpleNamespace(
        id="msg_fake",
        type="message",
        role="assistant",
        model="claude-haiku-4-5-20251001",
        stop_reason=stop_reason,
        stop_sequence=None,
        content=blocks,
        usage=_fake_usage(),
    )


class _ScriptedAnthropic:
    """Fake Anthropic client that returns scripted responses."""

    def __init__(self, responses: list[SimpleNamespace]):
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.messages = self

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if not self._responses:
            raise RuntimeError("ScriptedAnthropic: no more responses queued.")
        return self._responses.pop(0)


def _ctx() -> Any:
    from apps.leases.agents.context import IntentEnum, LeaseContext

    return LeaseContext(
        intent=IntentEnum.FORMAT,
        user_message="format this document",
        property_type="sectional_title",
        tenant_count=1,
        lease_type="fixed_term",
        chat_history=({"role": "user", "content": "format this document"},),
        template_html=MINIMAL_HTML,
    )


def _runner(client: _ScriptedAnthropic) -> Any:
    from apps.leases.agent_runner import LeaseAgentRunner

    return LeaseAgentRunner(
        request_id="test-fmt",
        intent="format",
        anthropic_client=client,
        max_calls=8,
        max_wallclock_seconds=60.0,
        max_retries=1,
        max_cost_usd=1.0,
    )


class FormatterHandlerTests(unittest.TestCase):
    """test_formatter_handler_runs_tool_loop_via_scripted_client."""

    def test_handler_applies_set_running_header_and_footer(self):
        """FormatterHandler executes tool_use blocks from the model response."""
        from apps.leases.agents.formatter import FormatterHandler

        resp = _fake_response(
            [
                {
                    "type": "tool_use",
                    "id": "tu_1",
                    "name": "set_running_header",
                    "input": {"text": "Lease {page} of {pages}"},
                },
                {
                    "type": "tool_use",
                    "id": "tu_2",
                    "name": "set_per_page_initials",
                    "input": {},
                },
                {
                    "type": "text",
                    "text": "Applied running header and per-page initials.",
                },
            ]
        )
        client = _ScriptedAnthropic([resp])
        runner = _runner(client)
        handler = FormatterHandler()
        result = handler.run(
            runner=runner,
            context=_ctx(),
            document_html=MINIMAL_HTML,
            system_blocks=[],
        )

        # Both tools applied successfully.
        self.assertEqual(len(result.applied_changes), 2)
        self.assertIn("@top-right", result.html)
        self.assertIn("I have read this page", result.html)
        self.assertEqual(result.internal_turns, 1)
        self.assertIn("Applied", result.conversational_reply)

    def test_handler_no_tool_calls_returns_unchanged_html(self):
        """When model returns no tool_use blocks, HTML is unchanged."""
        from apps.leases.agents.formatter import FormatterHandler

        resp = _fake_response(
            [{"type": "text", "text": "No changes needed."}]
        )
        client = _ScriptedAnthropic([resp])
        runner = _runner(client)
        handler = FormatterHandler()
        result = handler.run(
            runner=runner,
            context=_ctx(),
            document_html=MINIMAL_HTML,
            system_blocks=[],
        )

        self.assertEqual(result.html, MINIMAL_HTML)
        self.assertEqual(result.applied_changes, [])
        self.assertEqual(result.conversational_reply, "No changes needed.")


class FormatterBudgetCapTests(unittest.TestCase):
    """test_formatter_respects_budget_cap — max 6 tool calls."""

    def test_cap_at_six_tool_calls(self):
        """FormatterHandler stops executing after MAX_TOOL_CALLS=6 tool_use blocks."""
        from apps.leases.agents.formatter import FormatterHandler

        # 8 tool_use blocks in one response — only 6 should execute.
        tool_blocks = [
            {
                "type": "tool_use",
                "id": f"tu_{i}",
                "name": "set_running_footer",
                "input": {"text": f"Footer {i}"},
            }
            for i in range(8)
        ]
        resp = _fake_response(tool_blocks)
        client = _ScriptedAnthropic([resp])
        runner = _runner(client)
        handler = FormatterHandler()
        result = handler.run(
            runner=runner,
            context=_ctx(),
            document_html=MINIMAL_HTML,
            system_blocks=[],
        )

        # MAX_TOOL_CALLS = 6; at most 6 changes applied.
        self.assertLessEqual(len(result.applied_changes), FormatterHandler.MAX_TOOL_CALLS)
        self.assertEqual(result.terminated_reason, "tool_cap")


# ── Front Door route table ────────────────────────────────────────────── #


class FrontDoorFormatterRouteTests(unittest.TestCase):
    """test_formatter_skipped_on_audit_intent — Front Door integration."""

    def _route_for_intent(self, intent_str: str) -> tuple[str, ...]:
        from apps.leases.agents.front_door import _ROUTE_BY_INTENT
        from apps.leases.agents.context import IntentEnum

        return _ROUTE_BY_INTENT[IntentEnum(intent_str)]

    def test_generate_includes_formatter(self):
        route = self._route_for_intent("generate")
        self.assertIn("formatter", route)
        self.assertIn("drafter", route)
        self.assertIn("reviewer", route)

    def test_format_intent_routes_to_formatter_only(self):
        route = self._route_for_intent("format")
        self.assertIn("formatter", route)
        self.assertNotIn("drafter", route)
        self.assertNotIn("reviewer", route)

    def test_audit_intent_skips_formatter(self):
        route = self._route_for_intent("audit")
        self.assertNotIn("formatter", route)
        self.assertIn("reviewer", route)

    def test_audit_case_law_intent_skips_formatter(self):
        route = self._route_for_intent("audit_case_law")
        self.assertNotIn("formatter", route)

    def test_edit_intent_skips_formatter(self):
        route = self._route_for_intent("edit")
        self.assertNotIn("formatter", route)


# ── Formatter persona checks ─────────────────────────────────────────── #


class FormatterPersonaTests(unittest.TestCase):
    """Persona contains the load-bearing invariants."""

    def test_persona_forbids_prose_changes(self):
        from apps.leases.agents.formatter import PERSONA_FORMATTER

        self.assertIn("NEVER change", PERSONA_FORMATTER)

    def test_persona_names_sa_initials_convention(self):
        from apps.leases.agents.formatter import PERSONA_FORMATTER

        self.assertIn("I have read this page", PERSONA_FORMATTER)

    def test_persona_names_header_pattern(self):
        from apps.leases.agents.formatter import PERSONA_FORMATTER

        self.assertIn("{page}", PERSONA_FORMATTER)


if __name__ == "__main__":
    unittest.main()
