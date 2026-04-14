# TipTap Custom Extensions — Creating & Extending

## Extension Types

| Type | Import | Purpose |
|------|--------|---------|
| `Extension` | `@tiptap/core` | Functionality only, no schema |
| `Node` | `@tiptap/core` | Content types in the document tree |
| `Mark` | `@tiptap/core` | Formatting applied to text |

## Create an Extension (Functionality Only)

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
      types: ['heading', 'paragraph'],  // or '*', 'nodes', 'marks'
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

## Create a Node (Content Type)

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

## Create a Mark (Formatting)

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

## Callback Function Pattern

```javascript
const CustomExtension = Extension.create(() => {
  let internalState = 0
  return {
    name: 'custom',
    onUpdate() { internalState++ },
  }
})
```

## Extending Existing Extensions

Every extension has `.extend()`:

```javascript
import Heading from '@tiptap/extension-heading'

const CustomHeading = Heading.extend({
  addOptions() {
    return { ...this.parent?.(), levels: [1, 2, 3] }
  },

  addAttributes() {
    return {
      ...this.parent?.(),  // keep existing attributes
      customId: { default: null },
    }
  },

  content: 'inline*',  // override schema

  renderHTML({ HTMLAttributes }) {
    return ['h' + this.options.levels[0], mergeAttributes(HTMLAttributes), 0]
  },

  parseHTML() {
    return this.options.levels.map(level => ({
      tag: `h${level}`,
      attrs: { level },
    }))
  },

  addKeyboardShortcuts() {
    return { 'Mod-l': () => this.editor.commands.toggleBulletList() }
  },

  addCommands() {
    return {
      ...this.parent?.(),
      customCommand: () => ({ commands }) => { /* ... */ },
    }
  },
})
```

### Storage (Mutable Data)

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

## Schema Configuration

### Node Properties

| Property | Description | Example |
|----------|-------------|---------|
| `content` | Allowed children | `'block+'`, `'inline*'`, `'(paragraph\|list?)+'` |
| `marks` | Allowed marks | `'bold'`, `'_'` (all), `''` (none) |
| `group` | Node group | `'block'`, `'inline'` |
| `inline` | Render inline | `true` / `false` |
| `atom` | Non-editable unit | `true` / `false` |
| `selectable` | Node selection | `true` / `false` |
| `draggable` | Drag-and-drop | `true` / `false` |
| `code` | Code behavior | `true` / `false` |
| `whitespace` | Whitespace | `'pre'` preserves |
| `defining` | Prevents removal | `true` / `false` |
| `isolating` | Fences cursor | `true` / `false` |
| `allowGapCursor` | Gap cursor | `true` / `false` |
| `tableRole` | Table role | `'table'`, `'row'`, `'cell'`, `'header_cell'` |

### Mark Properties

| Property | Description |
|----------|-------------|
| `inclusive` | Mark stays active at boundary (default: true) |
| `excludes` | Marks that can't coexist |
| `exitable` | Cursor can leave mark at node end |
| `group` | Mark group |
| `spanning` | Can span multiple nodes |

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
