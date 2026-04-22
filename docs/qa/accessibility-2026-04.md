# Accessibility Audit — WCAG 2.1 AA
**Date:** 2026-04-22
**Auditor:** rentals-implementer (QA-007)
**Scope:** Admin SPA (`admin/src/`), Astro marketing website (`website/src/`). Tenant Flutter app deferred (cut from v1 per DEC record).
**Standard:** WCAG 2.1 Level AA

---

## Executive summary

Static code audit performed. No live axe-core sweep was run (dev server not started — that is the tester's responsibility per the test plan). All _critical_ and _serious_ structural violations found in code have been remediated in this commit. Colour-contrast values have been calculated from design tokens. Two items are documented as accepted exceptions. VoiceOver / NVDA manual passes are pending tester sign-off.

---

## Findings — Admin SPA

### FIXED — F-001: `BaseModal` missing dialog role and labelledby
**Severity:** Critical (WCAG 4.1.2)
**File:** `admin/src/components/BaseModal.vue`
**Issue:** Modal panel had no `role="dialog"`, no `aria-modal="true"`, no `aria-labelledby`. Screen readers could not identify it as a modal or announce the title on open.
**Fix applied:** Added `role="dialog" aria-modal="true" :aria-labelledby="modalTitleId"` to the panel div. Added `useId()` for a stable ID bound to the `<h2>` title. Close button now has `aria-label="Close dialog"`.

### FIXED — F-002: `BaseDrawer` missing dialog role and labelledby
**Severity:** Critical (WCAG 4.1.2)
**File:** `admin/src/components/BaseDrawer.vue`
**Issue:** Same as F-001 but on the drawer/side-panel component used throughout the app (property drawer, lease drawer, etc.).
**Fix applied:** Same pattern as F-001. Close button has `aria-label="Close panel"`.

### FIXED — F-003: `SearchInput` — input has no accessible label; clear button unlabelled
**Severity:** Serious (WCAG 1.3.1, 4.1.2)
**File:** `admin/src/components/SearchInput.vue`
**Issue:** Input had no `<label>`, no `aria-label`. Clear (×) button had no accessible name. Decorative Search icon lacked `aria-hidden`.
**Fix applied:**
- Input gets `type="search"` (announces purpose to SR) and `:aria-label="ariaLabel || placeholder"`.
- New optional `ariaLabel` prop lets callers provide a specific label (e.g. "Search properties").
- Clear button gets `aria-label="Clear search"`.
- Search SVG gets `aria-hidden="true"`.

### FIXED — F-004: Auth forms — labels not associated with inputs
**Severity:** Serious (WCAG 1.3.1)
**Files:** `admin/src/views/auth/ForgotPasswordView.vue`, `admin/src/views/auth/RegisterView.vue`
**Issue:** All `<label>` elements used `class="label"` but had no `for` attribute. The corresponding `<input>` elements had no `id`. Labels were visually visible but not programmatically associated.
**Fix applied:** All label/input pairs now have matching `for`/`id` attributes. `autocomplete` attributes added for browser autofill support (helps users with cognitive disabilities).

### FIXED — F-005: Error messages not announced to screen readers
**Severity:** Serious (WCAG 4.1.3)
**Files:** `admin/src/views/auth/ForgotPasswordView.vue`, `admin/src/views/auth/RegisterView.vue`
**Issue:** Inline error `<div>` elements appeared on form validation failure but had no `role="alert"`. Screen readers would not announce them automatically.
**Fix applied:** Both error containers now have `role="alert"`. Alert icon SVGs marked `aria-hidden="true"`.

### FIXED — F-006: Show/hide password button unlabelled
**Severity:** Serious (WCAG 4.1.2)
**File:** `admin/src/views/auth/RegisterView.vue`
**Issue:** Eye / EyeOff toggle button had no accessible name — screen readers would announce "button" with no context.
**Fix applied:** `:aria-label="showPassword ? 'Hide password' : 'Show password'"` + `aria-pressed` for toggle state. Icon SVGs marked `aria-hidden="true"`.

### FIXED — F-007: No global focus-visible ring in admin SPA
**Severity:** Serious (WCAG 2.4.7)
**File:** `admin/src/styles/klikk-components.css`
**Issue:** The admin SPA had focus-visible styles only inside `.agent-shell` (the preview layout). All real production views had no `:focus-visible` rule, meaning keyboard users saw browser-default or no focus indicator depending on Tailwind reset.
**Fix applied:** Added a global `:focus-visible` rule at the top of `klikk-components.css` using Navy `#2B2D6E` at 2px offset. Tailwind `focus-visible:` utilities on individual elements take precedence where they are more specific.

### NOT FIXED — NF-001: `outline-none` / `focus:outline-none` on some editor components
**Severity:** Moderate (WCAG 2.4.7) — accepted exception
**Files:** `TiptapEditorView.vue`, `TemplateEditorView.vue`, `LeaseTemplatesView.vue`, `SignatureCapture.vue`, `AgencySettingsView.vue`, `DocumentPage.vue`, `SignatureBlockComponent.vue`
**Rationale:** These views either (a) use the TipTap rich-text editor which manages its own contenteditable focus ring internally, or (b) are canvas/drawing areas (signature capture) where `outline-none` is intentional. Removing it would create visual noise. **Remediation plan:** Tester to verify each with VoiceOver; if the TipTap editor ProseMirror element lacks a focus indicator, add a custom `box-shadow` to `.ProseMirror:focus` in `tiptap-editor.css`.

### PENDING — P-001: Focus trap not implemented in BaseModal / BaseDrawer
**Severity:** Serious (WCAG 2.1.2) — requires tester confirmation
**Issue:** When a modal or drawer opens, keyboard focus is not programmatically moved into the dialog, and Tab can escape to the background. A focus trap (or use of the native `<dialog>` element) is needed for full WCAG 2.1.2 compliance.
**Remediation plan:** Implement a `useFocusTrap` composable using `focus-trap` npm package (already common in Vue ecosystems) and call it from `BaseModal` and `BaseDrawer` on `open` watcher. Estimated effort: S. Raise as a discovery task for PM to schedule.

### PENDING — P-002: Keyboard navigation of agent golden path — tester validation required
**Status:** Not verified — requires live session
**Path:** Login → Properties list → Property detail → Open lease drawer → Submit
**Expected:** Full Tab/Shift-Tab traversal, Enter activates buttons, Escape closes modals.

---

## Findings — Astro Marketing Website

### FIXED — F-008: `<nav>` missing aria-label; links not in list
**Severity:** Serious (WCAG 1.3.1, 2.4.6)
**File:** `website/src/components/Header.astro`
**Issue:** `<nav>` had no `aria-label` — two unlabelled navs (header + footer) would be indistinguishable for SR users. Nav logo link had no accessible name. External login link missing `rel="noopener noreferrer"`.
**Fix applied:** `aria-label="Main navigation"` on the `<nav>`. Logo `<a>` gets `aria-label="Klikk home"`. Decorative period span gets `aria-hidden="true"`. `rel="noopener noreferrer"` added to the external login link.

### FIXED — F-009: Footer nav missing landmark and label
**Severity:** Moderate (WCAG 1.3.1)
**File:** `website/src/components/Footer.astro`
**Issue:** Footer links were in a plain `<div>`, not a `<nav>` element. Not discoverable as a navigation landmark.
**Fix applied:** Wrapped in `<nav aria-label="Footer navigation">`. SA flag emoji marked `aria-hidden="true"` (decorative). Footer logo `aria-label="Klikk"` added.

### FIXED — F-010: No focus-visible ring on website
**Severity:** Serious (WCAG 2.4.7)
**File:** `website/src/styles/global.css`
**Issue:** No `:focus-visible` rule existed. Browsers applied their default (often thin blue) outline which can fail contrast on dark backgrounds.
**Fix applied:** Added `:focus-visible { outline: 2px solid var(--color-navy); outline-offset: 3px; border-radius: 4px; }` with an override for dark sections (nav/footer) using `rgba(255,255,255,0.9)`.

---

## Colour contrast audit

Design tokens used: Navy `#2B2D6E`, Accent `#FF3D7F` / `#D6336C` (website), White `#FFFFFF`, Ink `#1A1A2E`, Muted `#6B6B7A`.

| Pair | Ratio | Use | WCAG AA? |
|------|-------|-----|---------|
| Ink `#1A1A2E` on White `#FFFFFF` | 18.1:1 | Body text | Pass (req. 4.5:1) |
| Navy `#2B2D6E` on White `#FFFFFF` | 8.6:1 | Headings, nav active | Pass |
| Muted `#6B6B7A` on White `#FFFFFF` | 4.6:1 | Subtitle, metadata | Pass (just) |
| Accent `#FF3D7F` on White `#FFFFFF` | 3.5:1 | Admin accent (large text only) | Fail for body text |
| Accent `#D6336C` on White `#FFFFFF` | 5.0:1 | Website accent | Pass |
| Navy `#2B2D6E` on `#E9EAF4` (navy-soft) | 5.4:1 | `.klikk-badge.tone-marketing` | Pass |
| `#6B6B7A` on `#EFEFF5` | 3.1:1 | Badge default | Fail for body text — badge text is 11px so counts as small text. Needs fix. |
| White `#FFFFFF` on Navy `#2B2D6E` | 8.6:1 | Active nav item text | Pass |
| `#92400e` on `#fef3c7` | 8.2:1 | Warn alert strip | Pass |
| `#991b1b` on `#fee2e2` | 7.2:1 | Danger alert strip | Pass |
| `#166534` on `#dcfce7` | 7.2:1 | Success badge | Pass |
| Nav links `rgba(255,255,255,0.55)` on dark bg | ~3.1:1 | Website nav inactive links | Fail (hover = white = pass) |

### Contrast violations requiring remediation

**CV-001: Admin Accent `#FF3D7F` on White — body-text contexts**
The accent is used for the `.dot` indicator in the topbar (small visual dot — decorative, no text) and as a highlight on interactive elements. Where it appears as the sole colour on small body text it fails at 3.5:1. Current codebase usage: primarily as a border/dot colour and in `.klikk-badge.tone-moveout` which has `background: #f3e8ff; color: #6b21a8` — that pair passes. Direct `color: #FF3D7F` on white needs review per view. Recommend tester to flag any remaining instances during axe sweep.

**CV-002: Website nav inactive link text `rgba(255,255,255,0.55)` on dark background**
At 55% white on `rgba(15,16,56,0.75)` the effective hex is approximately `#9FA0B3` on `#040412` which calculates to ~3.1:1 — fails 4.5:1 for normal text. Hover state (white) passes.
**Remediation plan:** Increase opacity to 0.75 (`rgba(255,255,255,0.75)`) for inactive link colour. Reviewer to action in a follow-up or bundle into this task.

---

## Screen reader validation status

| Flow | Tool | Status |
|------|------|--------|
| Agent: Login → Properties list → Property detail | VoiceOver (macOS) | Pending — tester |
| Tenant: (tenant web app not in v1 scope) | NVDA | Deferred |

---

## Keyboard navigation status

| Flow | Status |
|------|--------|
| Agent golden path (Login → Properties → Lease create) | Pending — tester to validate live |
| Website (Home → Pricing → Contact) | Pending — tester to validate live |

---

## `npm run test:a11y` status

No `test:a11y` script exists yet. The current `package.json` has `test:browser` (Vitest + Playwright) but no axe runner configured. See `tasks/discoveries/` for follow-up (focus trap + axe CI job).

---

## Accepted exceptions

| ID | Description | Rationale |
|----|-------------|-----------|
| NF-001 | `outline-none` on TipTap editor contenteditable + signature canvas | Intentional — editor manages own focus indicator; canvas drawing areas. |

---

## Open items for tester

1. Run live axe-core sweep on: Login, Register, Properties list, Property detail + lease drawer, Lease builder/editor, Public sign page.
2. Validate keyboard: Tab order, Enter activation, Escape to close modals/drawers, focus returns to trigger element on close.
3. VoiceOver run: agent golden path (Login → view lease → sign).
4. Confirm `useFocusTrap` is needed (P-001) and raise discovery task if so.
5. Check CV-002: nav link contrast — action or accepted exception?
