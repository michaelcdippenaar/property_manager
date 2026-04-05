# Issue: Signing Page vs Builder Pagination Mismatch
**Module:** esigning
**Status:** FIXED
**Discovered:** 2026-04-04 (manual testing)
**Test file:** apps/test_hub/esigning/integration/test_html_rendering.py::SigningBuilderConsistencyTests
**Frontend test:** admin/src/__tests__/browser/signing-builder-consistency.browser.test.ts

## Description
The signing page (`/sign/:token/`) and the lease builder (`/leases/build?template=35`) render the same document with different pagination. Section 7.4 appears on page 6 in the signing view but on page 7 in the builder.

## Reproduction Steps
1. Open `/leases/build?template=35` — note section 7.4 is on page 7
2. Open `/sign/50ce9cca-e28a-4a02-8b71-e70b68139abe/` — note section 7.4 is on page 6
3. Both should render identically since they use the same TipTap PaginationPlus plugin

## Root Cause
Container width mismatch between the two views:
- **Signing page** (`SigningDocumentViewer.vue`): `max-w-[816px]` — 22px wider than A4
- **Lease builder** (`TiptapEditorView.vue`): `max-w-[794px]` — matches A4 exactly
- Both use PaginationPlus configured with `pageWidth: 794`

The 22px extra space gives PaginationPlus a wider layout context in the signing view, causing text reflow and different page break positions.

## Fix Applied
1. Changed `SigningDocumentViewer.vue` container from `max-w-[816px]` to `max-w-[794px]`
2. Removed `px-4` horizontal padding from inner div (caused grey background bleed-through, squeezed white editor to 762px)
3. Created shared `tiptapSettings.ts` — single source of truth for page dimensions, typography, and PaginationPlus config
4. All 3 views now use `.tiptap-page-container` CSS class (max-width from CSS custom property)
5. Fixed LeaseBuilderView `max-width: 850px` → uses shared `tiptap-page-container` (794px)

## Test Coverage
- **Vitest Browser Mode:** `admin/src/__tests__/browser/signing-builder-consistency.browser.test.ts`
  - Container width assertion (794px)
  - ProseMirror editor width assertion
  - Page count parity between signing viewer and editor
- **Backend:** `test_html_rendering.py::SigningBuilderConsistencyTests`
  - Generated HTML `@page` CSS uses A4 size
  - Page margin values are documented and consistent
- **Playwright E2E:** `admin/e2e/builder-signing-consistency.spec.ts`
  - Live page container width verification
  - Page count comparison between signing and builder views
- Duplicate check: confirmed NOT covered — checked existing signing-visual-regression.spec.ts

## Status History
- 2026-04-04: Discovered during manual testing → RED
- 2026-04-04: Fixed `max-w-[816px]` → `max-w-[794px]` in SigningDocumentViewer.vue → FIXED
- 2026-04-04: Vitest Browser Mode set up + 6 browser tests green, 3 backend tests green, Playwright E2E added
