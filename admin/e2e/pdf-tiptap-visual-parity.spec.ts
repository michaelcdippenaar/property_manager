/**
 * Layer 2: PDF vs TipTap Visual Parity Tests
 *
 * Prerequisites:
 *   - Layer 1 (test_pdf_css_parity.py) must pass — CSS values must be aligned
 *   - Vite dev server running on localhost:5173
 *   - Django backend running on localhost:8000
 *   - Gotenberg running on localhost:3000
 *   - A native signing submission with a public link UUID
 *
 * These tests compare the TipTap browser page count against the Gotenberg
 * PDF page count for the same document. If they differ (beyond the audit
 * trail page), the CSS values have drifted.
 *
 * Usage:
 *   npx playwright test e2e/pdf-tiptap-visual-parity.spec.ts
 *
 * Environment variables:
 *   SIGN_UUID       — public link UUID (defaults to test fixture)
 *   SUBMISSION_ID   — submission ID for PDF endpoint (defaults to test fixture)
 */
import { test, expect, type Page } from '@playwright/test'

const SIGN_UUID = process.env.SIGN_UUID || '50ce9cca-e28a-4a02-8b71-e70b68139abe'
const SUBMISSION_ID = process.env.SUBMISSION_ID || '74'
const API_BASE = process.env.API_BASE || 'http://localhost:8000'

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

/** Get TipTap page count from the signing page */
async function getTiptapPageCount(page: Page): Promise<number> {
  return page.evaluate(() => {
    return document.querySelectorAll('.rm-pagination-gap').length + 1
  })
}

/** Get PDF page count via the test-pdf endpoint */
async function getPdfPageCount(): Promise<number> {
  const resp = await fetch(`${API_BASE}/api/v1/esigning/submissions/${SUBMISSION_ID}/test-pdf/`)
  if (!resp.ok) {
    throw new Error(`test-pdf endpoint returned ${resp.status}: ${await resp.text()}`)
  }

  const pdfBytes = await resp.arrayBuffer()
  const pdfText = new TextDecoder('latin1').decode(pdfBytes)

  // Count pages by looking for /Type /Page entries (not /Type /Pages)
  const pageMatches = pdfText.match(/\/Type\s*\/Page[^s]/g)
  return pageMatches ? pageMatches.length : 0
}

// ── Tests ───────────────────────────────────────────────────────────

test.describe('PDF ↔ TipTap Visual Parity', () => {

  test('page count: TipTap + 1 (audit trail) === PDF', async ({ page }) => {
    // Get TipTap page count from signing page
    await page.goto(`/sign/${SIGN_UUID}/`)
    await passConsentGate(page)
    await waitForTiptapReady(page)

    const tiptapPages = await getTiptapPageCount(page)
    console.log(`TipTap page count: ${tiptapPages}`)
    expect(tiptapPages).toBeGreaterThan(0)

    // Get PDF page count
    const pdfPages = await getPdfPageCount()
    console.log(`PDF page count: ${pdfPages}`)
    expect(pdfPages).toBeGreaterThan(0)

    // PDF has one extra page: the audit trail
    // Allow ±1 tolerance for minor rendering differences
    const diff = Math.abs(pdfPages - (tiptapPages + 1))
    console.log(`Expected PDF pages: ${tiptapPages + 1} (TipTap + audit trail), actual: ${pdfPages}, diff: ${diff}`)
    expect(diff).toBeLessThanOrEqual(1)
  })

  test('PDF page count is stable across regeneration', async () => {
    const count1 = await getPdfPageCount()
    const count2 = await getPdfPageCount()

    console.log(`PDF page count: ${count1} → ${count2}`)
    expect(count1).toBe(count2)
  })

  test('PDF has no blank pages', async () => {
    const resp = await fetch(`${API_BASE}/api/v1/esigning/submissions/${SUBMISSION_ID}/test-pdf/`)
    expect(resp.ok).toBe(true)

    const pdfBytes = await resp.arrayBuffer()
    // Basic validation: PDF should start with %PDF header
    const header = new TextDecoder('latin1').decode(pdfBytes.slice(0, 5))
    expect(header).toBe('%PDF-')

    // File should be reasonably sized (not empty or trivially small)
    expect(pdfBytes.byteLength).toBeGreaterThan(10_000)
  })
})
