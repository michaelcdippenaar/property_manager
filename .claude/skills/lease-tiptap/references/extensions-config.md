# TipTap Extension Configuration Reference

## StarterKit

Bundles the most common extensions.

**Nodes:** Document, Paragraph, Text, Heading, Blockquote, BulletList, OrderedList, ListItem, CodeBlock, HardBreak, HorizontalRule

**Marks:** Bold, Italic, Strike, Code, Link, Underline

**Functionality:** Dropcursor, Gapcursor, Undo/Redo, ListKeymap, TrailingNode

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

## Table

```javascript
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableCell } from '@tiptap/extension-table-cell'
import { TableHeader } from '@tiptap/extension-table-header'

Table.configure({
  resizable: true,          // column resize (default: false)
  handleWidth: 5,           // resize handle width (default: 5)
  cellMinWidth: 25,         // min cell width (default: 25)
  lastColumnResizable: true,
  allowTableNodeSelection: false,
})
```

## TextAlign

```javascript
import { TextAlign } from '@tiptap/extension-text-align'

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

## Color (requires TextStyle)

```javascript
import { TextStyle, Color } from '@tiptap/extension-text-style'

extensions: [TextStyle, Color]

// Commands
editor.commands.setColor('#ff0000')
editor.commands.unsetColor()
```

## Highlight

```javascript
import { Highlight } from '@tiptap/extension-highlight'

Highlight.configure({
  multicolor: true,  // enable multiple colors (default: false)
  HTMLAttributes: { class: 'highlight' },
})

// Commands
editor.commands.setHighlight({ color: '#ffcc00' })
editor.commands.toggleHighlight()
editor.commands.unsetHighlight()
```

## Placeholder

```javascript
import { Placeholder } from '@tiptap/extensions'

Placeholder.configure({
  placeholder: 'Write something...',
  // or dynamic:
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

## Image

```javascript
import Image from '@tiptap/extension-image'

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

## DragHandle

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

## Available Marks (Open Source)

| Mark | Tag | Shortcut |
|------|-----|----------|
| Bold | `<strong>` | Ctrl/Cmd+B |
| Italic | `<em>` | Ctrl/Cmd+I |
| Underline | `<u>` | Ctrl/Cmd+U |
| Strike | `<s>` | Ctrl/Cmd+Shift+S |
| Code | `<code>` | — |
| Highlight | `<mark>` | Ctrl/Cmd+Shift+H |
| Link | `<a>` | — |
| TextStyle | `<span>` | Foundation for Color, FontFamily |
| Subscript | `<sub>` | — |
| Superscript | `<sup>` | — |

## Available Nodes (Open Source)

| Node | Tag | Input Rule |
|------|-----|------------|
| Document | — | Required root node |
| Paragraph | `<p>` | Required |
| Text | — | Required |
| Heading | `<h1>`-`<h6>` | `#`, `##`, etc. |
| BulletList | `<ul>` | `*`, `-`, `+` |
| OrderedList | `<ol>` | `1.` |
| ListItem | `<li>` | — |
| Blockquote | `<blockquote>` | `>` |
| CodeBlock | `<pre><code>` | ``` |
| HardBreak | `<br>` | Shift+Enter |
| HorizontalRule | `<hr>` | `---` |
| Image | `<img>` | — |
| Table | `<table>` | — |
| TaskList/TaskItem | `<ul>/<li>` | — |
| Mention | — | `@` |

## ProseMirror Integration

Access internals via `@tiptap/pm`:

```javascript
import { EditorState, Plugin } from '@tiptap/pm/state'
import { EditorView } from '@tiptap/pm/view'
import { Schema, Node as ProseMirrorNode } from '@tiptap/pm/model'
```

Available: `@tiptap/pm/state`, `@tiptap/pm/view`, `@tiptap/pm/model`,
`@tiptap/pm/transform`, `@tiptap/pm/commands`, `@tiptap/pm/keymap`,
`@tiptap/pm/inputrules`, `@tiptap/pm/history`, `@tiptap/pm/tables`,
`@tiptap/pm/dropcursor`, `@tiptap/pm/gapcursor`, `@tiptap/pm/collab`
