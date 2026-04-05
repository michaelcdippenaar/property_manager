/**
 * Vitest Browser Mode tests for tiptapSettings integrity.
 *
 * Verifies that CSS custom properties from tiptapSettings.ts are correctly
 * injected and that the shared `.tiptap-page-container` class resolves to
 * the correct max-width. Also asserts that no hardcoded max-width classes
 * have crept back into the 3 TipTap view components.
 *
 * Run:
 *   npm run test:browser
 *   npx vitest run src/__tests__/browser/tiptap-settings-integrity.browser.test.ts
 */
import { describe, it, expect, beforeAll } from 'vitest'
import {
  CSS_CUSTOM_PROPERTIES,
  PAGE_WIDTH,
  FONT_FAMILY,
  FONT_SIZE,
  LINE_HEIGHT,
  TEXT_COLOR,
  EDITOR_BACKGROUND,
  EDITOR_SHADOW,
} from '../../config/tiptapSettings'

// Inject CSS custom properties the same way main.ts does at app startup
beforeAll(() => {
  Object.entries(CSS_CUSTOM_PROPERTIES).forEach(([key, value]) => {
    document.documentElement.style.setProperty(key, value)
  })
})

// ── Tests: CSS Custom Properties ──────────────────────────────────────

describe('tiptapSettings — CSS Custom Properties', () => {

  it('--tiptap-page-width is set on document.documentElement', () => {
    const value = document.documentElement.style.getPropertyValue('--tiptap-page-width')
    expect(value).toBe(`${PAGE_WIDTH}px`)
  })

  it('--tiptap-font-family is set correctly', () => {
    const value = document.documentElement.style.getPropertyValue('--tiptap-font-family')
    expect(value).toBe(FONT_FAMILY)
  })

  it('--tiptap-font-size is set correctly', () => {
    const value = document.documentElement.style.getPropertyValue('--tiptap-font-size')
    expect(value).toBe(FONT_SIZE)
  })

  it('--tiptap-line-height is set correctly', () => {
    const value = document.documentElement.style.getPropertyValue('--tiptap-line-height')
    expect(value).toBe(`${LINE_HEIGHT}`)
  })

  it('--tiptap-text-color is set correctly', () => {
    const value = document.documentElement.style.getPropertyValue('--tiptap-text-color')
    expect(value).toBe(TEXT_COLOR)
  })

  it('--tiptap-editor-bg is set correctly', () => {
    const value = document.documentElement.style.getPropertyValue('--tiptap-editor-bg')
    expect(value).toBe(EDITOR_BACKGROUND)
  })

  it('--tiptap-editor-shadow is set correctly', () => {
    const value = document.documentElement.style.getPropertyValue('--tiptap-editor-shadow')
    expect(value).toBe(EDITOR_SHADOW)
  })

  it('all CSS_CUSTOM_PROPERTIES keys are present on documentElement', () => {
    const keys = Object.keys(CSS_CUSTOM_PROPERTIES)
    expect(keys.length).toBeGreaterThanOrEqual(7)
    for (const key of keys) {
      const value = document.documentElement.style.getPropertyValue(key)
      expect(value, `Missing CSS property: ${key}`).not.toBe('')
    }
  })
})

// ── Tests: Exported Constants ─────────────────────────────────────────

describe('tiptapSettings — Exported Constants', () => {

  it('PAGE_WIDTH is 794 (A4 at 96 DPI)', () => {
    expect(PAGE_WIDTH).toBe(794)
  })

  it('FONT_FAMILY includes Arial', () => {
    expect(FONT_FAMILY).toContain('Arial')
  })

  it('FONT_SIZE is 10.5pt', () => {
    expect(FONT_SIZE).toBe('10.5pt')
  })

  it('LINE_HEIGHT is 1.55', () => {
    expect(LINE_HEIGHT).toBe(1.55)
  })

  it('TEXT_COLOR is #111', () => {
    expect(TEXT_COLOR).toBe('#111')
  })
})

// ── Tests: .tiptap-page-container resolves to correct max-width ───────

describe('tiptapSettings — .tiptap-page-container class', () => {

  it('resolves max-width to PAGE_WIDTH from CSS custom property', () => {
    // Import the stylesheet (normally loaded by main.ts / global CSS)
    // We inject it manually for the test environment
    const style = document.createElement('style')
    style.textContent = `
      .tiptap-page-container {
        max-width: var(--tiptap-page-width);
      }
    `
    document.head.appendChild(style)

    // Create a test element with the class
    const el = document.createElement('div')
    el.className = 'tiptap-page-container'
    document.body.appendChild(el)

    const computed = getComputedStyle(el)
    expect(computed.maxWidth).toBe(`${PAGE_WIDTH}px`)

    // Cleanup
    el.remove()
    style.remove()
  })
})

// ── Tests: No hardcoded max-width in view components ──────────────────

describe('tiptapSettings — No hardcoded max-width in TipTap views', () => {

  // These tests statically import the raw SFC source to check for
  // hardcoded Tailwind max-width classes that should use the shared class.
  // We use dynamic import of the raw text via a glob pattern isn't available,
  // so we check the component modules' template at runtime.

  it('LeaseBuilderView does not use max-w-[794px] or max-w-[816px]', async () => {
    const mod = await import('../../views/leases/LeaseBuilderView.vue?raw')
    const source = mod.default
    expect(source).not.toContain('max-w-[794px]')
    expect(source).not.toContain('max-w-[816px]')
  })

  it('TiptapEditorView does not use max-w-[794px] or max-w-[816px]', async () => {
    const mod = await import('../../views/leases/TiptapEditorView.vue?raw')
    const source = mod.default
    expect(source).not.toContain('max-w-[794px]')
    expect(source).not.toContain('max-w-[816px]')
  })

  it('SigningDocumentViewer does not use max-w-[794px] or max-w-[816px]', async () => {
    const mod = await import('../../views/signing/SigningDocumentViewer.vue?raw')
    const source = mod.default
    expect(source).not.toContain('max-w-[794px]')
    expect(source).not.toContain('max-w-[816px]')
  })
})
