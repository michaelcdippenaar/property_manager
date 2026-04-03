# TipTap API Reference (Open Source)

Complete reference for the open-source TipTap editor framework, built on ProseMirror.

## Table of Contents

1. [Installation & Setup](#installation--setup)
2. [Editor Configuration](#editor-configuration)
3. [Editor Methods & Properties](#editor-methods--properties)
4. [Commands](#commands)
5. [Extensions System](#extensions-system)
6. [Creating Custom Extensions](#creating-custom-extensions)
7. [Extending Existing Extensions](#extending-existing-extensions)
8. [Node Views](#node-views)
9. [Vue 3 Node Views](#vue-3-node-views)
10. [Schema](#schema)
11. [Events](#events)
12. [Marks](#marks)
13. [Nodes](#nodes)
14. [Styling](#styling)
15. [Menus](#menus)
16. [Output (JSON & HTML)](#output-json--html)
17. [TypeScript](#typescript)
18. [ProseMirror Integration](#prosemirror-integration)
19. [StarterKit](#starterkit)
20. [Extension Reference](#extension-reference)

---

## Installation & Setup

### Vue 3

```bash
npm install @tiptap/vue-3 @tiptap/pm @tiptap/starter-kit
```

```vue
<template>
  <editor-content :editor="editor" />
</template>

<script setup>
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'

const editor = useEditor({
  content: '<p>Hello World</p>',
  extensions: [StarterKit],
})
</script>
```

`useEditor` handles lifecycle automatically — no manual `destroy()` needed.

### Vanilla JavaScript

```javascript
import { Editor } from '@tiptap/core'
import Document from '@tiptap/extension-document'
import Paragraph from '@tiptap/extension-paragraph'
import Text from '@tiptap/extension-text'

new Editor({
  element: document.querySelector('.element'),
  extensions: [Document, Paragraph, Text],
  content: '<p>Example Text</p>',
})
```

---

## Editor Configuration

| Option | Type | Description |
|--------|------|-------------|
| `element` | HTMLElement/null | DOM mount target (not required for Vue/React) |
| `extensions` | Extension[] | Required extensions array |
| `content` | string/JSON | Initial content (HTML or JSON) |
| `editable` | boolean | Read/write mode (default: true) |
| `autofocus` | 'start'/'end'/'all'/number/boolean/null | Initial cursor position |
| `textDirection` | 'ltr'/'rtl'/'auto'/undefined | Text direction |
| `enableInputRules` | boolean/Extension[] | Input rules toggle |
| `enablePasteRules` | boolean/Extension[] | Paste rules toggle |
| `injectCSS` | boolean | Default CSS injection (default: true) |
| `injectNonce` | string | CSP nonce for dynamic elements |
| `editorProps` | EditorProps | ProseMirror EditorProps passthrough |
| `parseOptions` | ParseOptions | ProseMirror ParseOptions passthrough |
| `enableContentCheck` | boolean | Validate content against schema |

### Configure extensions

```javascript
new Editor({
  extensions: [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
      undoRedo: false, // disable specific extension
    }),
    Strike, // add extra extensions alongside StarterKit
  ],
})
```

---

## Editor Methods & Properties

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `can()` | object | Check if a command can execute without running it |
| `chain()` | ChainedCommands | Create command chains |
| `destroy()` | void | Stop editor and unbind events |
| `getHTML()` | string | Current document as HTML |
| `getJSON()` | object | Current document as JSON |
| `getText()` | string | Plain text (optional blockSeparator, textSerializers) |
| `getAttributes(name)` | object | Attributes of selected node or mark |
| `isActive(name, attrs?)` | boolean | Whether node/mark is active |
| `mount(element)` | void | Attach editor to DOM element |
| `unmount()` | void | Detach from current element |
| `registerPlugin(plugin)` | void | Register ProseMirror plugin |
| `unregisterPlugin(name)` | void | Remove ProseMirror plugin |
| `setOptions(options)` | void | Update options after init |
| `setEditable(editable)` | void | Change editable state |
| `$node(name, attrs?)` | NodePos | Reference NodePos for positioning |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `isEditable` | boolean | Editor is editable |
| `isEmpty` | boolean | No content |
| `isFocused` | boolean | Has focus |
| `isDestroyed` | boolean | Instance destroyed |
| `isCapturingTransaction` | boolean | Capturing transaction |
| `schema` | Schema | ProseMirror schema |
| `state` | EditorState | ProseMirror state |
| `view` | EditorView | ProseMirror view |
| `storage` | Record | Extension storage access |

---

## Commands

### Execute commands

```javascript
// Single command
editor.commands.setBold()

// Chained commands (single transaction, single update event)
editor.chain().focus().toggleBold().run()

// Dry run — check without applying
editor.can().toggleBold()
editor.can().chain().toggleBold().toggleItalic().run()
```

### Inline commands in chains

```javascript
editor.chain().focus().command(({ tr }) => {
  tr.insertText('inserted text')
  return true
}).run()
```

### Try first successful command

```javascript
editor.commands.first(({ commands }) => [
  () => commands.undoInputRule(),
  () => commands.deleteSelection(),
])
```

### Content Commands

| Command | Description |
|---------|-------------|
| `clearContent()` | Clear whole document |
| `insertContent(value)` | Insert node or HTML at current position |
| `insertContentAt(pos, value)` | Insert at specific position |
| `setContent(value)` | Replace whole document |

### Node & Mark Commands

| Command | Description |
|---------|-------------|
| `clearNodes()` | Normalize nodes to paragraph |
| `createParagraphNear()` | Create paragraph nearby |
| `deleteNode(name)` | Delete a node |
| `extendMarkRange(name)` | Extend selection to mark |
| `exitCode()` | Exit code block |
| `joinBackward()` / `joinForward()` | Join nodes |
| `lift(name)` | Remove wrap |
| `liftEmptyBlock()` | Lift empty block |
| `resetAttributes(name, attrs)` | Reset to defaults |
| `setMark(name, attrs)` | Add mark |
| `setNode(name, attrs)` | Replace with node |
| `splitBlock()` | Fork new node |
| `toggleMark(name, attrs)` | Toggle mark |
| `toggleNode(name, toggle, attrs)` | Toggle between nodes |
| `toggleWrap(name)` | Wrap/unwrap |
| `undoInputRule()` | Undo input rule |
| `unsetAllMarks()` | Remove all marks |
| `unsetMark(name)` | Remove specific mark |
| `updateAttributes(name, attrs)` | Update node/mark attributes |

### List Commands

| Command | Description |
|---------|-------------|
| `liftListItem(name)` | Lift into wrapping list |
| `sinkListItem(name)` | Sink into inner list |
| `splitListItem(name)` | Split list item |
| `toggleList(name, itemName)` | Toggle list type |
| `wrapInList(name)` | Wrap in list |

### Selection Commands

| Command | Description |
|---------|-------------|
| `blur()` | Remove focus |
| `deleteRange(range)` | Delete range |
| `deleteSelection()` | Delete selection |
| `enter()` | Trigger enter |
| `focus(position?)` | Focus at position |
| `keyboardShortcut(shortcut)` | Trigger shortcut |
| `scrollIntoView()` | Scroll selection into view |
| `selectAll()` | Select whole document |
| `selectNodeBackward()` / `selectNodeForward()` | Select adjacent node |
| `selectParentNode()` | Select parent |
| `setNodeSelection(pos)` | Create NodeSelection |
| `setTextSelection(pos)` | Create TextSelection |

### Transaction mapping in chained commands

When chaining commands that modify the document, positions shift. Use `tr.mapping.map(pos)`:

```javascript
addCommands() {
  return {
    delete: () => ({ tr }) => {
      const from = tr.mapping.map(tr.selection.$from.pos)
      const to = tr.mapping.map(tr.selection.$to.pos)
      tr.delete(from, to)
      return true
    },
  }
}
```

### Custom commands with dispatch check

For commands to work with `.can()`, check `dispatch`:

```javascript
export default (value) => ({ tr, dispatch }) => {
  if (dispatch) {
    tr.insertText(value)
  }
  return true
}
```

---

## Extensions System

Extensions are the fundamental building blocks. They can:

- Add content types (nodes, marks)
- Add attributes to nodes/marks
- Apply global attributes across multiple types
- Add commands for custom actions
- Listen to events (focus, blur, update)
- Add keyboard shortcuts
- Add ProseMirror plugins
- Add input rules and paste rules

### Three types

| Type | Import | Purpose |
|------|--------|---------|
| `Extension` | `@tiptap/core` | Functionality only, no schema |
| `Node` | `@tiptap/core` | Content types in the document tree |
| `Mark` | `@tiptap/core` | Formatting applied to text |

---

## Creating Custom Extensions

### Extension (functionality, no schema)

```javascript
import { Extension } from '@tiptap/core'

const CustomExtension = Extension.create({
  name: 'customExtension',

  addOptions() {
    return { myOption: 'default' }
  },

  addStorage() {
    return { count: 0 }
  },

  addGlobalAttributes() {
    return [{
      types: ['heading', 'paragraph'],
      attributes: {
        textAlign: {
          default: 'left',
          renderHTML: (attrs) => ({ style: `text-align: ${attrs.textAlign}` }),
          parseHTML: (el) => el.style.textAlign || 'left',
        },
      },
    }]
  },

  addCommands() {
    return {
      myCommand: (param) => ({ commands }) => {
        return commands.insertContent(param)
      },
    }
  },

  addKeyboardShortcuts() {
    return {
      'Mod-Shift-X': () => this.editor.commands.myCommand('x'),
    }
  },
})
```

### Node (content type)

```javascript
import { Node, mergeAttributes } from '@tiptap/core'

const CustomNode = Node.create({
  name: 'customNode',
  group: 'block',         // or 'inline'
  content: 'inline*',     // or 'block+', 'text*', etc.
  atom: true,             // non-editable unit (no content hole)
  draggable: true,
  selectable: true,
  inline: false,          // true for inline nodes
  defining: true,         // prevents removal during replace

  addAttributes() {
    return {
      myAttr: {
        default: null,
        renderHTML: (attrs) => ({ 'data-my-attr': attrs.myAttr }),
        parseHTML: (el) => el.getAttribute('data-my-attr'),
      },
    }
  },

  parseHTML() {
    return [
      { tag: 'div[data-type="custom"]' },
      { tag: 'div', getAttrs: (node) => node.classList.contains('custom') && null },
      { style: 'display', getAttrs: (value) => value === 'block' && null },
    ]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes({ 'data-type': 'custom' }, HTMLAttributes), 0]
    // 0 = content hole. Omit for atom nodes.
  },

  addCommands() {
    return {
      insertCustomNode: (attrs) => ({ chain }) => {
        return chain().insertContent({ type: this.name, attrs }).run()
      },
    }
  },
})
```

### Mark (formatting)

```javascript
import { Mark, mergeAttributes } from '@tiptap/core'

const CustomMark = Mark.create({
  name: 'customMark',
  inclusive: true,     // false = mark doesn't stick at boundary
  excludes: '',        // marks that can't coexist
  exitable: false,     // true = cursor can leave mark at node end
  spanning: true,      // false = can't span multiple nodes

  addAttributes() {
    return {
      color: {
        default: null,
        renderHTML: (attrs) => ({ style: `color: ${attrs.color}` }),
        parseHTML: (el) => el.style.color,
      },
    }
  },

  parseHTML() {
    return [{ tag: 'span[data-custom-mark]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['span', mergeAttributes({ 'data-custom-mark': '' }, HTMLAttributes), 0]
  },

  addCommands() {
    return {
      setCustomMark: (attrs) => ({ commands }) => commands.setMark(this.name, attrs),
      toggleCustomMark: (attrs) => ({ commands }) => commands.toggleMark(this.name, attrs),
      unsetCustomMark: () => ({ commands }) => commands.unsetMark(this.name),
    }
  },
})
```

### Callback function pattern

```javascript
const CustomExtension = Extension.create(() => {
  let internalState = 0
  return {
    name: 'custom',
    onUpdate() { internalState++ },
  }
})
```

---

## Extending Existing Extensions

Every extension has an `.extend()` method:

```javascript
import Heading from '@tiptap/extension-heading'

const CustomHeading = Heading.extend({
  // Override settings
  addOptions() {
    return { ...this.parent?.(), levels: [1, 2, 3] }
  },

  // Add/modify attributes
  addAttributes() {
    return {
      ...this.parent?.(),
      customId: { default: null },
    }
  },

  // Override schema
  content: 'inline*',

  // Override rendering
  renderHTML({ HTMLAttributes }) {
    return ['h' + this.options.levels[0], mergeAttributes(HTMLAttributes), 0]
  },

  // Override parsing
  parseHTML() {
    return this.options.levels.map(level => ({
      tag: `h${level}`,
      attrs: { level },
    }))
  },

  // Add/override keyboard shortcuts
  addKeyboardShortcuts() {
    return {
      'Mod-l': () => this.editor.commands.toggleBulletList(),
    }
  },

  // Add/override commands
  addCommands() {
    return {
      ...this.parent?.(),
      customCommand: () => ({ commands }) => { /* ... */ },
    }
  },
})
```

### Storage (mutable data)

```javascript
const CustomExtension = Extension.create({
  name: 'custom',
  addStorage() {
    return { awesomeness: 100 }
  },
  onUpdate() {
    this.storage.awesomeness += 1
  },
})
// Access: editor.storage.custom.awesomeness
```

### Global attributes

Apply attributes across multiple extension types:

```javascript
addGlobalAttributes() {
  return [{
    types: ['heading', 'paragraph'],  // or '*', 'nodes', 'marks'
    attributes: {
      textAlign: {
        default: 'left',
        renderHTML: (attrs) => ({ style: `text-align: ${attrs.textAlign}` }),
        parseHTML: (el) => el.style.textAlign || 'left',
      },
    },
  }]
}
```

---

## Node Views

Node views let you add interactive, fully custom nodes with complete control over in-editor experience AND output rendering (they're independent).

### Three types

1. **Editable text** — cursor enters, standard commands work (e.g., TaskItem)
2. **Non-editable text** — `contenteditable="false"` applied automatically
3. **Mixed content** — combine editable and non-editable sections

### Important: Markup vs. Node View

The node view controls the **in-editor experience**. The `renderHTML()` method controls the **HTML output**. These are independent — the editor does NOT export the rendered JavaScript node view.

---

## Vue 3 Node Views

### Setup pattern

```javascript
import { Node } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import Component from './Component.vue'

export default Node.create({
  name: 'myNode',
  group: 'block',
  atom: true,
  draggable: true,

  addAttributes() {
    return { count: { default: 0 } }
  },

  parseHTML() {
    return [{ tag: 'div[data-type="my-node"]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes({ 'data-type': 'my-node' }, HTMLAttributes)]
  },

  addNodeView() {
    return VueNodeViewRenderer(Component)
  },
})
```

### Vue component

```vue
<template>
  <node-view-wrapper as="div" :draggable="true" data-drag-handle>
    <span contenteditable="false">
      Count: {{ node.attrs.count }}
    </span>
    <button @click="increment">+</button>
    <!-- For editable content inside the node: -->
    <node-view-content as="p" />
  </node-view-wrapper>
</template>

<script setup lang="ts">
import { nodeViewProps, NodeViewWrapper, NodeViewContent } from '@tiptap/vue-3'

const props = defineProps(nodeViewProps)

function increment() {
  props.updateAttributes({ count: props.node.attrs.count + 1 })
}
</script>
```

### Available props

| Prop | Type | Description |
|------|------|-------------|
| `editor` | Editor | Editor instance |
| `node` | ProseMirrorNode | Current node (access `node.attrs`) |
| `decorations` | Decoration[] | Applied decorations |
| `selected` | boolean | Whether node is selected (NodeSelection) |
| `extension` | Extension | Node extension access |
| `getPos()` | () => number | Document position |
| `updateAttributes(attrs)` | function | Update node attributes |
| `deleteNode()` | function | Delete this node |

### Rules

- **Must** wrap in `<node-view-wrapper>` as root element
- For inline nodes, use `<node-view-wrapper as="span">`
- `<node-view-content>` renders editable child content (for non-atom nodes)
- Both wrapper and content render `<div>` by default; use `as` prop to change
- For dragging: set `draggable: true` in extension AND add `data-drag-handle` to wrapper

---

## Schema

The schema defines document structure strictly. Content not matching the schema is removed.

### Node configuration

| Property | Description | Example |
|----------|-------------|---------|
| `content` | Allowed child content | `'block+'`, `'inline*'`, `'(paragraph\|list?)+'` |
| `marks` | Allowed marks | `'bold'`, `'_'` (all), `''` (none) |
| `group` | Node group | `'block'`, `'inline'` |
| `inline` | Render inline | `true` / `false` |
| `atom` | Single non-editable unit | `true` / `false` |
| `selectable` | Node selection available | `true` / `false` |
| `draggable` | Drag-and-drop | `true` / `false` |
| `code` | Code content behavior | `true` / `false` |
| `whitespace` | Whitespace handling | `'pre'` preserves |
| `defining` | Prevents removal on replace | `true` / `false` |
| `isolating` | Fences cursor | `true` / `false` |
| `allowGapCursor` | Gap cursor at boundaries | `true` / `false` |
| `tableRole` | Table element role | `'table'`, `'row'`, `'cell'`, `'header_cell'` |

### Mark configuration

| Property | Description |
|----------|-------------|
| `inclusive` | Mark stays active at boundary (default: true) |
| `excludes` | Marks that can't coexist |
| `exitable` | Cursor can leave mark at node end |
| `group` | Mark group |
| `code` | Code mark behavior |
| `spanning` | Can span multiple nodes |

### Access schema

```javascript
// With editor
const schema = editor.schema

// Without editor
import { getSchema } from '@tiptap/core'
const schema = getSchema([Document, Paragraph, Text])
```

---

## Events

| Event | Description | Callback params |
|-------|-------------|-----------------|
| `beforeCreate` | Before view is created | `{ editor }` |
| `create` | Editor fully initialized | `{ editor }` |
| `update` | Content changed | `{ editor }` |
| `selectionUpdate` | Selection changed | `{ editor }` |
| `transaction` | State changed | `{ editor, transaction }` |
| `focus` | Editor gained focus | `{ editor, event }` |
| `blur` | Editor lost focus | `{ editor, event }` |
| `destroy` | Editor being destroyed | — |
| `paste` | Content pasted | `{ event, slice }` |
| `drop` | Content dropped | `{ event, slice, moved }` |
| `delete` | Content deleted | `{ type, deletedRange, newRange, partial, node, mark }` |
| `contentError` | Content doesn't match schema | `{ editor, error, disableCollaboration }` |

### Three ways to register

```javascript
// 1. Configuration
new Editor({
  onUpdate({ editor }) { /* ... */ },
  onFocus({ editor, event }) { /* ... */ },
})

// 2. Binding
editor.on('update', ({ editor }) => { /* ... */ })
editor.off('update', handler) // unbind

// 3. Inside extensions
Extension.create({
  onUpdate({ editor }) { /* ... */ },
  onFocus({ editor, event }) { /* ... */ },
})
```

---

## Marks

### Available mark extensions (open source)

| Mark | Tag | Description |
|------|-----|-------------|
| Bold | `<strong>` | Bold text. Shortcut: `Ctrl/Cmd+B` |
| Code | `<code>` | Inline code |
| Highlight | `<mark>` | Text highlight, supports multicolor |
| Italic | `<em>` | Italic text. Shortcut: `Ctrl/Cmd+I` |
| Link | `<a>` | Hyperlinks |
| Strike | `<s>` | Strikethrough. Shortcut: `Ctrl/Cmd+Shift+S` |
| Subscript | `<sub>` | Subscript text |
| Superscript | `<sup>` | Superscript text |
| TextStyle | `<span>` | Foundation for styling (Color, FontFamily) |
| Underline | `<u>` | Underline text. Shortcut: `Ctrl/Cmd+U` |

### Common mark commands pattern

```javascript
editor.commands.setBold()      // apply
editor.commands.toggleBold()   // toggle
editor.commands.unsetBold()    // remove
editor.isActive('bold')        // check state
```

---

## Nodes

### Available node extensions (open source)

| Node | Tag | Description |
|------|-----|-------------|
| Document | — | Root node (topNode), required |
| Paragraph | `<p>` | Basic paragraph, required |
| Text | — | Inline text node, required |
| Heading | `<h1>`-`<h6>` | Headings. Input: `#`, `##`, etc. |
| BulletList | `<ul>` | Bullet list. Input: `*`, `-`, `+` |
| OrderedList | `<ol>` | Numbered list. Input: `1.` |
| ListItem | `<li>` | List item |
| Blockquote | `<blockquote>` | Block quote. Input: `>` |
| CodeBlock | `<pre><code>` | Code block |
| HardBreak | `<br>` | Line break. Shortcut: `Shift+Enter` |
| HorizontalRule | `<hr>` | Horizontal rule. Input: `---` |
| Image | `<img>` | Images (block or inline) |
| Table | `<table>` | Tables with resizable columns |
| TableRow | `<tr>` | Table row |
| TableCell | `<td>` | Table cell |
| TableHeader | `<th>` | Table header cell |
| TaskList | `<ul>` | Checkbox list |
| TaskItem | `<li>` | Checkbox item |
| Mention | — | @mentions (inline) |

### Table commands

```javascript
editor.commands.insertTable({ rows: 3, cols: 3, withHeaderRow: true })
editor.commands.addColumnBefore()
editor.commands.addColumnAfter()
editor.commands.deleteColumn()
editor.commands.addRowBefore()
editor.commands.addRowAfter()
editor.commands.deleteRow()
editor.commands.deleteTable()
editor.commands.mergeCells()
editor.commands.splitCell()
editor.commands.toggleHeaderRow()
editor.commands.toggleHeaderColumn()
editor.commands.toggleHeaderCell()
editor.commands.setCellAttribute(name, value)
editor.commands.fixTables()
```

---

## Styling

TipTap is headless — no default styles. The editor renders inside `.tiptap` class.

### Basic CSS

```css
.tiptap p { margin: 1em 0; }
.tiptap h1 { font-size: 2em; }
```

### CSS Modules — use `:global()`

```css
:global(.tiptap) p { margin: 1em 0; }
```

### Add classes via extensions

```javascript
Paragraph.configure({
  HTMLAttributes: { class: 'my-paragraph' },
})
```

### Add classes via editorProps

```javascript
new Editor({
  editorProps: {
    attributes: {
      class: 'prose prose-sm focus:outline-none',
    },
  },
})
```

### Customize HTML output

```javascript
const CustomBold = Bold.extend({
  renderHTML({ HTMLAttributes }) {
    return ['b', HTMLAttributes, 0] // <b> instead of <strong>
  },
})
```

### Tailwind CSS

```css
.tiptap {
  p { @apply my-4 first:mt-0 last:mb-0 text-base leading-relaxed; }
  h1 { @apply text-3xl font-bold mt-8 mb-4; }
}
```

---

## Menus

### Menu types

- **Fixed menu** — permanently positioned (toolbar above editor)
- **Bubble menu** — appears on text selection
- **Floating menu** — appears on empty lines
- **Slash commands** — type `/` for popup menu

### Button pattern

```javascript
// In template: @click handler
editor.chain().focus().toggleBold().run()

// Active state for button highlighting
editor.isActive('bold')
editor.isActive('heading', { level: 2 })
editor.isActive('highlight', { color: '#ffa8a8' })
editor.isActive('textStyle', { color: /.*/ }) // regex match
```

Always include `.focus()` in button handlers to restore editor focus.

---

## Output (JSON & HTML)

### Get content

```javascript
const html = editor.getHTML()
const json = editor.getJSON()
const text = editor.getText()
```

### Set content

```javascript
editor.commands.setContent('<p>New HTML content</p>')
editor.commands.setContent({ type: 'doc', content: [...] })
```

### Listen for changes

```javascript
new Editor({
  onUpdate({ editor }) {
    const html = editor.getHTML()
    const json = editor.getJSON()
    // save to backend
  },
})
```

### Server-side HTML generation from JSON

```javascript
import { generateHTML } from '@tiptap/html'
import StarterKit from '@tiptap/starter-kit'

const html = generateHTML(jsonContent, [StarterKit])
```

### Static renderer (no editor instance needed)

```javascript
import { renderToHTMLString } from '@tiptap/static-renderer'
// Convert ProseMirror JSON to HTML, React elements, or Markdown
```

---

## TypeScript

### Options types

```typescript
export interface CustomExtensionOptions {
  awesomeness: number
}

const CustomExtension = Extension.create<CustomExtensionOptions>({
  addOptions() {
    return { awesomeness: 100 }
  },
})
```

### Storage types

```typescript
export interface CustomExtensionStorage {
  count: number
}

declare module '@tiptap/core' {
  interface Storage {
    customExtension: CustomExtensionStorage
  }
}

const CustomExtension = Extension.create<{}, CustomExtensionStorage>({
  name: 'customExtension',
  addStorage() {
    return { count: 0 }
  },
})
```

### Command types

```typescript
declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    customExtension: {
      yourCommand: (someProp: any) => ReturnType
    }
  }
}
```

---

## ProseMirror Integration

Access ProseMirror internals via `@tiptap/pm`:

```javascript
import { EditorState } from '@tiptap/pm/state'
import { EditorView } from '@tiptap/pm/view'
import { Schema, Node as ProseMirrorNode } from '@tiptap/pm/model'
import { Plugin } from '@tiptap/pm/state'
```

### Available packages

`@tiptap/pm/state`, `@tiptap/pm/view`, `@tiptap/pm/model`, `@tiptap/pm/transform`,
`@tiptap/pm/commands`, `@tiptap/pm/keymap`, `@tiptap/pm/inputrules`,
`@tiptap/pm/history`, `@tiptap/pm/tables`, `@tiptap/pm/dropcursor`,
`@tiptap/pm/gapcursor`, `@tiptap/pm/collab`, `@tiptap/pm/menu`,
`@tiptap/pm/schema-basic`, `@tiptap/pm/schema-list`, `@tiptap/pm/markdown`,
`@tiptap/pm/trailing-node`, `@tiptap/pm/changeset`

---

## StarterKit

Bundles the most common extensions.

### Included

**Nodes:** Document, Paragraph, Text, Heading, Blockquote, BulletList, OrderedList, ListItem, CodeBlock, HardBreak, HorizontalRule

**Marks:** Bold, Italic, Strike, Code, Link, Underline

**Functionality:** Dropcursor, Gapcursor, Undo/Redo, ListKeymap, TrailingNode

### Usage

```javascript
import StarterKit from '@tiptap/starter-kit'

new Editor({
  extensions: [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
      undoRedo: false, // disable specific extension
    }),
  ],
})
```

---

## Extension Reference

### Functionality Extensions

| Extension | Package | Description |
|-----------|---------|-------------|
| Placeholder | `@tiptap/extensions` | Empty editor/node hint text |
| TextAlign | `@tiptap/extension-text-align` | Text alignment (left/center/right/justify) |
| Color | `@tiptap/extension-text-style` | Font color (requires TextStyle) |
| Highlight | `@tiptap/extension-highlight` | Text highlighting with multicolor support |
| DragHandle | `@tiptap/extension-drag-handle` | Drag nodes around the editor |
| Collaboration | `@tiptap/extension-collaboration` | Real-time collaborative editing via Y.js |

### Placeholder configuration

```javascript
import { Placeholder } from '@tiptap/extensions'

Placeholder.configure({
  placeholder: 'Write something...',
  // or dynamic per node type:
  placeholder: ({ node }) => {
    if (node.type.name === 'heading') return 'Enter a title...'
    return 'Write something...'
  },
  emptyEditorClass: 'is-editor-empty',
  emptyNodeClass: 'is-empty',
  showOnlyWhenEditable: true,
  showOnlyCurrent: true,
  includeChildren: false,
})
```

CSS required:
```css
.tiptap p.is-editor-empty:first-child::before {
  color: #adb5bd;
  content: attr(data-placeholder);
  float: left;
  height: 0;
  pointer-events: none;
}
```

### TextAlign configuration

```javascript
TextAlign.configure({
  types: ['heading', 'paragraph'],
  alignments: ['left', 'center', 'right', 'justify'],
  defaultAlignment: null,
})

// Commands
editor.commands.setTextAlign('center')
editor.commands.unsetTextAlign()
editor.commands.toggleTextAlign('right')
```

### Color configuration

```javascript
import { TextStyle, Color } from '@tiptap/extension-text-style'

// Both required
extensions: [TextStyle, Color]

// Commands
editor.commands.setColor('#ff0000')
editor.commands.unsetColor()
```

### Highlight configuration

```javascript
Highlight.configure({
  multicolor: true,
  HTMLAttributes: { class: 'highlight' },
})

// Commands
editor.commands.setHighlight({ color: '#ffcc00' })
editor.commands.toggleHighlight()
editor.commands.unsetHighlight()
```

### Table configuration

```javascript
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableCell } from '@tiptap/extension-table-cell'
import { TableHeader } from '@tiptap/extension-table-header'

Table.configure({
  resizable: true,
  handleWidth: 5,
  cellMinWidth: 25,
  lastColumnResizable: true,
  allowTableNodeSelection: false,
})
```

### Image configuration

```javascript
Image.configure({
  inline: false,          // true for inline images
  allowBase64: true,      // allow data URLs
  resize: {
    enabled: true,
    directions: ['top', 'bottom', 'left', 'right'],
    minWidth: 50,
    minHeight: 50,
    alwaysPreserveAspectRatio: true,
  },
})

// Command
editor.commands.setImage({ src: 'url', alt: 'desc', title: 'title' })
```

### DragHandle configuration

```javascript
import DragHandle from '@tiptap/extension-drag-handle'

DragHandle.configure({
  render: () => {
    const el = document.createElement('div')
    el.classList.add('drag-handle')
    return el
  },
  locked: false,
  nested: false,
})

// Commands
editor.commands.lockDragHandle()
editor.commands.unlockDragHandle()
editor.commands.toggleDragHandle()
```

### Keyboard shortcuts reference

| Action | Windows/Linux | macOS |
|--------|---------------|-------|
| Bold | Ctrl+B | Cmd+B |
| Italic | Ctrl+I | Cmd+I |
| Underline | Ctrl+U | Cmd+U |
| Strike | Ctrl+Shift+S | Cmd+Shift+S |
| Highlight | Ctrl+Shift+H | Cmd+Shift+H |
| Heading 1-6 | Ctrl+Alt+[1-6] | Cmd+Alt+[1-6] |
| Paragraph | Ctrl+Alt+0 | Cmd+Alt+0 |
| Bullet list | Ctrl+Shift+8 | Cmd+Shift+8 |
| Ordered list | Ctrl+Shift+7 | Cmd+Shift+7 |
| Align left | Ctrl+Shift+L | Cmd+Shift+L |
| Align center | Ctrl+Shift+E | Cmd+Shift+E |
| Align right | Ctrl+Shift+R | Cmd+Shift+R |
| Justify | Ctrl+Shift+J | Cmd+Shift+J |
| Hard break | Shift+Enter | Shift+Enter |
| Undo | Ctrl+Z | Cmd+Z |
| Redo | Ctrl+Shift+Z | Cmd+Shift+Z |
