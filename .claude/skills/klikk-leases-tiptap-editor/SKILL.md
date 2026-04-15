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

# TipTap Editor

TipTap is a headless ProseMirror-based rich-text editor framework — pure editor logic, no built-in UI. All rendering, menus, and toolbar are your responsibility.

**Key files:**
- Editor view: `admin/src/views/leases/TiptapEditorView.vue`
- Editor factory: `admin/src/composables/useTiptapEditor.ts`
- Custom extensions: `admin/src/extensions/`

---

## TipTap Core Concepts

**Always chain commands with `.focus()`** — commands fail silently without editor focus:
```typescript
editor.chain().focus().toggleBold().run()
editor.can().toggleBold()  // dry run
```

**Three extension types:**
- `Extension.create()` — functionality only, no schema (TextAlign, Placeholder)
- `Node.create()` — document content type (Heading, Table, MergeField)
- `Mark.create()` — text formatting (Bold, Link, FontSize)

**Output:**
```typescript
editor.getHTML()    // HTML string (from renderHTML(), NOT Vue node view)
editor.getJSON()    // ProseMirror JSON (preferred for lossless roundtrip)
editor.getText()    // plain text
```

**Document storage** — v2 JSON envelope in `LeaseTemplate.content_html`:
```json
{ "v": 2, "html": "...", "tiptapJson": {...}, "fields": [...] }
```
Always load from `tiptapJson` when present.

---

## Reference Index

| When you need... | File |
|-----------------|------|
| Editor setup, options, events, styling, menus | [editor-config.md](references/editor-config.md) |
| Commands (content, node, mark, list, selection, table) | [commands.md](references/commands.md) |
| Creating custom extensions, extending existing, TypeScript | [custom-extensions.md](references/custom-extensions.md) |
| Vue 3 node views (VueNodeViewRenderer, props, patterns) | [node-views-vue.md](references/node-views-vue.md) |
| StarterKit, Table, TextAlign, Color, Highlight, Placeholder, Image, DragHandle | [extensions-config.md](references/extensions-config.md) |
| MergeField, SignatureBlock, PageBreak, FontSize, PaginationPlus, v2 JSON envelope | [tremly-tiptap-extensions.md](references/tremly-tiptap-extensions.md) |
| Commands not working, drag-and-drop, infinite loops, content stripping | [troubleshooting.md](references/troubleshooting.md) |

---

## Extension Stack (Tremly)

```typescript
extensions: [
  StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
  Table.configure({ resizable: true, cellMinWidth: 60 }),
  TableRow, TableCell, TableHeader,
  TextAlign.configure({ types: ['heading', 'paragraph'] }),
  Underline, TextStyle, Color,
  Highlight.configure({ multicolor: true }),
  FontSize,
  Placeholder.configure({ placeholder: 'Start editing your lease template...' }),
  PaginationPlus.configure({ pageHeight: 1123, pageWidth: 794, pageGap: 40,
    marginTop: 48, marginBottom: 48, marginLeft: 56, marginRight: 56 }),
  MergeField, SignatureBlock, PageBreak,
]
```
