---
name: klikk-design-mobile-ux
description: Platform-correct iOS (HIG) and Android (Material Design 3) UX/UI engineering for the Klikk Agent App and Tenant App (Quasar/Capacitor). Enforces exact specs from Apple HIG and Google Material Design 3, plus the Klikk design standard — CSS custom properties, shared utilities, reusable component classes, error handling, and accessibility. Use this skill whenever building or modifying any mobile UI in agent-app or tenant-app, even for small changes like adding a button or fixing spacing.
---

# Mobile UX/UI — iOS HIG + Android Material Design 3

**Stack:** Quasar Framework v2 + Vue 3 + Capacitor (`agent-app`, `tenant-app`)
**Brand:** Primary `#2B2D6E` (navy) · Accent `#FF3D7F` (pink)
**Platform detection:** `agent-app/src/composables/usePlatform.ts`

---

## When to use this vs related skills

| Instead of | Use this when |
|------------|---------------|
| `klikk-design-standard` | Building mobile screens (Quasar), not admin Vue |
| `klikk-design-frontend-taste` | Need architecture/UX quality review for mobile |

---

## Reference Index

| Topic | File |
|-------|------|
| CSS custom properties, SCSS tokens, designTokens.ts, formatters, CSS classes, error handling, accessibility | [klikk-design-tokens.md](references/klikk-design-tokens.md) |
| iOS HIG — typography, spacing, navigation, component sizes, colors, materials, animation | [ios-hig.md](references/ios-hig.md) |
| Android Material Design 3 — typography, spacing, navigation, components, colors, elevation, motion | [android-md3.md](references/android-md3.md) |
| Platform detection, navigation patterns, critical behaviors, icon usage, cross-platform size tables | [platform-detection.md](references/platform-detection.md) |
| Pre-ship UX checklist (Klikk standard + iOS + Android + both) | [ux-checklist.md](references/ux-checklist.md) |

---

## Mandatory Rules (apply to every change)

1. **Always detect platform** — use `usePlatform()` (`isIos`, `isAndroid`)
2. **Apply platform-correct specs** — iOS in points (pt), Android in dp
3. **Never hardcode colors** — use `var(--klikk-*)` / `var(--q-primary)` in templates, `$primary` in SCSS
4. **Never hardcode sizes** — use tokens from `designTokens.ts`
5. **Respect safe areas** — iOS notch top, home indicator bottom (34pt)
6. **Touch targets** — iOS min 44×44pt · Android min 48×48dp
7. **Never silent catches** — every API call must show `$q.notify()` on error
8. **Use shared utilities** — never duplicate `formatZAR`, `fmtLabel`, `RULES`, or status functions
9. **Accessibility** — `aria-label` on all icon-only buttons

---

## Quick Workflow

1. Read [klikk-design-tokens.md](references/klikk-design-tokens.md) for Klikk-specific tokens and CSS classes
2. Read [ios-hig.md](references/ios-hig.md) if building iOS-specific UI
3. Read [android-md3.md](references/android-md3.md) if building Android-specific UI
4. Read [platform-detection.md](references/platform-detection.md) for cross-platform component implementation
5. Before shipping, run through [ux-checklist.md](references/ux-checklist.md)
