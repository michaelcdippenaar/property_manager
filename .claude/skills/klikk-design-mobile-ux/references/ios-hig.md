# iOS Human Interface Guidelines (iOS 17/18)

Reference: https://developer.apple.com/design/human-interface-guidelines/designing-for-ios

---

## Typography — San Francisco (SF Pro)

| Style | Size | Weight | Usage |
|-------|------|--------|-------|
| Large Title | 34pt | Regular | Page/screen titles (large) |
| Title 1 | 28pt | Regular | Primary section headings |
| Title 2 | 22pt | Regular | Secondary headings |
| Title 3 | 20pt | Regular | Tertiary headings |
| Headline | 17pt | Semibold | List item titles, card titles |
| Body | 17pt | Regular | Default content text |
| Callout | 16pt | Regular | Supplementary body content |
| Subheadline | 15pt | Regular | Supporting text, captions |
| Footnote | 13pt | Regular | Fine print, hints |
| Caption 1 | 12pt | Regular | Labels, secondary captions |
| Caption 2 | 11pt | Regular | Tab bar labels, tertiary info |

**Rules:**
- Tab bar labels = Caption 2 style (11pt / `font-size: 9.5px` in the agent-app)
- List item titles = Headline weight (semibold)
- Section group labels = `.section-header` class (12px uppercase with letter-spacing)

---

## Spacing and Layout

**Base grid:** 8pt (use 4pt for fine adjustments)

| Context | Value |
|---------|-------|
| Horizontal page margin | 16-20pt |
| Standard padding | 16pt |
| Card inner padding | 12-16pt |
| List row height (minimum) | 44pt |
| Section gap | 16-24pt |

**Safe Area Insets — NEVER hardcode, always use `env(safe-area-inset-*)`:**
```scss
padding-bottom: env(safe-area-inset-bottom, 0px);
padding-top: env(safe-area-inset-top, 0px);
```

---

## Navigation

**Navigation Bar:**
- Height: 44pt (portrait) / 32pt (landscape)
- Title: centered, `text-weight-semibold`
- Frosted glass: `.ios-header` class in `app.scss`

**Tab Bar:**
- Height: 49pt + `safe-area-inset-bottom`
- Max 5 tabs (3-5 recommended)
- Icons: 22-25pt, Labels: 11pt (Caption 2)
- Selected: filled icon + `$primary`, Unselected: outline + `var(--klikk-text-muted)`
- Frosted glass: `.ios-tab-bar` class in `app.scss`

**Sheets / Modals:**
- Always slides up from bottom (`q-dialog` with `position="bottom"`)
- Corner radius: 12-16pt on top corners

---

## Component Sizes

**Buttons:**
- Touch target: **44×44pt minimum**
- Full-width primary action: height ~48pt, `border-radius: 10px` (iOS), `size="md"`
- Destructive: red text, not filled red button

**Text Inputs:**
- Height: 44pt minimum
- Corner radius: `var(--klikk-radius-input)` (10px)
- Use `hide-bottom-space` when stacking inputs to prevent uneven spacing

**Cards:**
- Corner radius: `var(--klikk-radius-card)` (12px)
- Border: `1px solid var(--klikk-border)`
- No shadow (flat with border is iOS standard)

**Lists:**
- Separator: `0.5px solid rgba(0,0,0,0.12)` (hairline)
- Disclosure chevron: 8pt from trailing edge

---

## Color System

Use semantic tokens — never hardcode iOS system colors:

| iOS | Quasar mapping |
|-----|----------------|
| systemBlue (tint) | `var(--q-primary)` (`#2B2D6E`) |
| systemRed | `var(--q-negative)` |
| systemGreen | `var(--q-positive)` |
| systemOrange | `var(--q-warning)` |
| secondarySystemBackground | `$surface` |

---

## Materials and Blur

```scss
// Tab bar — iOS chrome material
background: rgba(255, 255, 255, 0.92);
backdrop-filter: saturate(180%) blur(20px);
-webkit-backdrop-filter: saturate(180%) blur(20px);
border-top: 0.5px solid var(--klikk-border-strong);
```

---

## Animation

- **Default:** ease-in-out, ~0.35s
- **Quasar transitions:** `fadeIn` / `fadeOut` for iOS (set in `usePlatform.ts`)
- **Reduce Motion:** Always respect `prefers-reduced-motion`

---

## iOS Checklist

- [ ] Touch targets >= 44×44pt
- [ ] Safe area insets applied (top and bottom)
- [ ] Tab bar uses frosted glass (`.ios-tab-bar`)
- [ ] No FAB unless explicitly justified
- [ ] Keyboard doesn't cover input fields
- [ ] `:rounded="isIos"` on buttons and inputs where appropriate
