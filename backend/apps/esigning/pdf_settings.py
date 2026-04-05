"""
Shared page layout constants for PDF generation.

MUST match admin/src/config/tiptapSettings.ts — the browser-side source of truth.

These values control Gotenberg (Chromium) PDF rendering and must produce
identical pagination to the TipTap PaginationPlus browser preview.

Conversion: TipTap uses px at 96 DPI → mm = px ÷ 96 × 25.4
"""

# ── Page dimensions ──────────────────────────────────────────────────────
PAGE_SIZE = "A4"
PAGE_WIDTH_MM = 210
PAGE_HEIGHT_MM = 297

# ── Margins (mm) ─────────────────────────────────────────────────────────
# TipTap px → mm at 96 DPI:
#   48px ÷ 96 × 25.4 = 12.7mm
#   32px ÷ 96 × 25.4 = 8.47mm ≈ 8.5mm
MARGIN_TOP_MM = 12.7
MARGIN_BOTTOM_MM = 12.7
MARGIN_LEFT_MM = 8.5
MARGIN_RIGHT_MM = 8.5

# ── Typography ───────────────────────────────────────────────────────────
FONT_FAMILY = "Arial, sans-serif"
FONT_SIZE = "10.5pt"
LINE_HEIGHT = 1.55
TEXT_COLOR = "#111"

# ── Headings ─────────────────────────────────────────────────────────────
H1_FONT_SIZE = "14pt"
H2_FONT_SIZE = "11pt"
H3_FONT_SIZE = "10.5pt"

# ── Paragraph ────────────────────────────────────────────────────────────
P_MARGIN = "3pt 0"

# ── Tables ───────────────────────────────────────────────────────────────
TD_FONT_SIZE = "10pt"
TD_PADDING = "5pt 7pt"

# ── Formatted CSS @page rule ─────────────────────────────────────────────
PAGE_RULE = (
    f"@page {{ size: {PAGE_SIZE}; "
    f"margin: {MARGIN_TOP_MM}mm {MARGIN_RIGHT_MM}mm "
    f"{MARGIN_BOTTOM_MM}mm {MARGIN_LEFT_MM}mm; }}"
)
