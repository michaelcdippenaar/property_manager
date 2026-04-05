/**
 * useTiptapEditor — composable that creates a fully configured TipTap editor
 * for lease template editing, with all custom extensions.
 *
 * Usage:
 *   const { editor } = useTiptapEditor({ content: '<p>Hello</p>' })
 */
import { ref, watch, type Ref } from 'vue'
import { useEditor, type Editor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableCell } from '@tiptap/extension-table-cell'
import { TableHeader } from '@tiptap/extension-table-header'
import { TextAlign } from '@tiptap/extension-text-align'
import { Underline } from '@tiptap/extension-underline'
import { TextStyle } from '@tiptap/extension-text-style'
import { Color } from '@tiptap/extension-color'
import { Highlight } from '@tiptap/extension-highlight'
import { Placeholder } from '@tiptap/extension-placeholder'

import { PaginationPlus } from 'tiptap-pagination-plus'
import { PAGINATION_CONFIG } from '../config/tiptapSettings'
import { MergeField } from '../extensions/MergeFieldNode'
import { SignatureBlock } from '../extensions/SignatureBlockNode'
import { PageBreak } from '../extensions/PageBreakNode'
import { FontSize } from '../extensions/FontSize'

export interface TiptapEditorOptions {
  /** Initial HTML content */
  content?: string
  /** Placeholder text when editor is empty */
  placeholder?: string
  /** Whether the editor is editable */
  editable?: boolean
  /** Called on every content change (debounce externally if needed) */
  onUpdate?: (html: string, json: any) => void
}

export function useTiptapEditor(options: TiptapEditorOptions = {}) {
  const isDirty = ref(false)
  const wordCount = ref(0)

  const editor = useEditor({
    content: options.content || '',
    editable: options.editable !== false,
    editorProps: {
      handleDrop(view, event, _slice, moved) {
        // Only handle external drops (from panel), not internal ProseMirror moves
        if (moved) return false

        const mergeData = event.dataTransfer?.getData('application/tiptap-merge-field')
        const signingData = event.dataTransfer?.getData('application/tiptap-signing-field')

        if (!mergeData && !signingData) return false

        // Find drop position in the document
        const dropPos = view.posAtCoords({ left: event.clientX, top: event.clientY })
        if (!dropPos) return false

        event.preventDefault()

        if (mergeData) {
          const attrs = JSON.parse(mergeData)
          const node = view.state.schema.nodes.mergeField?.create(attrs)
          if (node) {
            const tr = view.state.tr.insert(dropPos.pos, node)
            view.dispatch(tr)
          }
          return true
        }

        if (signingData) {
          const attrs = JSON.parse(signingData)
          // Generate unique field name
          const fieldName = `${attrs.signerRole}_${attrs.fieldType}_${Date.now()}`
          const node = view.state.schema.nodes.signatureBlock?.create({ ...attrs, fieldName })
          if (node) {
            const tr = view.state.tr.insert(dropPos.pos, node)
            view.dispatch(tr)
          }
          return true
        }

        return false
      },
    },
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
      }),
      // Tables
      Table.configure({ resizable: true, cellMinWidth: 60, lastColumnResizable: true }),
      TableRow,
      TableCell,
      TableHeader,
      // Text formatting
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Underline,
      TextStyle,
      Color,
      Highlight.configure({ multicolor: true }),
      FontSize,
      Placeholder.configure({ placeholder: options.placeholder || 'Start editing your lease template...' }),
      // Pagination — Google Docs-style page breaks
      // Config from shared tiptapSettings.ts — single source of truth
      PaginationPlus.configure(PAGINATION_CONFIG),
      // Custom lease extensions
      MergeField,
      SignatureBlock,
      PageBreak,
    ],
    onUpdate: ({ editor: e }) => {
      isDirty.value = true
      wordCount.value = _countWords(e)
      options.onUpdate?.(e.getHTML(), e.getJSON())
    },
  })

  /** Reset dirty flag (e.g. after save) */
  function markClean() {
    isDirty.value = false
  }

  /** Replace editor content (e.g. after loading from backend) */
  function setContent(html: string) {
    editor.value?.commands.setContent(html)
    isDirty.value = false
  }

  /** Get clean HTML suitable for backend storage */
  function getHTML(): string {
    return editor.value?.getHTML() || ''
  }

  /** Get TipTap JSON for structured storage */
  function getJSON(): any {
    return editor.value?.getJSON() || null
  }

  return {
    editor,
    isDirty,
    wordCount,
    markClean,
    setContent,
    getHTML,
    getJSON,
  }
}

function _countWords(editor: Editor): number {
  const text = editor.state.doc.textContent || ''
  return text.split(/\s+/).filter(Boolean).length
}

export default useTiptapEditor
