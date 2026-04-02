# TipTap Custom Nodes & Extensions Reference

## Creating Custom Nodes

```typescript
import { Node, mergeAttributes } from '@tiptap/core'

const CustomNode = Node.create({
  name: 'customNode',
  group: 'inline',       // 'block' | 'inline'
  inline: true,          // inline with text
  atom: true,            // uneditable unit (no cursor inside)
  draggable: true,       // can be dragged
  selectable: true,      // can be selected
  content: 'inline*',    // child content expression (empty for atom nodes)
})
```

### Node Group & Content Expressions

- `group: 'block'` — block-level node
- `group: 'inline'` — inline with text
- `content: 'block+'` — one or more block children
- `content: 'inline*'` — zero or more inline children
- `content: '(paragraph|heading)+'` — specific types
- No `content` for atom nodes

---

## renderHTML — Controls getHTML() Serialization

**Critical: renderHTML is SEPARATE from addNodeView.** renderHTML controls `editor.getHTML()` output. addNodeView controls what appears in the editor UI. They are completely independent.

### Return Format

```typescript
renderHTML({ HTMLAttributes }) {
  // [tagName, attributes, content/0]
  return ['div', HTMLAttributes, 0]  // 0 = render children here
}
```

- **First element**: HTML tag name (string) — can be ANY tag including custom tags
- **Second element**: Attributes object (optional)
- **`0`**: Placeholder for child content rendering
- **String**: Static text content
- **Nested array**: Wrapped elements `['pre', ['code', attrs, 0]]`

### Examples

```typescript
// Simple tag
renderHTML({ HTMLAttributes }) {
  return ['strong', HTMLAttributes, 0]
}
// Output: <strong>content</strong>

// Custom tag with attributes
renderHTML({ HTMLAttributes }) {
  return ['signature-field', mergeAttributes(HTMLAttributes, {
    name: 'sig1',
    role: 'landlord',
    required: 'true',
  }), ' ']  // space as content
}
// Output: <signature-field name="sig1" role="landlord" required="true"> </signature-field>

// Nested tags
renderHTML({ HTMLAttributes }) {
  return ['pre', ['code', HTMLAttributes, 0]]
}
// Output: <pre><code>content</code></pre>

// Merge custom attrs with node attrs
import { mergeAttributes } from '@tiptap/core'
renderHTML({ HTMLAttributes }) {
  return ['a', mergeAttributes(HTMLAttributes, { rel: 'noopener' }), 0]
}
```

---

## parseHTML — Load from HTML

Defines rules for how HTML is parsed back into the node.

```typescript
parseHTML() {
  return [
    // Simple tag matching
    { tag: 'strong' },

    // Tag with attribute selector
    { tag: 'span[data-type="mention"]' },

    // Custom tag
    { tag: 'signature-field' },

    // With attribute extraction
    { tag: 'div[data-field-type]', getAttrs: (el: HTMLElement) => {
      const type = el.getAttribute('data-field-type')
      if (type !== 'signature') return false  // false = skip this rule
      return {
        fieldType: type,
        fieldName: el.getAttribute('data-field'),
      }
    }},

    // Style-based matching
    { style: 'font-weight', getAttrs: value =>
      /^(bold|[5-9]\d{2,})$/.test(value) && null
    },
  ]
}
```

**getAttrs return values:**
- `null` or `undefined` — match succeeded, use default attrs
- `false` — skip this rule, try next
- `{ ... }` — match succeeded, use these attrs
- Object with attribute values

**Priority:** Rules are tried in order. First match wins.

---

## addAttributes — Node Data

```typescript
addAttributes() {
  return {
    fieldName: {
      default: null,
      // How to read from HTML
      parseHTML: (element: HTMLElement) => element.getAttribute('data-field-name'),
      // How to write to HTML (returned object is merged into tag attrs)
      renderHTML: (attributes: Record<string, any>) => ({
        'data-field-name': attributes.fieldName,
      }),
    },
    color: {
      default: 'black',
      parseHTML: (el) => el.getAttribute('data-color'),
      renderHTML: (attrs) => ({
        'data-color': attrs.color,
        style: `color: ${attrs.color}`,
      }),
      rendered: false, // Set to false to skip rendering this attr
    },
  }
}
```

**Extending parent attributes:**
```typescript
addAttributes() {
  return {
    ...this.parent?.(),
    myNewAttribute: { default: null },
  }
}
```

---

## addNodeView — Editor Display (Vue)

**Completely independent from renderHTML.** NodeView controls what users see in the editor. renderHTML controls getHTML() output.

```typescript
import { VueNodeViewRenderer } from '@tiptap/vue-3'
import MyComponent from './MyComponent.vue'

addNodeView() {
  return VueNodeViewRenderer(MyComponent)
}
```

**Vue Component:**
```vue
<template>
  <NodeViewWrapper class="my-node">
    <span>{{ node.attrs.fieldName }}</span>
    <!-- For editable content: -->
    <NodeViewContent />
  </NodeViewWrapper>
</template>

<script setup>
import { NodeViewWrapper, NodeViewContent, nodeViewProps } from '@tiptap/vue-3'

const props = defineProps(nodeViewProps)
// Available: props.node, props.editor, props.selected, props.updateAttributes, props.deleteNode
</script>
```

**nodeViewProps provides:**
- `node` — ProseMirror node (access `node.attrs`)
- `editor` — TipTap editor instance
- `selected` — boolean, is node selected
- `updateAttributes(attrs)` — update node attributes
- `deleteNode()` — remove this node
- `getPos()` — get node position in document
- `extension` — the extension instance
- `decorations` — ProseMirror decorations

---

## addCommands

```typescript
addCommands() {
  return {
    insertMyNode: (attrs) => ({ commands }) => {
      return commands.insertContent({
        type: this.name,
        attrs: { ...attrs },
      })
    },
    toggleMyNode: () => ({ commands }) => {
      return commands.toggleNode(this.name, 'paragraph')
    },
  }
}
```

**Usage:** `editor.commands.insertMyNode({ fieldName: 'test' })`

---

## addKeyboardShortcuts

```typescript
addKeyboardShortcuts() {
  return {
    'Mod-Enter': () => this.editor.commands.insertMyNode(),
    'Backspace': () => this.editor.commands.deleteNode(this.name),
  }
}
```

---

## addInputRules & addPasteRules

```typescript
import { nodeInputRule, nodePasteRule } from '@tiptap/core'

addInputRules() {
  return [
    nodeInputRule({
      find: /pattern$/,
      type: this.type,
      getAttributes: match => ({ /* attrs */ }),
    }),
  ]
}
```

---

## addProseMirrorPlugins

```typescript
import { Plugin } from '@tiptap/pm/state'

addProseMirrorPlugins() {
  return [
    new Plugin({
      // ProseMirror plugin config
    }),
  ]
}
```

---

## getHTML() vs getJSON()

```typescript
// HTML string — uses renderHTML() from all extensions
const html = editor.getHTML()

// ProseMirror JSON — structured data, no renderHTML needed
const json = editor.getJSON()

// Server-side rendering (no editor instance needed)
import { generateHTML, generateJSON } from '@tiptap/html'
const html = generateHTML(json, extensions)
const json = generateJSON(html, extensions)
```

**Key principle:** `getHTML()` calls `renderHTML()` on every node/mark in the document tree. The output is pure HTML with no interactive behavior. `addNodeView()` is NEVER used by `getHTML()`.

---

## Global Attributes

Apply attributes across multiple node types:

```typescript
const TextAlign = Extension.create({
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
})
```

---

## Schema Validation

```typescript
const editor = new Editor({
  content: htmlOrJson,
  enableContentCheck: true,
  onContentError({ error }) {
    console.error('Content does not match schema:', error)
  },
})
```

ProseMirror schema is strict — unrecognized HTML tags/attributes are silently stripped during parsing.

---

## Extension Lifecycle Hooks

```typescript
Extension.create({
  onCreate() {},        // Editor created
  onUpdate() {},        // Content changed
  onSelectionUpdate() {},
  onTransaction() {},
  onFocus() {},
  onBlur() {},
  onDestroy() {},       // Editor destroyed
})
```
