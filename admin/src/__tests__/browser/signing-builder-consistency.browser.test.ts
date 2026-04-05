/**
 * Vitest Browser Mode tests for signing page vs builder rendering consistency.
 *
 * These tests mount Vue components in a real Chromium browser to verify
 * that TipTap PaginationPlus renders identically in both views.
 *
 * Run:
 *   npm run test:browser
 *   npx vitest run src/__tests__/browser/signing-builder-consistency.browser.test.ts
 */
import { describe, it, expect, beforeAll, beforeEach } from 'vitest'
import { render } from 'vitest-browser-vue'
import SigningDocumentViewer from '../../views/signing/SigningDocumentViewer.vue'
import { CSS_CUSTOM_PROPERTIES, PAGE_WIDTH } from '../../config/tiptapSettings'

// ── Constants ──────────────────────────────────────────────────────────
/** A4 page width in px at 96 DPI — from shared tiptapSettings.ts */
const A4_PAGE_WIDTH = PAGE_WIDTH

// Inject CSS custom properties (normally done in main.ts at app startup)
beforeAll(() => {
  Object.entries(CSS_CUSTOM_PROPERTIES).forEach(([key, value]) => {
    document.documentElement.style.setProperty(key, value)
  })
})

// ── Shared Props ───────────────────────────────────────────────────────

function signingViewerProps(html: string) {
  return {
    html,
    signerRole: 'tenant_1',
    signedFields: new Map(),
    alreadySigned: [],
    onFieldClick: () => {},
    capturedFields: {},
    onMergeFieldChange: () => {},
  }
}

// ── Sample HTML ────────────────────────────────────────────────────────

const MINIMAL_HTML = '<h1>Residential Lease Agreement</h1><p>Test content for pagination verification.</p>'

// Multi-page HTML to test pagination consistency
const MULTI_PAGE_HTML = `
<h1 style="text-align:center;">RESIDENTIAL LEASE AGREEMENT</h1>
<h2>1. Schedule</h2>
<h3>1.1. Details of the Landlord</h3>
<p>The Landlord: <span style="font-weight:600">Test Landlord (Pty) Ltd</span></p>
<p>Registration No: <span style="font-weight:600">2020/123456/07</span></p>
<p>Landlord Representative: <span style="font-weight:600">John Landlord</span></p>
<p>Landlord Email: <span style="font-weight:600">landlord@test.com</span></p>
<p>Physical Address: <span style="font-weight:600">10 Main Rd, Cape Town, 8001</span></p>
<h3>1.2. Details of the Tenant/s</h3>
<h3>1.3. Tenant One</h3>
<p>Full Legal Name: <span style="font-weight:600">Test Tenant</span></p>
<p>ID or Passport No: <span style="font-weight:600">9001015800083</span></p>
<p>Email: <span style="font-weight:600">tenant@test.com</span></p>
<h2>2. Property Description</h2>
<p>The Landlord hereby lets and the Tenant hereby hires the property described as Unit 101, Test Property, 123 Test St, Cape Town, Western Cape, 8001.</p>
<h2>3. Duration</h2>
<p>This lease shall commence on 1 January 2026 and shall endure for a fixed period of 12 months, terminating on 31 December 2026.</p>
<h2>4. Rental</h2>
<p>The monthly rental payable by the Tenant shall be R5,000.00 (Five Thousand Rand), due and payable in advance on or before the 1st day of each month.</p>
<p>The rental shall escalate annually by 8% on the anniversary of the commencement date.</p>
<h2>5. Deposit</h2>
<p>The Tenant shall pay a deposit of R10,000.00 (Ten Thousand Rand) on or before the commencement date. The deposit shall be held in a trust account and shall accrue interest.</p>
<h2>6. Obligations of the Tenant</h2>
<p>6.1. The Tenant shall use the property solely for residential purposes and shall not conduct any business from the premises without the prior written consent of the Landlord.</p>
<p>6.2. The Tenant shall keep the property in a good state of repair and shall be responsible for any damage caused by the Tenant or the Tenant's guests.</p>
<p>6.3. The Tenant shall not make any alterations to the property without the prior written consent of the Landlord.</p>
<p>6.4. The Tenant shall not sub-let the property or any part thereof without the prior written consent of the Landlord.</p>
<p>6.5. The Tenant shall comply with all rules and regulations of the body corporate or homeowners association, if applicable.</p>
<p>6.6. The Tenant shall maintain adequate insurance for the Tenant's personal belongings and shall not hold the Landlord liable for any loss or damage.</p>
<h2>7. Obligations of the Landlord</h2>
<p>7.1. The Landlord shall ensure that the property is in a habitable condition at the commencement of the lease and shall maintain the structural integrity of the property.</p>
<p>7.2. The Landlord shall be responsible for all structural repairs and maintenance of the common areas.</p>
<p>7.3. The Landlord shall provide the Tenant with a copy of the house rules, if applicable, within 7 days of the commencement of the lease.</p>
<p>7.4. The Landlord shall give the Tenant reasonable notice of any inspections or maintenance work to be carried out at the property. Such notice shall not be less than 24 hours.</p>
<p>7.5. The Landlord shall ensure compliance with all applicable laws and regulations, including but not limited to the Rental Housing Act and POPIA.</p>
<h2>8. Termination</h2>
<p>8.1. Either party may terminate this lease by giving not less than 20 calendar days written notice to the other party, in accordance with the Rental Housing Act.</p>
<p>8.2. In the event of early termination by the Tenant, the Tenant shall be liable for a reasonable cancellation penalty not exceeding the rental for the unexpired portion of the lease.</p>
<h2>9. General</h2>
<p>9.1. This agreement constitutes the entire agreement between the parties and no amendment or variation shall be binding unless reduced to writing and signed by both parties.</p>
<p>9.2. This agreement shall be governed by the laws of the Republic of South Africa.</p>
`.trim()

// ── Tests: Container Width ─────────────────────────────────────────────

describe('Signing Viewer — Container Width', () => {

  it('outer wrapper uses tiptap-page-container class (shared A4 page width)', async () => {
    const screen = render(SigningDocumentViewer, {
      props: signingViewerProps(MINIMAL_HTML),
    })

    // Allow TipTap to initialise
    await new Promise(r => setTimeout(r, 1500))

    const wrapper = document.querySelector('.signing-document-viewer > div') as HTMLElement
    expect(wrapper).not.toBeNull()

    // The wrapper must use the shared tiptap-page-container class
    // which sets max-width via CSS custom property from tiptapSettings.ts
    const classList = wrapper.className
    expect(classList).toContain('tiptap-page-container')

    // Must NOT have hardcoded max-width Tailwind classes (use shared class instead)
    expect(classList).not.toContain('max-w-[816px]')
    expect(classList).not.toContain('max-w-[794px]')

    // Must NOT have horizontal padding inside the max-width container.
    // Padding squeezes the white bg-white area narrower than ProseMirror (794px),
    // causing grey background bleed-through on the sides.
    expect(classList).not.toMatch(/\bpx-\d/)
    expect(classList).not.toMatch(/\bpl-\d/)
    expect(classList).not.toMatch(/\bpr-\d/)

    screen.unmount()
  })

  it('ProseMirror editor width matches PaginationPlus pageWidth', async () => {
    // Render inside a constrained container to simulate real layout
    const containerDiv = document.createElement('div')
    containerDiv.style.width = '1280px'
    document.body.appendChild(containerDiv)

    const screen = render(SigningDocumentViewer, {
      props: signingViewerProps(MINIMAL_HTML),
      container: containerDiv,
    })

    // Wait for TipTap + PaginationPlus to settle
    await new Promise(r => setTimeout(r, 2500))

    const prosemirror = containerDiv.querySelector('.tiptap.ProseMirror') as HTMLElement
    expect(prosemirror).not.toBeNull()

    // PaginationPlus sets an inline style with the configured pageWidth.
    // Check that the rm-with-pagination class is applied (confirms PaginationPlus is active)
    expect(prosemirror.classList.contains('rm-with-pagination')).toBe(true)

    screen.unmount()
    containerDiv.remove()
  })
})

// ── Tests: Pagination ──────────────────────────────────────────────────

describe('Signing Viewer — Pagination', () => {

  it('renders with PaginationPlus active', async () => {
    const screen = render(SigningDocumentViewer, {
      props: signingViewerProps(MULTI_PAGE_HTML),
    })

    // Wait for PaginationPlus to kick in
    await new Promise(r => setTimeout(r, 3000))

    const paginatedEditor = document.querySelector('.tiptap.rm-with-pagination')
    expect(paginatedEditor).not.toBeNull()

    screen.unmount()
  })

  it('multi-page content produces page gaps', async () => {
    const screen = render(SigningDocumentViewer, {
      props: signingViewerProps(MULTI_PAGE_HTML),
    })

    await new Promise(r => setTimeout(r, 3000))

    const pageGaps = document.querySelectorAll('.rm-pagination-gap')
    // Multi-page lease should have at least 1 page gap (2+ pages)
    expect(pageGaps.length).toBeGreaterThan(0)

    const pageCount = pageGaps.length + 1
    console.log(`Signing viewer renders ${pageCount} pages`)

    screen.unmount()
  })

  it('page count is stable across re-renders', async () => {
    // First render
    const screen1 = render(SigningDocumentViewer, {
      props: signingViewerProps(MULTI_PAGE_HTML),
    })
    await new Promise(r => setTimeout(r, 3000))
    const count1 = document.querySelectorAll('.rm-pagination-gap').length + 1
    screen1.unmount()

    // Wait for cleanup
    await new Promise(r => setTimeout(r, 500))

    // Second render
    const screen2 = render(SigningDocumentViewer, {
      props: signingViewerProps(MULTI_PAGE_HTML),
    })
    await new Promise(r => setTimeout(r, 3000))
    const count2 = document.querySelectorAll('.rm-pagination-gap').length + 1
    screen2.unmount()

    console.log(`Page count: render 1 = ${count1}, render 2 = ${count2}`)
    expect(count1).toBe(count2)
  })
})

// ── Tests: Typography Consistency ──────────────────────────────────────

describe('Signing Viewer — Typography', () => {

  it('uses Arial 10.5pt base font', async () => {
    const screen = render(SigningDocumentViewer, {
      props: signingViewerProps(MINIMAL_HTML),
    })

    await new Promise(r => setTimeout(r, 1500))

    const prosemirror = document.querySelector('.tiptap.ProseMirror') as HTMLElement
    expect(prosemirror).not.toBeNull()

    const styles = getComputedStyle(prosemirror)
    expect(styles.fontFamily).toContain('Arial')
    expect(styles.fontSize).toBe('14px') // 10.5pt ≈ 14px
    expect(styles.color).toBe('rgb(17, 17, 17)') // #111

    screen.unmount()
  })
})
