"""Regression: AI lease-template chat must NOT destroy signature blocks.

Before commit (see audit punch-list #1), every `update_all` and most
`edit_lines` calls silently destroyed any existing SignatureBlock /
InitialsBlock / DateBlock / SignedAtBlock TipTap nodes. Root cause:
``_strip_tags`` removes the tags on input (Claude never sees them),
then ``_rebuild_html_from_lines`` / ``merge_lines_into_html`` only emit
``<h*>/<p>/<li>/<hr>/<table>`` — signature tags evaporate.

Fix: tokenisation via ``_extract_signature_tokens`` /
``_restore_signature_tokens`` so the blocks survive the AI round-trip
even though Claude only sees opaque ``⟪SIG#N⟫`` magic strings.

These tests exercise the helpers directly (no Anthropic API call) plus
the round-trip through ``html_to_plain_lines`` →
``_rebuild_html_from_lines`` to prove the fix end-to-end.
"""
from __future__ import annotations

import pytest

from apps.leases.template_views import (
    _SA_STANDARD_SECTION_BODIES,
    _build_signature_field_html,
    _extract_signature_tokens,
    _format_sa_standard,
    _rebuild_html_from_lines,
    _restore_signature_tokens,
    html_to_plain_lines,
    merge_lines_into_html,
)


pytestmark = [pytest.mark.integration]


# ── Unit: tokenise / restore ─────────────────────────────────────────────

class TestSignatureTokenisation:
    def test_self_closing_signature_tag_round_trip(self):
        html = '<p>Sign here: <signature-field name="ll_sig" role="landlord" required="true" /></p>'
        tok, sb = _extract_signature_tokens(html)
        assert "⟪SIG#0⟫" in tok
        assert "<signature-field" not in tok
        assert sb["⟪SIG#0⟫"].startswith("<signature-field")
        assert _restore_signature_tokens(tok, sb) == html

    def test_paired_signature_tag_round_trip(self):
        html = '<p><signature-field name="x" role="tenant"></signature-field></p>'
        tok, sb = _extract_signature_tokens(html)
        assert tok == "<p>⟪SIG#0⟫</p>"
        assert _restore_signature_tokens(tok, sb) == html

    def test_all_four_tag_types_tokenised(self):
        html = (
            '<p><signature-field name="a" role="landlord" /></p>'
            '<p><initials-field name="b" role="tenant" /></p>'
            '<p><date-field name="c" role="landlord" /></p>'
            '<p><signedat-field name="d" role="tenant" /></p>'
        )
        tok, sb = _extract_signature_tokens(html)
        assert tok.count("⟪SIG#") == 4
        # IDs are sequential by document position
        assert "⟪SIG#0⟫" in tok and "⟪SIG#1⟫" in tok and "⟪SIG#2⟫" in tok and "⟪SIG#3⟫" in tok
        assert len(sb) == 4
        assert _restore_signature_tokens(tok, sb) == html

    def test_implicit_delete_when_token_omitted(self):
        """If Claude removes a token from its output, the corresponding
        signature block is dropped silently — this is the only sanctioned
        way for the AI to remove signature blocks."""
        html = (
            '<p>Landlord: <signature-field name="a" role="landlord" /></p>'
            '<p>Witness: <signature-field name="b" role="witness" /></p>'
        )
        tok, sb = _extract_signature_tokens(html)
        # Simulate Claude dropping the witness block
        edited = tok.replace("⟪SIG#1⟫", "").replace("Witness: ", "(no witness required) ")
        restored = _restore_signature_tokens(edited, sb)
        assert "name=\"a\"" in restored
        assert "name=\"b\"" not in restored
        assert "(no witness required)" in restored

    def test_unknown_token_artefacts_stripped(self):
        """Defensive: if a token-shaped string slips into the output but
        isn't in the sidecar, strip it rather than rendering it raw."""
        tok = "<p>Hello ⟪SIG#42⟫ world</p>"
        restored = _restore_signature_tokens(tok, {})
        assert restored == "<p>Hello  world</p>"

    def test_preserves_complex_attributes(self):
        """Attributes (name, role, required, style) must round-trip exactly."""
        html = (
            '<p><signature-field '
            'name="tenant_signature_1" '
            'role="tenant" '
            'required="true" '
            'style="width: 240px; height: 60px; border-bottom: 2px solid #000;" '
            '/></p>'
        )
        tok, sb = _extract_signature_tokens(html)
        restored = _restore_signature_tokens(tok, sb)
        assert restored == html


# ── Integration: round-trip survives the AI's view of the document ──────

class TestSignatureSurvivesRoundTrip:
    """The bug audit identified was that signature blocks were destroyed by
    ``html_to_plain_lines`` → ``_rebuild_html_from_lines``. These tests prove
    that with tokenisation in place, blocks survive."""

    def test_html_to_plain_lines_carries_tokens(self):
        html = '<p>Sign: <signature-field name="x" role="landlord" /></p>'
        tok, _ = _extract_signature_tokens(html)
        lines = html_to_plain_lines(tok)
        # The line text should contain the opaque token (since _strip_tags
        # doesn't match ⟪⟫ unicode brackets as HTML).
        assert any("⟪SIG#0⟫" in ln["text"] for ln in lines)

    def test_full_round_trip_via_rebuild_preserves_blocks(self):
        """End-to-end: tokenise → AI view (plain lines) → rebuild → restore.
        Blocks must end up byte-identical in the final HTML."""
        html = (
            '<h1>LEASE AGREEMENT</h1>'
            '<p>Landlord signature: <signature-field name="ll_sig" role="landlord" required="true" /></p>'
            '<p>Tenant signature: <signature-field name="t_sig" role="tenant" required="true" /></p>'
            '<p>Date: <date-field name="signed_date" role="landlord" /></p>'
        )
        tok, sidecar = _extract_signature_tokens(html)
        lines = html_to_plain_lines(tok)
        # Simulate Claude returning the same lines unchanged
        rebuilt = _rebuild_html_from_lines(tok, lines)
        final = _restore_signature_tokens(rebuilt, sidecar)
        # All three blocks must be present with exact attributes
        assert 'name="ll_sig"' in final
        assert 'name="t_sig"' in final
        assert 'name="signed_date"' in final
        assert final.count("<signature-field") == 2
        assert final.count("<date-field") == 1

    def test_merge_lines_into_html_preserves_blocks(self):
        """merge_lines_into_html (used for partial edit_lines edits) must
        preserve token-bearing paragraphs when the line text is edited."""
        html = (
            '<p>Landlord: <signature-field name="ll" role="landlord" /></p>'
            '<p>Tenant: <signature-field name="t" role="tenant" /></p>'
        )
        tok, sb = _extract_signature_tokens(html)
        # Simulate Claude editing line 0 to change "Landlord:" → "Lessor:"
        edited_line_text = next(
            ln for ln in html_to_plain_lines(tok) if ln["i"] == 0
        )["text"].replace("Landlord:", "Lessor:")
        edits = [{"i": 0, "tag": "p", "text": edited_line_text}]
        new_html = merge_lines_into_html(tok, edits)
        final = _restore_signature_tokens(new_html, sb)
        assert "Lessor:" in final
        assert 'name="ll"' in final
        assert 'name="t"' in final


# ── _build_signature_field_html ──────────────────────────────────────────

class TestBuildSignatureFieldHtml:
    """The AI Section 3 fix added insert_signature_field as a tool. This
    builder emits the canonical TipTap-compatible signing-field HTML."""

    def test_signature_tag_shape(self):
        html = _build_signature_field_html("signature", "landlord")
        assert html.startswith("<signature-field")
        assert 'name="landlord_signature"' in html
        assert 'role="landlord"' in html
        assert 'required="true"' in html
        assert 'format="drawn_or_typed"' in html
        # Round-trips through the extractor
        tok, sb = _extract_signature_tokens(html)
        assert tok == "⟪SIG#0⟫"
        assert _restore_signature_tokens(tok, sb) == html

    def test_initials_has_no_format_attr(self):
        html = _build_signature_field_html("initials", "tenant_1")
        assert html.startswith("<initials-field")
        assert "format=" not in html  # only signature carries format
        assert 'name="tenant_1_initials"' in html

    def test_date_field_shape(self):
        html = _build_signature_field_html("date", "landlord")
        assert html.startswith("<date-field")
        assert 'name="landlord_date"' in html

    def test_signed_at_field_shape(self):
        html = _build_signature_field_html("signed_at", "tenant_1")
        assert html.startswith("<signedat-field")
        assert 'name="tenant_1_signed_at"' in html

    def test_custom_field_name_overrides_default(self):
        html = _build_signature_field_html("initials", "landlord", field_name="landlord_initials_p2")
        assert 'name="landlord_initials_p2"' in html
        assert 'data-field-name="landlord_initials_p2"' in html

    def test_unknown_type_falls_back_to_signature(self):
        # Defensive: prevents Claude from emitting an exotic field_type and
        # ending up with empty tags.
        html = _build_signature_field_html("bogus_type", "landlord")
        assert html.startswith("<signature-field")


# ── _format_sa_standard — usable boilerplate, not [needs completion] stubs ─

class TestFormatSaStandardEmitsRealProse:
    """Audit #13 — _format_sa_standard used to emit
    `<p><em>[This section needs to be completed]</em></p>` for every
    missing section, making the AI's "I've restructured your template"
    confident reply technically true but practically useless. Now each
    section ships with RHA / CPA / POPIA-compliant prose."""

    def test_all_13_sections_have_a_body(self):
        # Every standard section must have prose, not be missing from the dict
        from apps.leases.template_views import _SA_STANDARD_SECTIONS
        for name, _ in _SA_STANDARD_SECTIONS:
            assert name in _SA_STANDARD_SECTION_BODIES, (
                f"Section {name!r} has no boilerplate body — _format_sa_standard "
                f"will fall back to the [needs completion] placeholder."
            )

    def test_no_section_is_a_needs_completion_placeholder(self):
        """The boilerplate must NOT be the old stub. This is the test that
        would have failed before audit #13 was fixed."""
        for name, body in _SA_STANDARD_SECTION_BODIES.items():
            assert "[This section needs to be completed]" not in body, (
                f"Section {name!r} is still the stub."
            )
            assert "[needs completion]" not in body, (
                f"Section {name!r} is still the stub."
            )
            # Each body should be at least 200 chars of real prose — the old
            # stub was ~52 chars. Catches future regressions where someone
            # accidentally truncates a body to "Edit this." or similar.
            assert len(body) > 200, (
                f"Section {name!r} body is suspiciously short ({len(body)} chars): "
                f"{body!r}"
            )

    def test_rha_cpa_popia_sections_cite_their_statutes(self):
        """Spot-check that the legally-load-bearing sections actually carry
        the right statutory references."""
        rental = _SA_STANDARD_SECTION_BODIES["RENTAL AND DEPOSIT"]
        assert "Rental Housing Act" in rental
        assert "5(3)(f)" in rental or "interest-bearing" in rental
        assert "14 days" in rental or "14 day" in rental

        cpa = _SA_STANDARD_SECTION_BODIES["CONSUMER PROTECTION ACT"]
        assert "Consumer Protection Act" in cpa
        assert "Section 14" in cpa or "section 14" in cpa
        assert "20 business days" in cpa

        popia = _SA_STANDARD_SECTION_BODIES["PROTECTION OF PERSONAL INFORMATION"]
        assert "Protection of Personal Information Act" in popia
        assert "Information Regulator" in popia

        dispute = _SA_STANDARD_SECTION_BODIES["DISPUTE RESOLUTION"]
        assert "Rental Housing Tribunal" in dispute
        assert "PIE" in _SA_STANDARD_SECTION_BODIES["NOTICE AND TERMINATION"] or \
               "Prevention of Illegal Eviction" in _SA_STANDARD_SECTION_BODIES["NOTICE AND TERMINATION"]

    def test_format_sa_standard_on_empty_doc_produces_real_lease(self):
        """End-to-end: starting from a stub document, the formatted output
        must contain real prose for every section — not a list of TODOs.
        This is the test that would have caught MC's bug today."""
        stub = '<p>Placeholder lease. Edit before use.</p>'
        out = _format_sa_standard(stub, add_missing=True)
        # Must not contain the old stub copy
        assert "[This section needs to be completed]" not in out, (
            "Output still contains the [needs completion] placeholder — "
            "_format_sa_standard regressed to its v1 behaviour."
        )
        # Must contain real legal prose anchors
        assert "Rental Housing Act" in out
        assert "Consumer Protection Act" in out
        assert "Protection of Personal Information Act" in out
        assert "Rental Housing Tribunal" in out
        # And every h2 has body content after it
        sections = re.split(r'(?=<h2)', out)
        for sec in sections:
            if "<h2>" not in sec:
                continue
            # Strip the h2 heading
            body = re.sub(r'<h2[^>]*>.*?</h2>', '', sec, count=1, flags=re.I)
            assert body.strip(), f"Empty section body: {sec[:100]!r}"

    def test_format_sa_standard_preserves_existing_sections(self):
        """If a section is already present in the source, _format_sa_standard
        must leave it alone — only fill missing sections."""
        custom_html = (
            '<h2>PARTIES</h2>\n'
            '<p>This is the original parties block — MC wrote it, leave alone.</p>\n'
            '<h2>SIGNATURES</h2>\n<p>Original signatures.</p>\n'
        )
        out = _format_sa_standard(custom_html, add_missing=True)
        # Custom PARTIES content preserved verbatim
        assert "MC wrote it, leave alone" in out
        # Missing sections added (e.g. PREMISES)
        assert "<h2>PREMISES</h2>" in out
        # SIGNATURES stays at the end
        assert out.rstrip().endswith("Original signatures.</p>") or \
               "Original signatures" in out.split("<h2>SIGNATURES</h2>")[-1]


# `re` is imported in the production module; pull it locally for the assertions
import re  # noqa: E402
