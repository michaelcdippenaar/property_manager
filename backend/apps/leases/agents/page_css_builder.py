"""CSS ``@page`` block builder for the Formatter agent.

Emits Variant A (CSS ``@page`` margin boxes) as confirmed by the
Gotenberg POC at ``backend/scripts/spikes/per_page_initials_spike.py``.

The canonical block shape matches ``build_variant_a()`` from the spike
exactly:

    @page {
        size: A4;
        margin: 2cm 2cm 3cm 2cm;

        @top-right {
            content: "Residential Lease — page " counter(page) " of " counter(pages);
            ...
        }

        @bottom-center {
            content: "I have read this page — initials: ____";
            ...
        }
    }

Usage::

    builder = PageCssBuilder.from_html(html)
    builder.running_header = "Lease Agreement — {page} of {pages}"
    builder.running_footer = "I have read this page — initials: ____"
    new_html = builder.write_back(html)
"""
from __future__ import annotations

import re

# ── Regex patterns ───────────────────────────────────────────────────── #

# Matches an existing @page { ... } block in a <style> tag. Non-greedy
# inner match so it doesn't swallow a second rule if there's one.
# We treat the block as opaque — we extract and replace it wholesale
# rather than parsing individual at-rules inside it.
_AT_PAGE_RE = re.compile(
    r"(@page\s*\{(?:[^{}]*|\{[^{}]*\})*\})",
    re.DOTALL | re.IGNORECASE,
)

# Matches a full <style> tag (capturing inner content) so we can replace
# or inject the @page block inside it.
_STYLE_TAG_RE = re.compile(
    r"(<style[^>]*>)(.*?)(</style>)",
    re.DOTALL | re.IGNORECASE,
)

# Placeholder tokens the builder supports in header/footer text.
# ``{page}`` → ``counter(page)``; ``{pages}`` → ``counter(pages)``.
_PLACEHOLDER_RE = re.compile(r"\{pages?\}")


# ── Placeholder → CSS counter expansion ─────────────────────────────── #

def _escape_css_string(text: str) -> str:
    """P1-4: escape a literal text fragment for use inside a CSS double-quoted string.

    CSS string escaping per CSS Syntax Module Level 3 §4.3.7:
      - ``\\`` → ``\\\\``
      - ``"``  → ``\\"``

    This prevents a Formatter tool call from injecting CSS that closes the
    quoted string and inserts arbitrary rules.
    """
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _expand_placeholders(text: str) -> str:
    """Expand ``{page}`` and ``{pages}`` into CSS counter() calls.

    Input:  ``"Residential Lease — page {page} of {pages}"``
    Output: ``"Residential Lease — page " counter(page) " of " counter(pages)``

    This is the CSS ``content:`` property value — the counters are not
    quoted; they sit adjacent to quoted string fragments.

    P1-4: literal text fragments are CSS-string-escaped via
    :func:`_escape_css_string` before interpolation so that
    user-controllable text cannot inject arbitrary CSS rules.
    """
    if not text:
        return ""
    # Split on placeholders; reassemble with counter() expressions between
    # the literal fragments.
    parts = _PLACEHOLDER_RE.split(text)
    tokens = _PLACEHOLDER_RE.findall(text)

    fragments: list[str] = []
    for i, part in enumerate(parts):
        if part:
            fragments.append(f'"{_escape_css_string(part)}"')
        if i < len(tokens):
            tok = tokens[i]
            if tok == "{page}":
                fragments.append("counter(page)")
            elif tok == "{pages}":
                fragments.append("counter(pages)")
    return " ".join(fragments) if fragments else '""'


# ── Builder ──────────────────────────────────────────────────────────── #


class PageCssBuilder:
    """Immutable-state builder for the CSS ``@page`` block.

    Attributes:
        running_header: text for ``@top-right`` margin box.
            ``{page}`` / ``{pages}`` expand to CSS ``counter()`` calls.
            Empty string omits the ``@top-right`` rule.
        running_footer: text for ``@bottom-center`` margin box.
            Same placeholder semantics. Empty string omits the rule.
        page_size: value for ``size:`` property (default ``"A4"``).
        margins: shorthand for ``margin:`` (default ``"2cm 2cm 3cm 2cm"``).
    """

    def __init__(
        self,
        *,
        running_header: str = "",
        running_footer: str = "",
        page_size: str = "A4",
        margins: str = "2cm 2cm 3cm 2cm",
    ):
        self.running_header = running_header
        self.running_footer = running_footer
        self.page_size = page_size or "A4"
        self.margins = margins or "2cm 2cm 3cm 2cm"

    # ── Factory ──────────────────────────────────────────────────────── #

    @classmethod
    def from_html(cls, html: str) -> "PageCssBuilder":
        """Parse the first ``@page`` block from ``html``.

        Extracts ``size`` / ``margin`` values and the ``content:`` strings
        from any ``@top-right`` / ``@bottom-center`` sub-rules. Returns a
        fresh :class:`PageCssBuilder` populated with whatever was found.
        When no ``@page`` block exists, all defaults apply.
        """
        builder = cls()
        at_page_match = _AT_PAGE_RE.search(html or "")
        if at_page_match is None:
            return builder

        block = at_page_match.group(1)

        # Extract size
        size_m = re.search(r"size:\s*([^;]+);", block)
        if size_m:
            builder.page_size = size_m.group(1).strip()

        # Extract margin
        margin_m = re.search(r"margin:\s*([^;]+);", block)
        if margin_m:
            builder.margins = margin_m.group(1).strip()

        # Extract @top-right content
        top_right_m = re.search(
            r"@top-right\s*\{[^}]*content:\s*([^;]+);", block, re.DOTALL
        )
        if top_right_m:
            builder.running_header = _css_content_to_text(top_right_m.group(1).strip())

        # Extract @bottom-center content
        bottom_center_m = re.search(
            r"@bottom-center\s*\{[^}]*content:\s*([^;]+);", block, re.DOTALL
        )
        if bottom_center_m:
            builder.running_footer = _css_content_to_text(
                bottom_center_m.group(1).strip()
            )

        return builder

    # ── Output ───────────────────────────────────────────────────────── #

    def to_css(self) -> str:
        """Emit the canonical ``@page`` block (Variant A shape).

        Matches ``build_variant_a()`` from the spike exactly — same
        ``font-family``, ``font-size``, ``color``, ``border-top`` decorations.
        Only the ``@top-right`` / ``@bottom-center`` sub-rules are omitted when
        their text is empty.
        """
        inner_lines: list[str] = [
            f"        size: {self.page_size};",
            f"        margin: {self.margins};",
        ]

        if self.running_header:
            content_val = _expand_placeholders(self.running_header)
            inner_lines += [
                "",
                "        @top-right {",
                f"            content: {content_val};",
                "            font-family: Arial, sans-serif;",
                "            font-size: 8pt;",
                "            color: #555;",
                "        }",
            ]

        if self.running_footer:
            content_val = _expand_placeholders(self.running_footer)
            inner_lines += [
                "",
                "        @bottom-center {",
                f"            content: {content_val};",
                "            font-family: Arial, sans-serif;",
                "            font-size: 8pt;",
                "            color: #333;",
                "            border-top: 1px solid #ccc;",
                "            padding-top: 4pt;",
                "        }",
            ]

        return "@page {\n" + "\n".join(inner_lines) + "\n    }"

    def write_back(self, html: str) -> str:
        """Replace the existing ``@page`` block in ``html`` (or inject one).

        Three cases:
          1. ``html`` has a ``<style>`` tag containing an ``@page`` block
             → replace the ``@page`` block in place.
          2. ``html`` has a ``<style>`` tag but no ``@page`` block
             → prepend the ``@page`` block at the start of ``<style>``.
          3. ``html`` has no ``<style>`` tag
             → inject ``<style>@page {...}</style>`` into ``<head>`` if
             present, else prepend to the document.
        """
        new_at_page = self.to_css()

        # Case 1 / 2 — there's a <style> tag
        style_match = _STYLE_TAG_RE.search(html or "")
        if style_match is not None:
            open_tag, style_content, close_tag = (
                style_match.group(1),
                style_match.group(2),
                style_match.group(3),
            )
            if _AT_PAGE_RE.search(style_content):
                # Case 1: replace existing @page block inside the style tag
                new_style_content = _AT_PAGE_RE.sub(new_at_page, style_content, count=1)
            else:
                # Case 2: prepend @page block to existing style content
                new_style_content = new_at_page + "\n    " + style_content

            new_style = open_tag + new_style_content + close_tag
            return (
                html[: style_match.start()]
                + new_style
                + html[style_match.end():]
            )

        # Case 3: no <style> tag — inject before </head> or at the start
        injected = f"<style>\n    {new_at_page}\n</style>\n"
        head_close = html.find("</head>")
        if head_close != -1:
            return html[:head_close] + injected + html[head_close:]
        return injected + (html or "")


# ── Helpers ──────────────────────────────────────────────────────────── #


def _css_content_to_text(css_content_value: str) -> str:
    """Invert :func:`_expand_placeholders` — turn a CSS ``content:`` value
    back into a human-readable template string.

    ``"Residential Lease — page " counter(page) " of " counter(pages)``
    → ``"Residential Lease — page {page} of {pages}"``

    This is used by :meth:`PageCssBuilder.from_html` to round-trip
    existing ``@page`` blocks. Only plain string fragments and
    ``counter(page)`` / ``counter(pages)`` are handled; anything else is
    preserved verbatim.
    """
    val = css_content_value.strip()
    # Replace counter(pages) and counter(page) with template tokens
    val = val.replace("counter(pages)", "{pages}")
    val = val.replace("counter(page)", "{page}")
    # Strip adjacent quotes and join fragments:
    # ``"foo" "{page}" "bar"`` → ``foo{page}bar``
    # We simply collapse all quoted fragments and unquoted tokens.
    result_parts: list[str] = []
    i = 0
    while i < len(val):
        if val[i] in ('"', "'"):
            quote = val[i]
            end = val.find(quote, i + 1)
            if end == -1:
                result_parts.append(val[i + 1:])
                break
            result_parts.append(val[i + 1: end])
            i = end + 1
        elif val[i:].startswith("{page}") or val[i:].startswith("{pages}"):
            tok = "{pages}" if val[i:].startswith("{pages}") else "{page}"
            result_parts.append(tok)
            i += len(tok)
        else:
            # Skip whitespace separators between fragments
            i += 1
    return "".join(result_parts)


__all__ = ["PageCssBuilder"]
