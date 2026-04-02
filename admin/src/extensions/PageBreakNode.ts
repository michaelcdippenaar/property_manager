/**
 * PageBreak — block node that renders as a visual page separator in the editor
 * and exports as a CSS page-break-after rule for PDF/print.
 */
import { Node, mergeAttributes } from '@tiptap/core'

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    pageBreak: {
      insertPageBreak: () => ReturnType
    }
  }
}

export const PageBreak = Node.create({
  name: 'pageBreak',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: false,

  parseHTML() {
    return [
      // Standard page break div
      { tag: 'div[data-page-break]' },
      { tag: 'div[style*="page-break"]' },
      // HR-style break
      { tag: 'hr.page-break' },
    ]
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'div',
      mergeAttributes(HTMLAttributes, {
        'data-page-break': 'true',
        style: 'page-break-after: always;',
      }),
    ]
  },

  addCommands() {
    return {
      insertPageBreak: () => ({ commands }) => {
        return commands.insertContent({ type: this.name })
      },
    }
  },
})

export default PageBreak
