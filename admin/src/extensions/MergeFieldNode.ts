/**
 * MergeField — inline atomic node for template merge fields like {{landlord_name}}.
 *
 * In the editor it renders as a coloured chip via the Vue component.
 * When exported to HTML (for lease generation) it becomes:
 *   <span data-type="merge-field" data-field-name="landlord_name">{{landlord_name}}</span>
 *
 * The backend regex `\{\{\s*(\w+)\s*\}\}` picks these up during lease HTML generation.
 */
import { Node, mergeAttributes } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import MergeFieldComponent from './MergeFieldComponent.vue'

export interface MergeFieldAttributes {
  fieldName: string
  /** Category for colour coding: landlord, tenant, property, lease, agent */
  category: string
  /** Human-readable label shown on the chip */
  label: string | null
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    mergeField: {
      insertMergeField: (attrs: Partial<MergeFieldAttributes> & { fieldName: string }) => ReturnType
    }
  }
}

export const MergeField = Node.create({
  name: 'mergeField',
  group: 'inline',
  inline: true,
  atom: true,
  selectable: true,
  draggable: true,

  addAttributes() {
    return {
      fieldName: {
        default: null,
        parseHTML: (el: HTMLElement) => el.getAttribute('data-field-name'),
        renderHTML: (attrs: Record<string, any>) => ({ 'data-field-name': attrs.fieldName }),
      },
      category: {
        default: 'general',
        parseHTML: (el: HTMLElement) => el.getAttribute('data-category') || _deriveCategory(el.getAttribute('data-field-name') || ''),
        renderHTML: (attrs: Record<string, any>) => ({ 'data-category': attrs.category }),
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
      // New TipTap format
      { tag: 'span[data-type="merge-field"]' },
      // Legacy format from old editor
      { tag: 'span[data-merge-field]', getAttrs: (el: HTMLElement) => ({
        fieldName: el.getAttribute('data-merge-field'),
        category: _deriveCategory(el.getAttribute('data-merge-field') || ''),
      })},
      { tag: 'span[data-field]', getAttrs: (el: HTMLElement) => {
        const name = el.getAttribute('data-field') || ''
        // Only match non-signing fields (signing fields are handled by SignatureBlock)
        const type = el.getAttribute('data-field-type')
        if (type === 'signature' || type === 'initials') return false
        return { fieldName: name, category: _deriveCategory(name) }
      }},
    ]
  },

  renderHTML({ HTMLAttributes }) {
    const name = HTMLAttributes['data-field-name'] || ''
    return [
      'span',
      mergeAttributes({ 'data-type': 'merge-field', class: 'merge-field' }, HTMLAttributes),
      `{{${name}}}`,
    ]
  },

  addNodeView() {
    return VueNodeViewRenderer(MergeFieldComponent)
  },

  addCommands() {
    return {
      insertMergeField: (attrs) => ({ commands }) => {
        return commands.insertContent({
          type: this.name,
          attrs: {
            ...attrs,
            category: attrs.category || _deriveCategory(attrs.fieldName),
            label: attrs.label || _humanLabel(attrs.fieldName),
          },
        })
      },
    }
  },
})

// ── Helpers ────────────────────────────────────────────────────────────────

function _deriveCategory(name: string): string {
  const n = name.toLowerCase()
  if (n.startsWith('landlord') || n.startsWith('lessor')) return 'landlord'
  if (n.startsWith('tenant') || n.startsWith('lessee') || n.startsWith('co_tenant') || n.startsWith('occupant')) return 'tenant'
  if (n.startsWith('property') || n.startsWith('unit') || n.startsWith('city') || n.startsWith('province')) return 'property'
  if (n.startsWith('lease') || n.startsWith('monthly') || n.startsWith('deposit') || n.startsWith('notice')
    || n.startsWith('water') || n.startsWith('electricity') || n.startsWith('max_') || n.startsWith('payment')) return 'lease'
  if (n.startsWith('agent')) return 'agent'
  return 'general'
}

function _humanLabel(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export default MergeField
