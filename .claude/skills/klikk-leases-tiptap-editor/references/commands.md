# TipTap Commands Reference

## Execute commands

```javascript
// Single command
editor.commands.setBold()

// Chained commands (single transaction, single update event)
editor.chain().focus().toggleBold().run()

// Dry run — check without applying
editor.can().toggleBold()
editor.can().chain().toggleBold().toggleItalic().run()
```

## Inline commands in chains

```javascript
editor.chain().focus().command(({ tr }) => {
  tr.insertText('inserted text')
  return true
}).run()
```

## Try first successful command

```javascript
editor.commands.first(({ commands }) => [
  () => commands.undoInputRule(),
  () => commands.deleteSelection(),
])
```

## Content Commands

| Command | Description |
|---------|-------------|
| `clearContent()` | Clear whole document |
| `insertContent(value)` | Insert node or HTML at current position |
| `insertContentAt(pos, value)` | Insert at specific position |
| `setContent(value)` | Replace whole document |

## Node & Mark Commands

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

## List Commands

| Command | Description |
|---------|-------------|
| `liftListItem(name)` | Lift into wrapping list |
| `sinkListItem(name)` | Sink into inner list |
| `splitListItem(name)` | Split list item |
| `toggleList(name, itemName)` | Toggle list type |
| `wrapInList(name)` | Wrap in list |

## Selection Commands

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

## Table Commands

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

## Mark Commands Pattern

```javascript
editor.commands.setBold()      // apply
editor.commands.toggleBold()   // toggle
editor.commands.unsetBold()    // remove
editor.isActive('bold')        // check state
```

## Transaction Mapping in Chained Commands

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

## Custom Commands with dispatch Check

For commands to work with `.can()`, check `dispatch`:

```javascript
export default (value) => ({ tr, dispatch }) => {
  if (dispatch) {
    tr.insertText(value)
  }
  return true
}
```

## Keyboard Shortcuts Reference

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
