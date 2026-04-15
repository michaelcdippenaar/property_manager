# Accessibility, Error Handling & Form Rules

---

## ARIA Labels

Every icon-only button MUST have an `aria-label`:
```html
<button aria-label="Log out"><LogOut :size="18" /></button>
<button aria-label="Close dialog"><X :size="18" /></button>
<button aria-label="Collapse sidebar"><ChevronsLeft :size="18" /></button>
```

---

## Semantic HTML

| Element | Requirement |
|---------|-------------|
| Modals | `role="dialog"`, `aria-modal="true"`, focus trapping |
| Tables | `scope="col"` on all `<th>` |
| Navigation | Wrap in `<nav>` landmark |
| Content | Wrap in `<main>` landmark |
| Toast/loading | `aria-live="polite"` regions |
| Collapsibles | `aria-expanded` on toggle buttons |
| Progress bars | `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax` |
| Form labels | Pair with `for`/`id` attributes |

---

## Focus Management

- Define `:focus-visible` styling for all interactive elements
- Never suppress browser focus rings without replacement
- Trap focus within modals/drawers

---

## Color Independence

- Never use color alone to convey status — always include text labels
- Badges already have text labels (good) — consider adding status icons for critical items

---

## Error Handling (CRITICAL)

**Never silently swallow errors:**

```typescript
// BAD — found 12+ times in codebase
catch {}
catch { /* ignore */ }

// GOOD
catch (err) {
  toast.error('Failed to load properties. Please try again.')
}
```

Every API call must have:
1. **Loading state** — skeleton loaders, not "Loading..." text
2. **Error state** — toast notification
3. **Empty state** — `EmptyState` component with action CTA

---

## Form Validation Rules

Every form MUST implement:
1. Required field indicators: `<span class="text-danger-500">*</span>` in labels
2. Field-level validation on blur AND submit
3. `.input-error` class on invalid fields
4. `.input-error-msg` message below invalid fields
5. Scroll to first error on submit
6. Disabled submit button while saving (`opacity-50 cursor-not-allowed`)

Use `useFormValidation()` composable when available.

---

## Destructive Action Rules

- **Never use `window.confirm()`** — use styled `ConfirmDialog` component
- Destructive buttons use `btn-danger` styling
- Include clear description of what will be deleted/changed
- Consider undo support for reversible actions

---

## Unsaved Changes

Forms that accumulate changes MUST:
1. Track dirty state
2. Show `beforeRouteLeave` guard warning
3. Add `beforeunload` event listener
4. Visually indicate unsaved changes (dot indicator or "Unsaved changes" text)

---

## Loading States

Use skeleton loaders (`animate-pulse`) that match the content layout:

```html
<!-- Table skeleton -->
<tr v-for="i in 5" :key="i">
  <td><div class="h-4 bg-gray-200 rounded animate-pulse w-3/4"></div></td>
  <td><div class="h-4 bg-gray-200 rounded animate-pulse w-1/2"></div></td>
</tr>

<!-- Card skeleton -->
<div class="card p-6">
  <div class="h-4 bg-gray-200 rounded animate-pulse w-1/3 mb-4"></div>
  <div class="h-8 bg-gray-200 rounded animate-pulse w-1/4"></div>
</div>
```

**Never use plain "Loading..." text** (audit finding: OwnerDashboard).
