# TipTap Editor Configuration, Methods & Properties

## Installation

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

## Editor Options

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

## Editor Methods

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

## Editor Properties

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

## Output (JSON & HTML)

```javascript
const html = editor.getHTML()
const json = editor.getJSON()
const text = editor.getText()

editor.commands.setContent('<p>New HTML content</p>')
editor.commands.setContent({ type: 'doc', content: [...] })
```

### Listen for changes

```javascript
new Editor({
  onUpdate({ editor }) {
    const html = editor.getHTML()
    const json = editor.getJSON()
  },
})
```

### Server-side HTML generation from JSON

```javascript
import { generateHTML } from '@tiptap/html'
import StarterKit from '@tiptap/starter-kit'
const html = generateHTML(jsonContent, [StarterKit])
```

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

## Styling

TipTap is headless — no default styles. Editor renders inside `.tiptap` class.

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
Paragraph.configure({ HTMLAttributes: { class: 'my-paragraph' } })
```

### Add classes via editorProps

```javascript
new Editor({
  editorProps: {
    attributes: { class: 'prose prose-sm focus:outline-none' },
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

## Menus

- **Fixed menu** — toolbar above editor
- **Bubble menu** — appears on text selection
- **Floating menu** — appears on empty lines

### Button pattern

```javascript
editor.chain().focus().toggleBold().run()
editor.isActive('bold')
editor.isActive('heading', { level: 2 })
```

Always include `.focus()` in button handlers to restore editor focus.
