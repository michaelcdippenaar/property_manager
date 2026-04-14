# Tremly Custom TipTap Extensions Reference

## Overview

All custom extensions live in `admin/src/extensions/` and are registered in `admin/src/composables/useTiptapEditor.ts`.

---

## 1. MergeField (Inline Atomic Node)

**File:** `admin/src/extensions/MergeFieldNode.ts`
**Component:** `admin/src/extensions/MergeFieldComponent.vue`
**Purpose:** Template variables like `{{landlord_name}}` rendered as colored chips in the editor.

### Schema
```typescript
{
  name: 'mergeField',
  group: 'inline',
  inline: true,
  atom: true,
  selectable: true,
  draggable: true,
}
```

### Attributes
| Attribute | Default | Description |
|-----------|---------|-------------|
| `fieldName` | null | Variable name (e.g., `landlord_name`) |
| `category` | 'general' | Color category: landlord, tenant, property, lease, agent |
| `label` | null | Human-readable display label |

### HTML Roundtrip
```html
<!-- Exported HTML -->
<span data-type="merge-field" data-field-name="landlord_name" data-category="landlord" class="merge-field">
  {{landlord_name}}
</span>

<!-- Legacy formats also parsed: -->
<span data-merge-field="landlord_name">...</span>
<span data-field="landlord_name">...</span>
```

### Command
```typescript
editor.chain().focus().insertMergeField({
  fieldName: 'landlord_name',
  category: 'landlord',  // optional — auto-derived from fieldName prefix
  label: 'Landlord Name', // optional — auto-generated from fieldName
}).run()
```

### Category Auto-Detection
| Prefix | Category |
|--------|----------|
| `landlord_`, `lessor_` | landlord (blue) |
| `tenant_`, `lessee_`, `co_tenant_` | tenant (green) |
| `property_`, `unit_`, `city_`, `province_` | property (amber) |
| `lease_`, `monthly_`, `deposit_`, `notice_`, `water_`, `electricity_`, `max_`, `payment_` | lease (purple) |
| `agent_` | agent (cyan) |
| Other | general (gray) |

### Vue Component
- Renders as inline `<span>` chip with icon + label
- Category-based color classes (bg, text, border)
- Icons from `lucide-vue-next`: User (landlord/tenant), Home (property), FileText (lease), Briefcase (agent)
- Shows selection ring when `selected` prop is true

---

## 2. SignatureBlock (Block Atomic Node)

**File:** `admin/src/extensions/SignatureBlockNode.ts`
**Component:** `admin/src/extensions/SignatureBlockComponent.vue`
**Purpose:** Signing fields (signature, initials, date) for e-signing workflows.

### Schema
```typescript
{
  name: 'signatureBlock',
  group: 'block',
  atom: true,
  draggable: true,
  selectable: true,
}
```

### Attributes
| Attribute | Default | Description |
|-----------|---------|-------------|
| `fieldName` | null | Unique field ID (e.g., `landlord_signature_1`) |
| `fieldType` | 'signature' | Type: `signature`, `initials`, `date` |
| `signerRole` | 'landlord' | Signer: `landlord`, `tenant_1`, `tenant_2`, `tenant_3`, `witness`, `agent` |
| `label` | null | Display label |

### Unique Field Names
Each insertion gets a unique counter-based name: `{signerRole}_{fieldType}_{counter}`
This fixes the old editor's bug where same-named fields were deduplicated.

```typescript
let _blockCounter = 0
// On insert: fieldName = `${signerRole}_${fieldType}_${++_blockCounter}`
// e.g., "landlord_initials_1", "landlord_initials_2", "tenant_1_signature_3"
```

### HTML Roundtrip
```html
<!-- Exported HTML -->
<div data-type="signature-block" data-field-type="initials" data-signer-role="landlord"
     data-field-name="landlord_initials_1" style="width:100px;height:40px;margin:8px 0;">
  {{landlord_initials_1}}
</div>

<!-- Legacy format also parsed: -->
<div data-field-type="signature" data-party="landlord" data-field="landlord_signature">...</div>
```

### Field Type Dimensions
| Type | Width | Height |
|------|-------|--------|
| signature | 200px | 60px |
| initials | 100px | 40px |
| date | 120px | 24px |

### Command
```typescript
editor.chain().focus().insertSignatureBlock({
  fieldType: 'signature',   // required
  signerRole: 'landlord',   // required
  label: 'Signature — Landlord',  // optional
}).run()
```

### Vue Component
- Block-level dashed border card with icon + info
- Role selector dropdown (landlord, tenant 1-3, witness, agent)
- Delete button (X icon)
- Color coding by signer role:
  - landlord: blue, tenant_1: green, tenant_2: emerald, tenant_3: teal
  - witness: amber, agent: cyan
- Icons: PenTool (signature), Type (initials), Calendar (date)
- Drag handle on the wrapper element

---

## 3. PageBreak (Block Atomic Node)

**File:** `admin/src/extensions/PageBreakNode.ts`
**Purpose:** Explicit page breaks for PDF/print output.

### Schema
```typescript
{
  name: 'pageBreak',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: false,
}
```

### HTML Roundtrip
```html
<div data-page-break="true" style="page-break-after: always;"></div>

<!-- Also parses: -->
<div style="page-break-before: always;">...</div>
<hr class="page-break">
```

### Command
```typescript
editor.chain().focus().insertPageBreak().run()
```

### Editor CSS (in TiptapEditorView.vue)
```css
.tiptap-editor div[data-page-break] {
  border-top: 2px dashed #d1d5db;
  margin: 24px 0;
  position: relative;
}
.tiptap-editor div[data-page-break]::after {
  content: 'Page Break';
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%);
  background: white;
  padding: 0 8px;
  font-size: 10px;
  color: #9ca3af;
}
```

---

## 4. FontSize (Functionality Extension)

**File:** `admin/src/extensions/FontSize.ts`
**Purpose:** Font size control via textStyle mark. Created because `@tiptap/extension-font-size` doesn't exist on npm.

### How It Works
- Adds `fontSize` as a global attribute on the `textStyle` mark type
- Parses `style="font-size: ..."` from HTML
- Renders back as inline style

### Commands
```typescript
// Set font size
editor.chain().focus().setFontSize('14pt').run()

// Remove font size
editor.chain().focus().unsetFontSize().run()
```

### Requires
- `@tiptap/extension-text-style` must be registered (provides the `textStyle` mark)

---

## 5. PaginationPlus (Third-Party Extension)

**Package:** `tiptap-pagination-plus`
**Purpose:** Google Docs-style page simulation with real page breaks, gaps between pages, and automatic page numbering.

This replaces the older custom `PageSimulation` extension. It is NOT a local extension — it's installed via npm.

### Configuration (in useTiptapEditor.ts)
```typescript
import { PaginationPlus } from 'tiptap-pagination-plus'

PaginationPlus.configure({
  pageHeight: 1123,           // A4 height in px
  pageWidth: 794,             // A4 width in px
  pageGap: 40,                // gray gap between pages
  pageGapBorderSize: 1,
  pageGapBorderColor: '#c4c7c5',
  pageBreakBackground: '#f8f9fa',
  marginTop: 48,
  marginBottom: 48,
  marginLeft: 56,
  marginRight: 56,
  contentMarginTop: 0,
  contentMarginBottom: 0,
  footerRight: '{page}',      // automatic page numbering
  footerLeft: '',
  headerRight: '',
  headerLeft: '',
})
```

### Key Differences from PageSimulation
- Real page boundaries with visual gaps between pages (like Google Docs)
- Automatic page numbering via `{page}` placeholder in footer
- Content flows within configured margins
- No custom ProseMirror plugin needed — the extension handles everything

---

## 6. Barrel Export

**File:** `admin/src/extensions/index.ts`
```typescript
export { MergeField } from './MergeFieldNode'
export { SignatureBlock } from './SignatureBlockNode'
export { PageBreak } from './PageBreakNode'
export { FontSize } from './FontSize'
```

Note: `PaginationPlus` is imported directly from `tiptap-pagination-plus`, not from the local extensions barrel.

---

## Document Storage Format

### v2 JSON Envelope
```json
{
  "v": 2,
  "html": "<p>Rendered HTML for backend consumption...</p>",
  "tiptapJson": {
    "type": "doc",
    "content": [
      { "type": "heading", "attrs": { "level": 1 }, "content": [{ "type": "text", "text": "Title" }] },
      { "type": "paragraph", "content": [
        { "type": "text", "text": "Landlord: " },
        { "type": "mergeField", "attrs": { "fieldName": "landlord_name", "category": "landlord", "label": "Landlord Name" } }
      ]},
      { "type": "signatureBlock", "attrs": { "fieldName": "landlord_signature_1", "fieldType": "signature", "signerRole": "landlord" } },
      { "type": "pageBreak" }
    ]
  },
  "fields": [
    { "fieldName": "landlord_signature_1", "fieldType": "signature", "signerRole": "landlord" },
    { "fieldName": "landlord_initials_1", "fieldType": "initials", "signerRole": "landlord" }
  ]
}
```

### v1 Legacy Format (old editor)
```json
{
  "v": 1,
  "html": "<p>Raw HTML with {{markers}} and data-field spans...</p>",
  "fields": [{ "fieldName": "landlord_signature", "fieldType": "signature", "signerRole": "landlord" }]
}
```

The TipTap editor's `parseHTML` rules handle both v1 legacy HTML (with `data-merge-field`, `data-field`, `data-field-type` attributes) and v2 format (with `data-type="merge-field"` and `data-type="signature-block"`).
