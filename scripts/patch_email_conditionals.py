#!/usr/bin/env python3
"""
patch_email_conditionals.py
Post-process a compiled MJML HTML file to re-insert Django template
conditional blocks that MJML strips during compilation.

Usage:
    python3 patch_email_conditionals.py <input.html> <output.html>

The script uses HTML comment markers placed in base.mjml as reliable anchors:
  <!-- BLOCK: optional CTA button -->   → wraps the CTA <tr> with {% if cta_url %}
  <!-- BLOCK: optional secondary note --> → wraps the note <tr> with {% if note %}

It is idempotent: running it twice on an already-patched file is a no-op.
"""

import re
import sys
from pathlib import Path


def patch(html: str) -> str:
    # ── CTA button block ──────────────────────────────────────────────────────
    # Anchor: <!-- BLOCK: optional CTA button -->
    # The compiled output places a <tr>...</tr> for the button after this comment.
    # We wrap that <tr> block with {% if cta_url %} ... {% endif %}.
    # Guard: skip if already patched.
    if "{% if cta_url %}" not in html:
        cta_marker = "<!-- BLOCK: optional CTA button -->"
        cta_pattern = re.compile(
            r"(" + re.escape(cta_marker) + r"\s*\n)"  # the comment line
            r"(\s*<tr>.*?</tr>\s*\n)",  # the single <tr>…</tr> block for the button
            re.DOTALL,
        )

        def _wrap_cta(m: re.Match) -> str:
            indent = "                      "  # 22 spaces — matches file indentation
            return (
                m.group(1)
                + indent + "{% if cta_url %}\n"
                + m.group(2)
                + indent + "{% endif %}\n"
            )

        html, count = cta_pattern.subn(_wrap_cta, html, count=1)
        if count == 0:
            raise RuntimeError(
                "Could not locate CTA button block in compiled HTML. "
                "Check that '<!-- BLOCK: optional CTA button -->' is present."
            )

    # ── Secondary note block ──────────────────────────────────────────────────
    if "{% if note %}" not in html:
        note_marker = "<!-- BLOCK: optional secondary note -->"
        note_pattern = re.compile(
            r"(" + re.escape(note_marker) + r"\s*\n)"
            r"(\s*<tr>.*?</tr>\s*\n)",
            re.DOTALL,
        )

        def _wrap_note(m: re.Match) -> str:
            indent = "                      "
            return (
                m.group(1)
                + indent + "{% if note %}\n"
                + m.group(2)
                + indent + "{% endif %}\n"
            )

        html, count = note_pattern.subn(_wrap_note, html, count=1)
        if count == 0:
            raise RuntimeError(
                "Could not locate secondary note block in compiled HTML. "
                "Check that '<!-- BLOCK: optional secondary note -->' is present."
            )

    return html


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.html> <output.html>", file=sys.stderr)
        sys.exit(1)

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])

    html = src.read_text(encoding="utf-8")
    patched = patch(html)
    dst.write_text(patched, encoding="utf-8")
    print(f"Patched: {dst}")


if __name__ == "__main__":
    main()
