# Icon Policy

## Lucide only

**All icons come from `lucide-vue-next`.** Phosphor (`@phosphor-icons/vue`) was removed from the admin app in April 2026 and is **banned** — do not reintroduce it.

```ts
import { Plus, Pencil, Trash2, Building2 } from 'lucide-vue-next'
```

If a view pulls in a second icon library to get a glyph that Lucide doesn't have, pick a different Lucide glyph or a small inline SVG. No mixed icon sets.

## Global stroke width

All Lucide icons ship at stroke-width 1.75, applied globally in `admin/src/assets/main.css`:

```css
.lucide { stroke-width: 1.75; }
```

Do not override per-icon unless there is a very good reason (and then only with `:stroke-width="2"` inline, documented).

## Sizes

| Context | Size | Notes |
|---------|------|-------|
| Buttons (`.btn-*`) | `:size="16"` | Paired with `gap-1.5` or `gap-2` |
| Primary nav links | `:size="18"` | Includes mobile accordion rows |
| Section-card headers | `:size="14"` | `text-navy` next to the uppercase label |
| Inline chevrons / dividers | `:size="12"` | Breadcrumb separators, dropdown affordances |
| Empty state hero icon | via `EmptyState`'s `icon` prop | Component handles sizing |

## Color

Default to inherit. Explicit colours:
- `text-navy` for section-card header icons and active dropdown items
- `text-gray-400` for inactive/inert affordances
- `text-accent` only on the logo dot — never on navigation icons
