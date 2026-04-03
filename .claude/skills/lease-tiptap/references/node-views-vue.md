# TipTap Vue 3 Node Views

Node views let you render interactive Vue components inside the editor. The node view (in-editor rendering) is **independent** from `renderHTML()` (HTML output) — the editor does NOT export the rendered Vue component.

## Setup Pattern

```javascript
import { Node, mergeAttributes } from '@tiptap/core'
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

## Vue Component

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

## Available Props

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

## Three Node View Types

1. **Editable text** — cursor enters, standard commands work (e.g., TaskItem)
2. **Non-editable text** — `contenteditable="false"` applied automatically
3. **Mixed content** — combine editable and non-editable sections

## Rules

- Root element **must** be `<node-view-wrapper>`
- For inline nodes: `<node-view-wrapper as="span">`
- `<node-view-content>` renders editable child content (for non-atom nodes)
- Both wrapper and content render `<div>` by default; use `as` prop to change
- For dragging: set `draggable: true` in extension AND add `data-drag-handle` to wrapper
- `contenteditable="false"` on elements prevents cursor entry

## Inline Node View Example

```vue
<template>
  <node-view-wrapper as="span" :draggable="true" data-drag-handle>
    <span contenteditable="false" :class="selected ? 'ring-2' : ''">
      {{ node.attrs.label }}
    </span>
  </node-view-wrapper>
</template>

<script setup lang="ts">
import { nodeViewProps, NodeViewWrapper } from '@tiptap/vue-3'
const props = defineProps(nodeViewProps)
</script>
```

## Important: renderHTML vs Node View

- `renderHTML()` → controls **HTML output** (getHTML(), storage, backend)
- `addNodeView()` → controls **in-editor rendering** (what the user sees while editing)
- These are independent. The editor never exports the Vue component.
- Always configure both: `renderHTML` for data persistence, `addNodeView` for the editing experience.
