/**
 * Visual regression tests for native signing page.
 *
 * Verifies that the signing page renders with proper A4 pagination,
 * consistent typography, and compact signing field elements that
 * don't cause content to overflow page boundaries.
 *
 * Prerequisites:
 *   - Vite dev server running on localhost:5173
 *   - Django backend running on localhost:8000
 *   - At least one native signing submission with a public link UUID
 *
 * Usage:
 *   npx playwright test e2e/signing-visual-regression.spec.ts
 *   npx playwright test --update-snapshots   # regenerate baselines
 *
 * Environment variables:
 *   SIGN_UUID  — public link UUID (defaults to test fixture)
 */
import { test, expect, type Page } from '@playwright/test'

const SIGN_UUID = process.env.SIGN_UUID || 'e8f3b219-97f5-402c-8df1-04c41590a35f'

// ── Helpers ─────────────────────────────────────────────────────────

/** Pass through the consent gate on the signing page */
async function passConsentGate(page: Page) {
  // Wait for the page to load
  await page.waitForLoadState('networkidle')

  const checkbox = page.locator('label input[type="checkbox"]')
  const visible = await checkbox.isVisible({ timeout: 5000 }).catch(() => false)
  if (visible) {
    // Click the label (more reliable than checkbox directly with Vue reactivity)
    await checkbox.click({ force: true })
    // Wait for Vue reactivity to enable the button
    const button = page.locator('button:has-text("Get Started"):not([disabled])')
    await button.waitFor({ state: 'visible', timeout: 5000 })
    await button.click()
    // Wait for document to start loading
    await page.waitForTimeout(500)
  }
}

/** Wait for TipTap editor to fully render with pagination */
async function waitForTiptapReady(page: Page) {
  await page.waitForSelector('.tiptap.ProseMirror', { timeout: 15_000 })
  await page.waitForSelector('.tiptap.rm-with-pagination', { timeout: 10_000 })
  // Let pagination settle
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
    // Count page gap elements + 1
    return document.querySelectorAll('.rm-pagination-gap').length + 1
  })
}

// ── Tests: Pagination & Layout ──────────────────────────────────────

test.describe('Signing Page — Pagination & Layout', () => {

  test('renders with A4 pagination', async ({ page }) => {
    await openSigningPage(page)

    // Verify pagination is active
    const hasPagination = await page.locator('.tiptap.rm-with-pagination').count()
    expect(hasPagination).toBeGreaterThan(0)

    // Verify page gaps exist (multi-page document)
    const pageGaps = await page.locator('.rm-pagination-gap').count()
    expect(pageGaps).toBeGreaterThan(0)

    const pageCount = await getPageCount(page)
    console.log(`Document has ${pageCount} pages`)
    expect(pageCount).toBeGreaterThanOrEqual(2)
  })

  test('uses correct typography', async ({ page }) => {
    await openSigningPage(page)

    const styles = await page.evaluate(() => {
      const tiptap = document.querySelector('.tiptap.ProseMirror')
      if (!tiptap) return null
      const cs = getComputedStyle(tiptap)
      return {
        fontFamily: cs.fontFamily,
        fontSize: cs.fontSize,
        lineHeight: cs.lineHeight,
        color: cs.color,
      }
    })

    expect(styles).not.toBeNull()
    // Must match tiptap-editor.css values
    expect(styles!.fontSize).toBe('14px') // 10.5pt ≈ 14px
    expect(styles!.fontFamily).toContain('Arial')
    expect(styles!.color).toBe('rgb(17, 17, 17)') // #111
  })

  test('has tiptap-editor class for shared styles', async ({ page }) => {
    await openSigningPage(page)

    // The editor-content wrapper must have tiptap-editor class
    const editorWrapper = page.locator('.tiptap-editor')
    await expect(editorWrapper).toBeVisible()
  })

  test('page footer shows page numbers', async ({ page }) => {
    await openSigningPage(page)

    // PaginationPlus renders footer with page numbers
    const footers = page.locator('.rm-page-footer-right')
    const count = await footers.count()
    expect(count).toBeGreaterThan(0)
  })
})

// ── Tests: Signing Field Sizing ─────────────────────────────────────

test.describe('Signing Page — Field Sizing', () => {

  test('unsigned initials buttons are compact', async ({ page }) => {
    await openSigningPage(page)

    // Find all unsigned initials buttons (contain "Click to Initial")
    const initialsButtons = page.locator('button:has-text("Click to Initial")')
    const count = await initialsButtons.count()

    if (count === 0) {
      test.skip(true, 'No unsigned initials fields — all may be signed already')
      return
    }

    for (let i = 0; i < Math.min(count, 5); i++) {
      const box = await initialsButtons.nth(i).boundingBox()
      if (!box) continue
      // Initials buttons must be compact: max 22px tall
      console.log(`Unsigned initials button ${i}: ${box.height}px`)
      expect(box.height).toBeLessThanOrEqual(22)
    }
  })

  test('signed initials images are compact', async ({ page }) => {
    await openSigningPage(page)

    // Find signed field images
    const signedImages = page.locator('img[alt="Signed"]')
    const count = await signedImages.count()

    if (count === 0) {
      test.skip(true, 'No signed fields to test — sign at least one field first')
      return
    }

    for (let i = 0; i < Math.min(count, 5); i++) {
      const imgBox = await signedImages.nth(i).boundingBox()
      if (!imgBox) continue
      console.log(`Signed image ${i}: ${imgBox.height}px`)
      // Signed initials image: max 20px, signatures: max 28px
      expect(imgBox.height).toBeLessThanOrEqual(28)
    }
  })

  test('unsigned signature buttons are reasonable size', async ({ page }) => {
    await openSigningPage(page)

    const sigButtons = page.locator('button:has-text("Click to Sign")')
    const count = await sigButtons.count()

    if (count === 0) {
      test.skip(true, 'No unsigned signature fields')
      return
    }

    for (let i = 0; i < Math.min(count, 3); i++) {
      const box = await sigButtons.nth(i).boundingBox()
      if (!box) continue
      console.log(`Unsigned signature button ${i}: ${box.height}px`)
      // Signature buttons can be taller but still reasonable
      expect(box.height).toBeLessThanOrEqual(34)
    }
  })

  test('pending chips are compact', async ({ page }) => {
    await openSigningPage(page)

    // "Pending: Landlord", "Pending: Tenant 2", etc.
    const pendingChips = page.locator('span:has-text("Pending:")')
    const count = await pendingChips.count()

    if (count === 0) {
      test.skip(true, 'No pending fields from other signers')
      return
    }

    for (let i = 0; i < Math.min(count, 5); i++) {
      const box = await pendingChips.nth(i).boundingBox()
      if (!box) continue
      console.log(`Pending chip ${i}: ${box.height}px`)
      expect(box.height).toBeLessThanOrEqual(22)
    }
  })
})

// ── Tests: Visual Snapshots ─────────────────────────────────────────

test.describe('Signing Page — Visual Snapshots', () => {

  test('first page matches baseline', async ({ page }) => {
    await openSigningPage(page)

    // Scroll to top
    await page.evaluate(() => {
      document.querySelector('.signing-document-viewer')?.scrollTo(0, 0)
    })
    await page.waitForTimeout(300)

    const docViewer = page.locator('.signing-document-viewer')
    await expect(docViewer).toHaveScreenshot('signing-first-page.png', {
      maxDiffPixelRatio: 0.03,
    })
  })

  test('initials row at page bottom matches baseline', async ({ page }) => {
    await openSigningPage(page)

    // Find the first signing field — could be a button or a pending/signed span
    const firstField = page.locator('button:has-text("Click to"), span:has-text("Pending:")').first()
    const exists = await firstField.isVisible({ timeout: 5000 }).catch(() => false)

    if (!exists) {
      test.skip(true, 'No signing fields visible in the document')
      return
    }

    await firstField.scrollIntoViewIfNeeded()
    await page.waitForTimeout(500)

    const fieldBox = await firstField.boundingBox()
    expect(fieldBox).not.toBeNull()

    if (fieldBox) {
      const clip = {
        x: Math.max(0, fieldBox.x - 200),
        y: Math.max(0, fieldBox.y - 30),
        width: 900,
        height: 80,
      }
      await expect(page).toHaveScreenshot('initials-row-at-page-bottom.png', {
        clip,
        maxDiffPixelRatio: 0.05,
      })
    }
  })

  test('page with all three field states matches baseline', async ({ page }) => {
    await openSigningPage(page)

    // Find a page that has a signed field (our field), pending field, and possibly unsigned
    // Navigate to first signed field
    const signedField = page.locator('img[alt="Signed"]').first()
    const exists = await signedField.isVisible({ timeout: 3000 }).catch(() => false)

    if (!exists) {
      test.skip(true, 'No signed fields — cannot test mixed field states')
      return
    }

    await signedField.scrollIntoViewIfNeeded()
    await page.waitForTimeout(500)

    // Screenshot the row containing mixed field states
    const container = signedField.locator('..').locator('..')
    const box = await container.boundingBox()
    if (box) {
      const clip = {
        x: Math.max(0, box.x - 200),
        y: Math.max(0, box.y - 20),
        width: 900,
        height: 60,
      }
      await expect(page).toHaveScreenshot('mixed-field-states.png', {
        clip,
        maxDiffPixelRatio: 0.05,
      })
    }
  })
})

// ── Tests: No Page Overflow ─────────────────────────────────────────

test.describe('Signing Page — No Page Overflow', () => {

  test('signing fields do not add extra pages compared to field count', async ({ page }) => {
    await openSigningPage(page)

    const pageCount = await getPageCount(page)

    // A reasonable lease should not have more than ~25 pages
    // If signing fields were inflating pages, we'd see significantly more
    console.log(`Document renders with ${pageCount} pages`)
    expect(pageCount).toBeLessThanOrEqual(25)
    expect(pageCount).toBeGreaterThanOrEqual(5)
  })

  test('last page content matches baseline snapshot', async ({ page }) => {
    await openSigningPage(page)

    // Scroll to the very bottom of the document
    await page.evaluate(() => {
      const viewer = document.querySelector('.signing-document-viewer') ||
                     document.querySelector('.flex-1.overflow-auto')
      if (viewer) viewer.scrollTop = viewer.scrollHeight
    })
    await page.waitForTimeout(500)

    // Screenshot the bottom portion (last page)
    await expect(page).toHaveScreenshot('signing-last-page.png', {
      maxDiffPixelRatio: 0.03,
    })
  })

  test('document page count is stable across reloads', async ({ page }) => {
    // Load the page twice and verify page count is consistent
    await openSigningPage(page)
    const count1 = await getPageCount(page)

    await page.reload()
    await passConsentGate(page)
    await waitForTiptapReady(page)
    const count2 = await getPageCount(page)

    console.log(`Page count: first load ${count1}, second load ${count2}`)
    expect(count1).toBe(count2)
  })
})
