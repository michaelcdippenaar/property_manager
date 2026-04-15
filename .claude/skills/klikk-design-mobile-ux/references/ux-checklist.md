# UX Quality Checklist — Mobile

Before shipping any mobile screen, verify all applicable items.

---

## Klikk Design Standard

- [ ] No hardcoded hex colors — using `var(--klikk-*)`, `var(--q-*)`, or `$primary` etc.
- [ ] Card borders use `var(--klikk-border)` and `var(--klikk-radius-card)`
- [ ] Section headers use `.section-header` class (not inline styles)
- [ ] Empty states use `.empty-state` class with icon + title + sub + CTA
- [ ] All validation rules imported from `RULES` (not inline `v => !!v || 'Required'`)
- [ ] Currency formatted with `formatZAR()` (not inline `toLocaleString`)
- [ ] Labels formatted with `fmtLabel()` (not inline `.replace()`)
- [ ] Every `catch` block shows `$q.notify()` feedback — no silent failures
- [ ] Icon-only buttons have `aria-label`
- [ ] Images have `alt` text
- [ ] `:focus-visible` styling not suppressed

---

## iOS

- [ ] Touch targets >= 44×44pt
- [ ] Safe area insets applied (top and bottom)
- [ ] Tab bar uses frosted glass (`.ios-tab-bar`)
- [ ] No FAB unless explicitly justified
- [ ] Keyboard doesn't cover input fields
- [ ] `:rounded="isIos"` on buttons and inputs where appropriate

---

## Android

- [ ] Touch targets >= 48×48dp
- [ ] FAB present for primary creation action
- [ ] Bottom navigation bar height 80dp
- [ ] Hardware back button handled
- [ ] Ripple effect on touchable surfaces (automatic via Quasar)
- [ ] Buttons are pill-shaped (full radius)

---

## Both Platforms

- [ ] Loading states use spinner tokens (`SPINNER_SIZE_PAGE` / `SPINNER_SIZE_INLINE`)
- [ ] Avatars use correct size token for context
- [ ] `prefers-reduced-motion` respected
- [ ] `hide-bottom-space` on stacked form inputs to prevent uneven spacing
- [ ] Forms use `q-form` with `ref` for `.validate()` on submit
- [ ] Submit buttons show `:loading="submitting"` state
