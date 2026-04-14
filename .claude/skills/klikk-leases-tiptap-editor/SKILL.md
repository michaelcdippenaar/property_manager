---
name: klikk-leases-tiptap-editor
description: >
  TipTap rich-text editor expertise for the Tremly lease template editor. Built from the official
  TipTap open-source documentation. Use this skill when the user asks about TipTap editor
  configuration, custom extensions, node views, marks, ProseMirror plugins, editor commands,
  Vue 3 integration, content serialization (HTML/JSON), styling, drag-and-drop, inline/block nodes,
  schema configuration, or troubleshooting the lease template editor. Also trigger for: "editor",
  "TipTap", "rich text", "node view", "ProseMirror", "extension", "merge field", "signature block",
  "page break", "font size", "pagination", "toolbar", "editor content", "insert command",
  "parse HTML", "render HTML", "schema", "signing field", "drag field into editor",
  "tiptap-pagination-plus", "StarterKit", "table extension", or any question about how the TipTap
  editor works in this project. Even if the user just says "fix the editor" or "the merge field
  isn't working" — this is your skill.
---

# TipTap Editor — Complete Reference + Tremly Integration

You are an expert at TipTap, the open-source ProseMirror-based rich-text editor framework. This skill covers both the official TipTap API and the Tremly-specific lease template editor built with it.

TipTap is headless — it provides pure editor logic with no default UI or styling. All rendering, menus, and toolbar are your responsibility. This is a strength: you have full control.

## References

Read the relevant file when you need deep detail beyond what's in this file. Pick the one that matches the task — don't load all of them.

| When you need... | Read |
|---|---|
| Editor setup, options, events, styling, menus | [editor-config.md](references/editor-config.md) |
| Commands (content, node, mark, list, selection, table) | [commands.md](references/commands.md) |
| Creating custom extensions, extending existing ones, TypeScript | [custom-extensions.md](references/custom-extensions.md) |
| Vue 3 node views (VueNodeViewRenderer, props, patterns) | [node-views-vue.md](references/node-views-vue.md) |
| StarterKit, Table, TextAlign, Color, Highlight, Placeholder, Image, DragHandle config | [extensions-config.md](references/extensions-config.md) |
| Tremly custom extensions: MergeField, SignatureBlock, PageBreak, FontSize, PaginationPlus, v2 JSON envelope | [tremly-tiptap-extensions.md](references/tremly-tiptap-extensions.md) |

## TipTap Core Concepts

### Editor Lifecycle

```typescript
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'

const editor = useEditor({
  content: '<p>Hello</p>',
  extensions: [StarterKit],
  editable: true,
  autofocus: 'end',
  onUpdate({ editor }) {
    // content changed — save
  },
})
// useEditor handles destroy() automatically in Vue 3
```

### Commands — Always Chain with Focus

```typescript
// Single command
editor.commands.setBold()

// Chained (single transaction, single update event)
editor.chain().focus().toggleBold().run()

// Dry run — check without applying
editor.can().toggleBold()

// Inline logic in chain
editor.chain().focus().command(({ tr }) => {
  tr.insertText('text')
  return true
}).run()
```

The `.focus()` call is critical — without it, commands silently fail when the editor doesn't have focus (e.g., after clicking a toolbar button).

### Schema — Strict Content Model

TipTap enforces a strict schema. Content that doesn't match is silently removed. Every node defines:
- `group`: `'block'` or `'inline'`
- `content`: what children are allowed (`'inline*'`, `'block+'`, `'text*'`)
- `marks`: which marks can apply (`'_'` = all, `''` = none)
- `atom`: `true` = non-editable unit (no content hole)
- `draggable`, `selectable`, `inline`, `defining`, `isolating`

### Extensions — The Building Blocks

Three types:
- **Extension** (`Extension.create()`) — functionality only, no schema (e.g., TextAlign, Placeholder)
- **Node** (`Node.create()`) — content type in document tree (e.g., Heading, Table, Image)
- **Mark** (`Mark.create()`) — formatting on text (e.g., Bold, Link, TextStyle)

Every extension can: add attributes, add commands, add keyboard shortcuts, listen to events, add ProseMirror plugins, add input/paste rules.

### Output Formats

```typescript
const html = editor.getHTML()   // HTML string
const json = editor.getJSON()   // ProseMirror JSON
const text = editor.getText()   // Plain text

editor.commands.setContent(html) // or JSON
```

The node view (in-editor rendering) is independent from `renderHTML()` (output). The editor does NOT export the rendered Vue component — only the HTML from `renderHTML()`.

## Creating Custom Extensions

This is the pattern used for all Tremly custom extensions (MergeField, SignatureBlock, etc.):

### Custom Node with Vue NodeView

```typescript
// Extension file: MyNode.ts
import { Node, mergeAttributes } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import MyComponent from './MyComponent.vue'

export const MyNode = Node.create({
  name: 'myNode',
  group: 'block',        // or 'inline'
  atom: true,            // non-editable unit
  draggable: true,
  selectable: true,
  inline: false,

  addAttributes() {
    return {
      myAttr: {
        default: null,
        // How to write to HTML
        renderHTML: (attrs) => ({ 'data-my-attr': attrs.myAttr }),
        // How to read from HTML
        parseHTML: (el) => el.getAttribute('data-my-attr'),
      },
    }
  },

  // What HTML to recognize as this node
  parseHTML() {
    return [
      { tag: 'div[data-type="my-node"]' },
      // Support legacy formats too:
      { tag: 'div.legacy-class', getAttrs: (node) => node.classList.contains('legacy') && null },
    ]
  },

  // What HTML to output (independent of node view!)
  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes({ 'data-type': 'my-node' }, HTMLAttributes)]
    // Add 0 as last element for content hole: ['div', attrs, 0]
  },

  addCommands() {
    return {
      insertMyNode: (attrs) => ({ chain }) => {
        return chain().insertContent({ type: this.name, attrs }).run()
      },
    }
  },

  addKeyboardShortcuts() {
    return {
      'Mod-Shift-M': () => this.editor.commands.insertMyNode({ myAttr: 'value' }),
    }
  },

  // Vue component for in-editor rendering
  addNodeView() {
    return VueNodeViewRenderer(MyComponent)
  },
})
```

### Vue NodeView Component

```vue
<template>
  <node-view-wrapper as="span" :draggable="true" data-drag-handle>
    <span contenteditable="false" :class="selected ? 'ring-2 ring-blue-400' : ''">
      {{ node.attrs.myAttr }}
    </span>
  </node-view-wrapper>
</template>

<script setup lang="ts">
import { nodeViewProps, NodeViewWrapper } from '@tiptap/vue-3'
const props = defineProps(nodeViewProps)
// props.node          — current ProseMirror node
// props.editor        — editor instance
// props.selected      — is this node selected?
// props.updateAttributes(attrs)  — update node attributes
// props.deleteNode()  — remove this node
// props.getPos()      — document position
</script>
```

**Rules:**
- Root element MUST be `<node-view-wrapper>`
- For inline nodes: `<node-view-wrapper as="span">`
- For editable content inside: add `<node-view-content />` component
- For dragging: `draggable: true` on extension AND `data-drag-handle` on wrapper

### Extending Existing Extensions

```typescript
import { TableCell } from '@tiptap/extension-table-cell'

const CustomTableCell = TableCell.extend({
  addAttributes() {
    return {
      ...this.parent?.(),  // keep existing attributes
      backgroundColor: {
        default: null,
        renderHTML: (attrs) => attrs.backgroundColor
          ? { style: `background-color: ${attrs.backgroundColor}` }
          : {},
        parseHTML: (el) => el.style.backgroundColor || null,
      },
    }
  },
})
```

## Tremly Lease Editor Integration

### Architecture

| Layer | File | Purpose |
|-------|------|---------|
| Editor View | `admin/src/views/leases/TiptapEditorView.vue` | Three-panel: AI chat, editor, field palette |
| Composable | `admin/src/composables/useTiptapEditor.ts` | Editor factory with all extensions |
| MergeField | `admin/src/extensions/MergeFieldNode.ts` + `.vue` | Template variable chips |
| SignatureBlock | `admin/src/extensions/SignatureBlockNode.ts` + `.vue` | Signing field placeholders |
| PageBreak | `admin/src/extensions/PageBreakNode.ts` | Explicit page breaks |
| FontSize | `admin/src/extensions/FontSize.ts` | Custom fontSize on textStyle mark |

### Extension Stack

```typescript
extensions: [
  StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
  Table.configure({ resizable: true, cellMinWidth: 60, lastColumnResizable: true }),
  TableRow, TableCell, TableHeader,
  TextAlign.configure({ types: ['heading', 'paragraph'] }),
  Underline, TextStyle, Color,
  Highlight.configure({ multicolor: true }),
  FontSize,
  Placeholder.configure({ placeholder: 'Start editing your lease template...' }),
  PaginationPlus.configure({
    pageHeight: 1123, pageWidth: 794, pageGap: 40,
    marginTop: 48, marginBottom: 48, marginLeft: 56, marginRight: 56,
    footerRight: '{page}',
  }),
  MergeField, SignatureBlock, PageBreak,
]
```

### Document Storage (v2 JSON Envelope)

Templates are stored as a JSON envelope in `LeaseTemplate.content_html`:

```json
{
  "v": 2,
  "html": "<p>rendered HTML...</p>",
  "tiptapJson": { "type": "doc", "content": [...] },
  "fields": [{ "fieldName": "landlord_signature_1", "fieldType": "signature", "signerRole": "landlord" }]
}
```

- `tiptapJson` is preferred on load for lossless roundtrip
- `html` is used by the backend for merge field replacement and PDF generation
- `fields` is extracted metadata for field discovery

### Drag-and-Drop from Field Palette

The composable's `handleDrop` in `editorProps` intercepts drops from the palette:
- `application/tiptap-merge-field` → inserts `mergeField` node
- `application/tiptap-signing-field` → inserts `signatureBlock` node with unique name

The palette uses `@dragstart` + `event.dataTransfer.setData()`.

### MergeField Categories

| Prefix | Category | Color |
|--------|----------|-------|
| `landlord_`, `lessor_` | landlord | blue |
| `tenant_`, `lessee_`, `co_tenant_` | tenant | green |
| `property_`, `unit_`, `city_`, `province_` | property | amber |
| `lease_`, `monthly_`, `deposit_`, `notice_` | lease | purple |
| `agent_` | agent | cyan |

### SignatureBlock Field Types

| Type | Width | Height | DocuSeal Tag |
|------|-------|--------|-------------|
| signature | 200px | 60px | `<signature-field>` |
| initials | 100px | 40px | `<initials-field>` |
| date | 120px | 24px | `<date-field>` |

## Troubleshooting

### Commands not working
Always chain with `.focus()` — commands fail silently without focus:
```typescript
// WRONG
editor.value?.commands.insertSignatureBlock({ signerRole: 'landlord' })
// CORRECT
editor.value?.chain().focus().insertSignatureBlock({ signerRole: 'landlord' }).run()
```

### Extension infinite loop / page hang
ProseMirror plugin modifying DOM → triggers update → triggers plugin again. Fix: use CSS-only approaches or `requestAnimationFrame` with change detection.

### Drag-and-drop not working
Both required: `<node-view-wrapper :draggable="true" data-drag-handle>` AND `draggable: true` in extension definition.

### Node not rendering as Vue component
- `addNodeView()` must return `VueNodeViewRenderer(Component)`
- Component root must be `<node-view-wrapper>`
- For inline: `<node-view-wrapper as="span">`

### @tiptap/extension-font-size doesn't exist
No official package. Use our custom `FontSize` extension in `admin/src/extensions/FontSize.ts`.

### Build error: "default" is not exported
TipTap uses named exports: `import { Table } from '@tiptap/extension-table'` (not default import).

### PaginationPlus not rendering
- Install: `npm install tiptap-pagination-plus`
- Needs concrete pixel values for `pageHeight`/`pageWidth`
- Import from `tiptap-pagination-plus` (not local extensions barrel)

### Content stripped on load
Schema mismatch — the loaded HTML/JSON contains nodes or marks not registered in extensions. Ensure all extensions the content was created with are still registered. Enable `enableContentCheck: true` + `onContentError` to debug.
