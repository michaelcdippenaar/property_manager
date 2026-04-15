# TipTap Troubleshooting

---

## Commands Not Working

Always chain with `.focus()` — commands fail silently without editor focus (e.g., after clicking a toolbar button):

```typescript
// WRONG
editor.value?.commands.insertSignatureBlock({ signerRole: 'landlord' })

// CORRECT
editor.value?.chain().focus().insertSignatureBlock({ signerRole: 'landlord' }).run()
```

---

## Extension Infinite Loop / Page Hang

Cause: ProseMirror plugin modifying the DOM → triggers update → triggers plugin again.

Fix: use CSS-only approaches or `requestAnimationFrame` with change detection to break the cycle.

---

## Drag-and-Drop Not Working

Both conditions are required:

1. `draggable: true` in the extension definition
2. `<node-view-wrapper :draggable="true" data-drag-handle>` in the Vue component

Missing either one breaks drag silently.

---

## Node Not Rendering as Vue Component

Checklist:
- `addNodeView()` must return `VueNodeViewRenderer(Component)`
- Component root element must be `<node-view-wrapper>`
- For inline nodes: `<node-view-wrapper as="span">`
- Import `NodeViewWrapper` from `@tiptap/vue-3`

---

## @tiptap/extension-font-size Doesn't Exist

No official TipTap package for this. Use the custom `FontSize` extension at `admin/src/extensions/FontSize.ts`.

---

## Build Error: "default" is not exported

TipTap uses named exports only:

```typescript
// WRONG
import Table from '@tiptap/extension-table'

// CORRECT
import { Table } from '@tiptap/extension-table'
```

---

## PaginationPlus Not Rendering

- Install: `npm install tiptap-pagination-plus`
- Requires concrete pixel values for `pageHeight` and `pageWidth`
- Import from `tiptap-pagination-plus` (not from the local extensions barrel)

---

## Content Stripped on Load

Cause: schema mismatch — loaded HTML/JSON contains nodes or marks not registered in extensions.

Fix: ensure all extensions used when content was created are still registered. Debug with:

```typescript
useEditor({
  enableContentCheck: true,
  onContentError({ editor, error, disableCollaboration }) {
    console.error('Content schema mismatch:', error)
  },
})
```

---

## Merge Field Not Appearing After Insert

The merge field chip only renders as a Vue node view in the editor — it does NOT appear in `editor.getHTML()`. The HTML output comes from `renderHTML()` in the extension definition, which produces `<span data-type="merge-field" data-field-name="...">`.

If the chip isn't showing in the editor, the node view may have failed to mount — check the browser console for Vue errors.

---

## Table Resizing Not Working

Requires `Table.configure({ resizable: true })` and the `@tiptap/extension-table` package ≥ 2.x. The `resizable` option is not available in v1.

---

## JSON Envelope Loading (v2)

Prefer loading from `tiptapJson` (lossless roundtrip) over `html`:

```typescript
const envelope = JSON.parse(template.content_html)
if (envelope.v === 2 && envelope.tiptapJson) {
  editor.commands.setContent(envelope.tiptapJson)
} else {
  editor.commands.setContent(envelope.html ?? envelope)
}
```
