# Issue: PDF CSS Does Not Match TipTap Browser Settings
**Module:** esigning (PDF generation)
**Status:** OPEN
**Discovered:** 2026-04-05 (code review)
**Priority:** High

## Description
The CSS used for Gotenberg PDF generation (`_SIGNED_PDF_CSS` in `services.py`) uses different typography and margin values than the TipTap browser editor (`tiptapSettings.ts`). This causes documents to reflow differently in the PDF compared to what the user sees in the editor, potentially changing page counts and page break positions.

## Mismatches

| Setting | TipTap (browser) | PDF (`_SIGNED_PDF_CSS`) | Impact |
|---------|-------------------|-------------------------|--------|
| Font family | `Arial, sans-serif` | `'Segoe UI', 'Helvetica Neue', Arial` | Different glyph widths → text reflow |
| Line height | `1.55` | `1.6` | More vertical space → more pages |
| Text color | `#111` | `#1a1a1a` | Minor visual difference |
| H1 size | `14pt` | `15pt` | Headings take more space |
| H2 size | `11pt` | `11.5pt` | Headings take more space |
| Page margins | 48/48/32/32 px (~12.7/12.7/8.5/8.5 mm) | `20mm 18mm 22mm 18mm` | Different content area → text reflow |

## Expected Behavior
Since Gotenberg uses Chromium (same engine as the browser), the PDF should render identically to the TipTap editor if the same CSS values are used. The shared `tiptapSettings.ts` should be the single source of truth, with the backend PDF CSS consuming the same values.

## Proposed Fix
1. Align `_SIGNED_PDF_CSS` in `services.py` with values from `tiptapSettings.ts`
2. Consider a shared constants approach (e.g. a Python config that mirrors the TypeScript constants)
3. Add a test that asserts PDF CSS values match frontend settings

## Files Involved
- `backend/apps/esigning/services.py` — `_SIGNED_PDF_CSS` constant (lines 1178-1379)
- `admin/src/config/tiptapSettings.ts` — frontend source of truth
- `backend/apps/esigning/gotenberg.py` — Gotenberg client

## Status History
- 2026-04-05: Discovered during code review of HTML→PDF pipeline → OPEN
