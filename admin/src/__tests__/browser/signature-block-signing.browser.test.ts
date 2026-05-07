/**
 * Vitest Browser Mode tests for SignatureBlockComponent in signing mode.
 *
 * These tests mount the component with a signing context injected via
 * Vue provide/inject to verify all signing-mode branches render correctly:
 * date auto-fill, click-to-sign button, signed checkmark, pending states,
 * and initials compact styling.
 *
 * Run:
 *   npm run test:browser
 *   npx vitest run src/__tests__/browser/signature-block-signing.browser.test.ts
 */
import { describe, it, expect, beforeAll, vi } from 'vitest'
import { render } from 'vitest-browser-vue'
import { defineComponent, h, provide } from 'vue'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import { SignatureBlock } from '../../extensions/SignatureBlockNode'
import { CSS_CUSTOM_PROPERTIES } from '../../config/tiptapSettings'

// Inject CSS custom properties (normally done in main.ts at app startup)
beforeAll(() => {
  Object.entries(CSS_CUSTOM_PROPERTIES).forEach(([key, value]) => {
    document.documentElement.style.setProperty(key, value)
  })
})

// ── Helpers ───────────────────────────────────────────────────────────

interface SigningContext {
  signerRole: string
  signedFields: Map<string, { imageData: string; signedAt: string }>
  alreadySigned: Array<{ fieldName: string; fieldType: string; signerName: string; signedAt: string }>
  onFieldClick: (fieldName: string, fieldType: string) => void
}

/**
 * Build a TipTap editor containing a single signatureBlock node,
 * wrap it in a component that provides the signing context via inject,
 * and render it in the browser DOM.
 */
function renderSignatureBlock(opts: {
  fieldName: string
  fieldType: 'signature' | 'initials' | 'date'
  signerRole: string
  signingContext: SigningContext
}) {
  const { fieldName, fieldType, signerRole, signingContext } = opts

  // Build the JSON doc with a single signature block node
  const doc = {
    type: 'doc',
    content: [
      {
        type: 'paragraph',
        content: [
          {
            type: 'signatureBlock',
            attrs: {
              fieldName,
              fieldType,
              signerRole,
              label: '',
            },
          },
        ],
      },
    ],
  }

  // Wrapper component that provides signing context and mounts a TipTap editor
  const WrapperComponent = defineComponent({
    name: 'SigningTestWrapper',
    setup() {
      // Provide the signing context so SignatureBlockComponent picks it up
      provide('signingContext', signingContext)

      const editor = new Editor({
        content: doc,
        editable: false,
        extensions: [
          StarterKit,
          SignatureBlock,
        ],
      })

      return { editor }
    },
    render() {
      if (!this.editor) return h('div', 'Loading...')
      return h('div', {
        class: 'signing-test-container',
        innerHTML: '',
      })
    },
    mounted() {
      // Mount TipTap editor into the container
      const container = this.$el as HTMLElement
      container.innerHTML = ''
      const editorEl = document.createElement('div')
      container.appendChild(editorEl)
      this.editor.setOptions({ element: editorEl })
    },
    unmounted() {
      this.editor?.destroy()
    },
  })

  return render(WrapperComponent)
}

/**
 * Simpler approach: mount the full editor via EditorContent and provide context.
 */
function renderWithEditorContent(opts: {
  fieldName: string
  fieldType: 'signature' | 'initials' | 'date'
  signerRole: string
  signingContext: SigningContext
}) {
  const { fieldName, fieldType, signerRole, signingContext } = opts

  const doc = {
    type: 'doc',
    content: [
      {
        type: 'paragraph',
        content: [
          {
            type: 'signatureBlock',
            attrs: { fieldName, fieldType, signerRole, label: '' },
          },
        ],
      },
    ],
  }

  // Use a component that creates the editor and renders via EditorContent
  const TestComponent = defineComponent({
    name: 'EditorContentTest',
    components: { EditorContent },
    setup() {
      provide('signingContext', signingContext)

      const editor = new Editor({
        content: doc,
        editable: false,
        extensions: [
          StarterKit,
          SignatureBlock,
        ],
      })

      return { editor }
    },
    render() {
      return h('div', { class: 'editor-mount' }, [
        h(EditorContent, { editor: this.editor }),
      ])
    },
    unmounted() {
      this.editor?.destroy()
    },
  })

  return render(TestComponent)
}

// ── Tests: Date field for matching signer ─────────────────────────────

describe('SignatureBlock — Signing Mode: Date Field', () => {

  it('date field for matching role shows today\'s date', async () => {
    const signingContext: SigningContext = {
      signerRole: 'tenant_1',
      signedFields: new Map(),
      alreadySigned: [],
      onFieldClick: vi.fn(),
    }

    const screen = renderWithEditorContent({
      fieldName: 'tenant_1_date_signed',
      fieldType: 'date',
      signerRole: 'tenant_1',
      signingContext,
    })

    // Wait for TipTap to initialise and Vue node views to mount
    await new Promise(r => setTimeout(r, 2000))

    const container = document.querySelector('.editor-mount') as HTMLElement
    expect(container).not.toBeNull()

    // The date field should show today's formatted date (e.g. "5 April 2026")
    const today = new Date().toLocaleDateString('en-ZA', {
      day: 'numeric', month: 'long', year: 'numeric',
    })

    // Find the date display — green background chip with calendar icon
    const dateEl = container.querySelector('[data-field-name="tenant_1_date_signed"]')
    expect(dateEl).not.toBeNull()

    // The rendered text should contain today's date
    const textContent = dateEl!.textContent || ''
    expect(textContent).toContain(today)

    // It should NOT show "Pending" or "Click to"
    expect(textContent).not.toContain('Pending')
    expect(textContent).not.toContain('Click to')

    screen.unmount()
  })
})

// ── Tests: Signature field unsigned ───────────────────────────────────

describe('SignatureBlock — Signing Mode: Unsigned Signature', () => {

  it('shows "Click to Sign" button when unsigned', async () => {
    const onFieldClick = vi.fn()
    const signingContext: SigningContext = {
      signerRole: 'landlord',
      signedFields: new Map(),
      alreadySigned: [],
      onFieldClick,
    }

    const screen = renderWithEditorContent({
      fieldName: 'landlord_signature',
      fieldType: 'signature',
      signerRole: 'landlord',
      signingContext,
    })

    await new Promise(r => setTimeout(r, 2000))

    const container = document.querySelector('.editor-mount') as HTMLElement
    expect(container).not.toBeNull()

    const fieldEl = container.querySelector('[data-field-name="landlord_signature"]')
    expect(fieldEl).not.toBeNull()

    // Should contain a "Click to Sign" button
    const button = fieldEl!.querySelector('button')
    expect(button).not.toBeNull()
    expect(button!.textContent).toContain('Click to Sign')

    // The button should have the animate-pulse-subtle class
    expect(button!.classList.contains('animate-pulse-subtle')).toBe(true)

    screen.unmount()
  })

  it('clicking the sign button triggers onFieldClick callback', async () => {
    const onFieldClick = vi.fn()
    const signingContext: SigningContext = {
      signerRole: 'landlord',
      signedFields: new Map(),
      alreadySigned: [],
      onFieldClick,
    }

    const screen = renderWithEditorContent({
      fieldName: 'landlord_signature',
      fieldType: 'signature',
      signerRole: 'landlord',
      signingContext,
    })

    await new Promise(r => setTimeout(r, 2000))

    const container = document.querySelector('.editor-mount') as HTMLElement
    const button = container.querySelector('[data-field-name="landlord_signature"] button') as HTMLButtonElement
    expect(button).not.toBeNull()

    button.click()
    expect(onFieldClick).toHaveBeenCalledWith('landlord_signature', 'signature')

    screen.unmount()
  })
})

// ── Tests: Signature field signed ─────────────────────────────────────

describe('SignatureBlock — Signing Mode: Signed Signature', () => {

  it('shows green checkmark SVG when signed with image data', async () => {
    const signedFields = new Map([
      ['landlord_signature', {
        imageData: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==',
        signedAt: '2026-04-05T10:00:00Z',
      }],
    ])

    const signingContext: SigningContext = {
      signerRole: 'landlord',
      signedFields,
      alreadySigned: [],
      onFieldClick: vi.fn(),
    }

    const screen = renderWithEditorContent({
      fieldName: 'landlord_signature',
      fieldType: 'signature',
      signerRole: 'landlord',
      signingContext,
    })

    await new Promise(r => setTimeout(r, 2000))

    const container = document.querySelector('.editor-mount') as HTMLElement
    expect(container).not.toBeNull()

    const fieldEl = container.querySelector('[data-field-name="landlord_signature"]')
    expect(fieldEl).not.toBeNull()

    // Should show the signature image
    const img = fieldEl!.querySelector('img') as HTMLImageElement
    expect(img).not.toBeNull()
    expect(img.src).toContain('data:image/png')
    expect(img.alt).toBe('Signed')

    // Should show green checkmark SVG (path with "M5 13l4 4L19 7")
    const svg = fieldEl!.querySelector('svg')
    expect(svg).not.toBeNull()
    const path = svg!.querySelector('path')
    expect(path).not.toBeNull()
    expect(path!.getAttribute('d')).toContain('M5 13l4 4L19 7')

    // Should NOT show any button
    const button = fieldEl!.querySelector('button')
    expect(button).toBeNull()

    screen.unmount()
  })
})

// ── Tests: Other signer's pending field ───────────────────────────────

describe('SignatureBlock — Signing Mode: Other Signer Pending', () => {

  it('shows "Pending: Role Name" for another signer\'s unsigned field', async () => {
    const signingContext: SigningContext = {
      signerRole: 'tenant_1',  // current signer is tenant_1
      signedFields: new Map(),
      alreadySigned: [],
      onFieldClick: vi.fn(),
    }

    const screen = renderWithEditorContent({
      fieldName: 'landlord_signature',
      fieldType: 'signature',
      signerRole: 'landlord',  // field belongs to landlord
      signingContext,
    })

    await new Promise(r => setTimeout(r, 2000))

    const container = document.querySelector('.editor-mount') as HTMLElement
    expect(container).not.toBeNull()

    const fieldEl = container.querySelector('[data-field-name="landlord_signature"]')
    expect(fieldEl).not.toBeNull()

    const textContent = fieldEl!.textContent || ''
    expect(textContent).toContain('Pending')
    expect(textContent).toContain('Landlord')

    // Should NOT have a clickable button
    const button = fieldEl!.querySelector('button')
    expect(button).toBeNull()

    screen.unmount()
  })

  it('shows "Signed by" for other signer\'s completed field', async () => {
    const signingContext: SigningContext = {
      signerRole: 'tenant_1',
      signedFields: new Map(),
      alreadySigned: [
        {
          fieldName: 'landlord_signature',
          fieldType: 'signature',
          signerName: 'John Landlord',
          signedAt: '2026-04-04T15:00:00Z',
        },
      ],
      onFieldClick: vi.fn(),
    }

    const screen = renderWithEditorContent({
      fieldName: 'landlord_signature',
      fieldType: 'signature',
      signerRole: 'landlord',
      signingContext,
    })

    await new Promise(r => setTimeout(r, 2000))

    const container = document.querySelector('.editor-mount') as HTMLElement
    const fieldEl = container.querySelector('[data-field-name="landlord_signature"]')
    expect(fieldEl).not.toBeNull()

    const textContent = fieldEl!.textContent || ''
    expect(textContent).toContain('Signed by')
    expect(textContent).toContain('John Landlord')

    // Should show a green checkmark for the completed state
    const svg = fieldEl!.querySelector('svg')
    expect(svg).not.toBeNull()

    screen.unmount()
  })
})

// ── Tests: Initials compact styling ───────────────────────────────────

describe('SignatureBlock — Signing Mode: Initials Compact Styling', () => {

  it('unsigned initials button has compact styling (smaller than signature)', async () => {
    const signingContext: SigningContext = {
      signerRole: 'tenant_1',
      signedFields: new Map(),
      alreadySigned: [],
      onFieldClick: vi.fn(),
    }

    // Render signature field first to compare
    const sigScreen = renderWithEditorContent({
      fieldName: 'tenant_1_signature',
      fieldType: 'signature',
      signerRole: 'tenant_1',
      signingContext,
    })
    await new Promise(r => setTimeout(r, 2000))

    const sigContainer = document.querySelector('.editor-mount') as HTMLElement
    const sigButton = sigContainer.querySelector('[data-field-name="tenant_1_signature"] button') as HTMLElement

    // Get signature button dimensions
    const sigRect = sigButton?.getBoundingClientRect()
    sigScreen.unmount()

    await new Promise(r => setTimeout(r, 500))

    // Now render initials field
    const initScreen = renderWithEditorContent({
      fieldName: 'tenant_1_initials',
      fieldType: 'initials',
      signerRole: 'tenant_1',
      signingContext,
    })
    await new Promise(r => setTimeout(r, 2000))

    const initContainer = document.querySelector('.editor-mount') as HTMLElement
    const initButton = initContainer.querySelector('[data-field-name="tenant_1_initials"] button') as HTMLElement
    expect(initButton).not.toBeNull()

    // Initials button text should say "Click to Initial" (not "Click to Sign")
    expect(initButton.textContent).toContain('Click to Initial')

    // Initials button should have smaller styling classes
    // Check for compact class markers: text-[10px] and smaller padding
    expect(initButton.classList.contains('text-[10px]') || initButton.className.includes('text-[10px]')).toBe(true)

    // Initials button should be smaller than signature button
    const initRect = initButton.getBoundingClientRect()
    if (sigRect && sigRect.height > 0) {
      expect(initRect.height).toBeLessThan(sigRect.height)
    }

    initScreen.unmount()
  })

  it('signed initials shows compact image with max-h-[18px]', async () => {
    const signedFields = new Map([
      ['tenant_1_initials', {
        imageData: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==',
        signedAt: '2026-04-05T10:00:00Z',
      }],
    ])

    const signingContext: SigningContext = {
      signerRole: 'tenant_1',
      signedFields,
      alreadySigned: [],
      onFieldClick: vi.fn(),
    }

    const screen = renderWithEditorContent({
      fieldName: 'tenant_1_initials',
      fieldType: 'initials',
      signerRole: 'tenant_1',
      signingContext,
    })

    await new Promise(r => setTimeout(r, 2000))

    const container = document.querySelector('.editor-mount') as HTMLElement
    const fieldEl = container.querySelector('[data-field-name="tenant_1_initials"]')
    expect(fieldEl).not.toBeNull()

    // Should show the initials image
    const img = fieldEl!.querySelector('img') as HTMLImageElement
    expect(img).not.toBeNull()

    // Initials image should have compact height class
    expect(img.className).toContain('h-[14px]')
    expect(img.className).toContain('max-h-[14px]')

    // The container span should have compact padding (px-0.5)
    const parentSpan = img.closest('span')
    expect(parentSpan).not.toBeNull()
    expect(parentSpan!.className).toContain('max-h-[18px]')

    // Signed initials should NOT show the green checkmark SVG (isInitials hides it)
    const svgs = fieldEl!.querySelectorAll('svg')
    // The checkmark svg with "M5 13l4 4L19 7" should not be present for initials
    let hasCheckmark = false
    svgs.forEach(svg => {
      const path = svg.querySelector('path')
      if (path && path.getAttribute('d')?.includes('M5 13l4 4L19 7')) {
        hasCheckmark = true
      }
    })
    expect(hasCheckmark).toBe(false)

    screen.unmount()
  })
})
