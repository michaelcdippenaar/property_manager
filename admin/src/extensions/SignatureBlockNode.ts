/**
 * SignatureBlock — inline atomic node for signing fields (signature, initials, date).
 *
 * Inline so multiple blocks can sit on the same line inside a paragraph.
 * Alignment is controlled by the parent paragraph's text-align (via TipTap TextAlign).
 *
 * Each instance gets a unique fieldName so multiple initials per party work correctly.
 *
 * HTML export:
 *   <span data-type="signature-block" data-field-type="initials" data-signer-role="landlord"
 *         data-field-name="landlord_initials_p2"
 *         style="display:inline-block;width:100px;height:40px;">
 *     {{landlord_initials_p2}}
 *   </span>
 */
import { Node, mergeAttributes } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import SignatureBlockComponent from './SignatureBlockComponent.vue'

export interface SignatureBlockAttributes {
  fieldName: string
  fieldType: 'signature' | 'initials' | 'date'
  signerRole: string    // landlord, tenant_1, tenant_2, witness, agent
  label: string | null
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    signatureBlock: {
      insertSignatureBlock: (attrs: Partial<SignatureBlockAttributes> & { fieldType: string; signerRole: string }) => ReturnType
    }
  }
}

let _blockCounter = Date.now() % 100000

export const SignatureBlock = Node.create({
  name: 'signatureBlock',
  group: 'inline',
  inline: true,
  atom: true,
  draggable: true,
  selectable: true,

  addAttributes() {
    return {
      fieldName: {
        default: null,
        parseHTML: (el: HTMLElement) => el.getAttribute('data-field-name'),
        renderHTML: (attrs: Record<string, any>) => ({ 'data-field-name': attrs.fieldName }),
      },
      fieldType: {
        default: 'signature',
        parseHTML: (el: HTMLElement) => el.getAttribute('data-field-type') || 'signature',
        renderHTML: (attrs: Record<string, any>) => ({ 'data-field-type': attrs.fieldType }),
      },
      signerRole: {
        default: 'landlord',
        parseHTML: (el: HTMLElement) => el.getAttribute('data-signer-role') || 'landlord',
        renderHTML: (attrs: Record<string, any>) => ({ 'data-signer-role': attrs.signerRole }),
      },
      label: {
        default: null,
        parseHTML: (el: HTMLElement) => el.getAttribute('data-label'),
        renderHTML: (attrs: Record<string, any>) => {
          if (attrs.label) return { 'data-label': attrs.label }
          return {}
        },
      },
    }
  },

  parseHTML() {
    return [
      // Native signing field tags (round-trip from renderHTML output)
      { tag: 'signature-field', getAttrs: (el: HTMLElement) => ({
        fieldName: el.getAttribute('name') || el.getAttribute('data-field-name'),
        fieldType: 'signature',
        signerRole: el.getAttribute('role') || el.getAttribute('data-signer-role') || 'landlord',
      })},
      { tag: 'initials-field', getAttrs: (el: HTMLElement) => ({
        fieldName: el.getAttribute('name') || el.getAttribute('data-field-name'),
        fieldType: 'initials',
        signerRole: el.getAttribute('role') || el.getAttribute('data-signer-role') || 'landlord',
      })},
      { tag: 'date-field', getAttrs: (el: HTMLElement) => ({
        fieldName: el.getAttribute('name') || el.getAttribute('data-field-name'),
        fieldType: 'date',
        signerRole: el.getAttribute('role') || el.getAttribute('data-signer-role') || 'landlord',
      })},
      // Legacy TipTap format (span)
      { tag: 'span[data-type="signature-block"]' },
      // Legacy TipTap format (div)
      { tag: 'div[data-type="signature-block"]' },
      // Legacy: block field divs from old editor
      { tag: 'div[data-field-type]', getAttrs: (el: HTMLElement) => {
        const type = el.getAttribute('data-field-type')
        if (type !== 'signature' && type !== 'initials') return false
        return {
          fieldName: el.getAttribute('data-field') || `${el.getAttribute('data-party') || 'unknown'}_${type}`,
          fieldType: type,
          signerRole: el.getAttribute('data-party') || 'landlord',
        }
      }},
    ]
  },

  renderHTML({ HTMLAttributes }) {
    const name = HTMLAttributes['data-field-name'] || ''
    const type = HTMLAttributes['data-field-type'] || 'signature'
    const role = HTMLAttributes['data-signer-role'] || 'landlord'

    // Map field type to signing field tag name
    const tagMap: Record<string, string> = {
      signature: 'signature-field',
      initials: 'initials-field',
      date: 'date-field',
    }
    const tag = tagMap[type] || 'signature-field'

    const dims = type === 'signature'
      ? 'width:200px;height:60px'
      : type === 'initials'
        ? 'width:100px;height:40px'
        : 'width:120px;height:24px'

    return [
      tag,
      mergeAttributes(
        {
          name,
          role,
          required: 'true',
          style: `display:inline-block;${dims};margin:4px 6px;vertical-align:middle;`,
          // Preserve TipTap attrs for round-tripping
          'data-field-type': type,
          'data-signer-role': role,
          'data-field-name': name,
        },
        type === 'signature' ? { format: 'drawn_or_typed' } : {},
      ),
      ' ',  // non-empty content required
    ]
  },

  addNodeView() {
    return VueNodeViewRenderer(SignatureBlockComponent)
  },

  addCommands() {
    return {
      insertSignatureBlock: (attrs) => ({ commands }) => {
        _blockCounter++
        const suffix = attrs.fieldType === 'date' ? 'date_signed' : attrs.fieldType
        const fieldName = attrs.fieldName || `${attrs.signerRole}_${suffix}_${_blockCounter}`
        return commands.insertContent({
          type: this.name,
          attrs: {
            ...attrs,
            fieldName,
            label: attrs.label || _makeLabel(attrs.fieldType, attrs.signerRole),
          },
        })
      },
    }
  },
})

function _makeLabel(type: string, role: string): string {
  const t = (type || 'signature').charAt(0).toUpperCase() + (type || 'signature').slice(1)
  const r = (role || 'Signer').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  return `${t} — ${r}`
}

export default SignatureBlock
