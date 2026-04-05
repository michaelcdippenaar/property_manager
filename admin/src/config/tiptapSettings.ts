/**
 * Shared TipTap settings — single source of truth for page dimensions,
 * margins, typography, and PaginationPlus config.
 *
 * These values MUST stay identical across all 3 TipTap views:
 *   - Template Editor  (/leases/templates/:id/edit)
 *   - Lease Builder    (/leases/build?template=X)
 *   - Signing Page     (/sign/:token/)
 *
 * Change a value here and it propagates everywhere.
 */

// -- Page dimensions (A4 at 96 DPI) ------------------------------------------
export const PAGE_WIDTH = 794      // px
export const PAGE_HEIGHT = 1123    // px
export const PAGE_GAP = 40         // px between pages

// -- Margins ------------------------------------------------------------------
export const MARGIN_TOP = 48       // px
export const MARGIN_BOTTOM = 48    // px
export const MARGIN_LEFT = 32      // px
export const MARGIN_RIGHT = 32     // px

// -- Typography ---------------------------------------------------------------
export const FONT_FAMILY = 'Arial, sans-serif'
export const FONT_SIZE = '10.5pt'
export const LINE_HEIGHT = 1.55
export const TEXT_COLOR = '#111'

// -- Page chrome --------------------------------------------------------------
export const EDITOR_BACKGROUND = '#f1f3f4'
export const EDITOR_SHADOW = '0 0 0 1px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.1)'

// -- PaginationPlus config (pass directly to .configure()) --------------------
export const PAGINATION_CONFIG = {
  pageHeight: PAGE_HEIGHT,
  pageWidth: PAGE_WIDTH,
  pageGap: PAGE_GAP,
  pageGapBorderSize: 1,
  pageGapBorderColor: '#c4c7c5',
  pageBreakBackground: '#f8f9fa',
  marginTop: MARGIN_TOP,
  marginBottom: MARGIN_BOTTOM,
  marginLeft: MARGIN_LEFT,
  marginRight: MARGIN_RIGHT,
  contentMarginTop: 0,
  contentMarginBottom: 0,
  footerRight: '{page}',
  footerLeft: '',
  headerRight: '',
  headerLeft: '',
} as const

// -- CSS custom properties (injected at app startup) --------------------------
export const CSS_CUSTOM_PROPERTIES = {
  '--tiptap-page-width': `${PAGE_WIDTH}px`,
  '--tiptap-page-height': `${PAGE_HEIGHT}px`,
  '--tiptap-font-family': FONT_FAMILY,
  '--tiptap-font-size': FONT_SIZE,
  '--tiptap-line-height': `${LINE_HEIGHT}`,
  '--tiptap-text-color': TEXT_COLOR,
  '--tiptap-editor-bg': EDITOR_BACKGROUND,
  '--tiptap-editor-shadow': EDITOR_SHADOW,
} as const
