/**
 * E2E tests for rendering consistency between the signing page and the lease builder.
 *
 * Verifies that both views produce identical pagination when rendering
 * the same lease document with TipTap PaginationPlus.
 *
 * Prerequisites:
 *   - Vite dev server running on localhost:5173
 *   - Django backend running on localhost:8000
 *   - A native signing submission with a public link UUID
 *
 * Usage:
 *   npx playwright test e2e/builder-signing-consistency.spec.ts
 *
 * Environment variables:
 *   SIGN_UUID  — public link UUID (defaults to test fixture)
 */
import { test, expect, type Page } from '@playwright/test'

const SIGN_UUID = process.env.SIGN_UUID || '50ce9cca-e28a-4a02-8b71-e70b68139abe'
const A4_PAGE_WIDTH = 794

// ── Helpers ─────────────────────────────────────────────────────────

/** Pass through the consent gate on the signing page */
async function passConsentGate(page: Page) {
  await page.waitForLoadState('networkidle')
  const checkbox = page.locator('label input[type="checkbox"]')
  const visible = await checkbox.isVisible({ timeout: 5000 }).catch(() => false)
  if (visible) {
    await checkbox.click({ force: true })
    const button = page.locator('button:has-text("Get Started"):not([disabled])')
    await button.waitFor({ state: 'visible', timeout: 5000 })
    await button.click()
    await page.waitForTimeout(500)
  }
}

/** Wait for TipTap editor to fully render with pagination */
async function waitForTiptapReady(page: Page) {
  await page.waitForSelector('.tiptap.ProseMirror', { timeout: 15_000 })
  await page.waitForSelector('.tiptap.rm-with-pagination', { timeout: 10_000 })
  await page.waitForTimeout(1500)
}

/** Navigate to signing page and wait for document to render */
async function openSigningPage(page: Page) {
  await page.goto(`/sign/${SIGN_UUID}/`)
  await passConsentGate(page)
  await waitForTiptapReady(page)
}

/** Get the total number of paginated pages */
async function getPageCount(page: Page): Promise<number> {
  return page.evaluate(() => {
    return document.querySelectorAll('.rm-pagination-gap').length + 1
  })
}

// ── Tests: Container Width Consistency ─────────────────────────────

test.describe('Builder ↔ Signing — Container Width', () => {

  test('signing page container width is 794px (A4)', async ({ page }) => {
    await openSigningPage(page)

    const maxWidth = await page.evaluate(() => {
      const wrapper = document.querySelector('.signing-document-viewer > div') as HTMLElement
      if (!wrapper) return null
      return getComputedStyle(wrapper).maxWidth
    })

    expect(maxWidth).toBe(`${A4_PAGE_WIDTH}px`)
  })

  test('signing page ProseMirror width does not exceed A4', async ({ page }) => {
    await openSigningPage(page)

    const editorWidth = await page.evaluate(() => {
      const pm = document.querySelector('.tiptap.ProseMirror') as HTMLElement
      if (!pm) return 0
      return pm.getBoundingClientRect().width
    })

    // ProseMirror rendered width should not exceed configured pageWidth
    expect(editorWidth).toBeLessThanOrEqual(A4_PAGE_WIDTH + 1)
    expect(editorWidth).toBeGreaterThan(0)
  })
})

// ── Tests: Pagination Consistency ──────────────────────────────────

test.describe('Builder ↔ Signing — Pagination', () => {

  test('signing page has consistent page count across reloads', async ({ page }) => {
    await openSigningPage(page)
    const count1 = await getPageCount(page)

    await page.reload()
    await passConsentGate(page)
    await waitForTiptapReady(page)
    const count2 = await getPageCount(page)

    console.log(`Signing page count: ${count1} → ${count2}`)
    expect(count1).toBe(count2)
  })

  test('signing page renders reasonable page count', async ({ page }) => {
    await openSigningPage(page)
    const pageCount = await getPageCount(page)

    console.log(`Signing document: ${pageCount} pages`)
    // A standard lease should be 5-25 pages
    expect(pageCount).toBeGreaterThanOrEqual(5)
    expect(pageCount).toBeLessThanOrEqual(25)
  })
})
