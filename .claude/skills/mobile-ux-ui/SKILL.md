---
name: mobile-ux-ui
description: Platform-correct iOS (HIG) and Android (Material Design 3) UX/UI engineering for the Klikk Agent App (Quasar/Capacitor). Enforces exact specs from Apple HIG and Google Material Design 3 — typography scales, spacing systems, navigation patterns, component sizes, color tokens, motion curves, and touch target minimums.
---

# Mobile UX/UI — iOS HIG + Android Material Design 3

**Stack:** Quasar Framework v2 + Vue 3 + Capacitor (agent-app)
**Brand:** Primary `#2B2D6E` (navy) · Secondary `#FF3D7F` (pink)
**Design tokens file:** `agent-app/src/utils/designTokens.ts`
**Shared formatters:** `agent-app/src/utils/formatters.ts`
**Platform detection:** `agent-app/src/composables/usePlatform.ts`

---

## MANDATE

When building or reviewing mobile UI for the Klikk agent-app:

1. **Always detect platform** — use `usePlatform()` composable (`isIos`, `isAndroid`)
2. **Apply platform-correct specs** — iOS dimensions in points (pt), Android in density-independent pixels (dp)
3. **Never hardcode colors** — use `var(--q-primary)` in templates/CSS, `$primary` in SCSS
4. **Never hardcode sizes** — use tokens from `designTokens.ts`
5. **Respect safe areas** — iOS notch/Dynamic Island top, home indicator bottom (34pt)
6. **Touch targets** — iOS minimum 44×44pt · Android minimum 48×48dp

---

## Part 1: iOS Human Interface Guidelines (iOS 17/18)

### 1.1 Typography — San Francisco (SF Pro)

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
- Never hardcode pt sizes — use Quasar's `text-*` classes that auto-scale
- Tab bar labels = Caption 2 style (11pt / `font-size: 9.5px` in the agent-app)
- List item titles = Headline weight (semibold)
- Section group labels = Caption 2 + uppercase + letter-spacing (as in SettingsPage)

### 1.2 Spacing and Layout

**Base grid:** 8pt (use 4pt for fine adjustments)

| Context | Value |
|---------|-------|
| Horizontal page margin | 16–20pt |
| Standard padding | 16pt |
| Card inner padding | 12–16pt |
| List row height (minimum) | 44pt |
| Section gap | 16–24pt |

**Safe Area Insets (NEVER hardcode — always use `env(safe-area-inset-*)`):**
- iPhone 8 / SE: top 20pt, bottom 0pt
- iPhone X–13 (notch): top 44pt, bottom 34pt
- iPhone 14 Pro / 15 Pro (Dynamic Island): top ~59pt, bottom 34pt

In Quasar:
```scss
padding-bottom: env(safe-area-inset-bottom, 0px);
padding-top: env(safe-area-inset-top, 0px);
```

### 1.3 Navigation

**Navigation Bar:**
- Height: 44pt (portrait) / 32pt (landscape)
- Large Title variant: ~96pt when expanded, collapses to 44pt on scroll
- Back button: chevron + previous screen title (truncates to "Back")
- Title: centered default; use `text-weight-semibold` on iOS

**Tab Bar:**
- Height: 49pt + `safe-area-inset-bottom`
- Max 5 tabs (3–5 recommended)
- Icons: 22–25pt visual size
- Labels: 11pt (Caption 2)
- Selected: filled icon + primary color
- Unselected: outline icon + grey-500

**Quasar implementation:**
```html
<!-- Tab bar label style -->
<span class="agent-tab-label">{{ tab.label }}</span>
<!-- font-size: 9.5px; font-weight: 500 — matches iOS Caption 2 -->
```

**Sheets / Modals:**
- Always slides up from bottom (not centered on iOS)
- Use `q-dialog` with `position="bottom"` for bottom sheets
- Supports interactive dismiss (pull down)
- Shows parent view at reduced scale behind sheet
- Corner radius: 12–16pt on top corners

### 1.4 Component Sizes

**Buttons:**
- Touch target: 44×44pt minimum
- Full-width primary action: height ~50pt, `border-radius: 14pt` (:rounded on iOS)
- FAB: not idiomatic on iOS — omit or use only when truly needed
- Destructive: red text, not filled red button

**Text Inputs:**
- Height: 44pt minimum (touch target)
- Corner radius: 10pt (`:rounded="isIos"` in Quasar = `border-radius: 28px` — slightly over-rounded but acceptable)
- Focus border: primary color
- Error border: negative color

**Cards:**
- Corner radius: 12pt
- Border: `1px solid rgba(0,0,0,0.08)`
- No shadow (flat card with border is iOS standard)
- Padding: 12–16pt

**Lists:**
- Row height: 44pt minimum (one-line), 56pt+ (two-line)
- Separator: `0.5px solid rgba(0,0,0,0.12)` (hairline separator — iOS standard)
- Disclosure chevron: 8pt from trailing edge

**Avatars:**
- Profile: 48pt
- List item: 40pt
- Compact (within small list cells): 36pt

**Spinners / Loaders:**
- Full-page loader: 36px (`SPINNER_SIZE_PAGE`)
- Inline / tab loader: 24px (`SPINNER_SIZE_INLINE`)
- Use `q-spinner-dots` for consistency

**Empty States:**
- Icon: 48px (`EMPTY_ICON_SIZE`)
- Icon color: `grey-3`
- Title: Body text, grey-5
- CTA button below

### 1.5 iOS Color System

Use semantic color tokens — NEVER hardcode iOS system colors for UI elements.

| Token | Light | Dark | Quasar mapping |
|-------|-------|------|----------------|
| systemBlue (tint) | #007AFF | #0A84FF | `var(--q-primary)` (overridden to `#2B2D6E`) |
| systemRed | #FF3B30 | #FF453A | `var(--q-negative)` |
| systemGreen | #34C759 | #30D158 | `var(--q-positive)` |
| systemOrange | #FF9500 | #FF9F0A | `var(--q-warning)` |
| systemBackground | #FFFFFF | #000000 | white / dark-page |
| secondarySystemBackground | #F2F2F7 | #1C1C1E | `$surface` |
| label (primary text) | #000000 | #FFFFFF | `text-grey-9` / `text-white` |
| secondaryLabel | rgba(60,60,67,0.6) | — | `text-grey-6` |
| tertiaryLabel | rgba(60,60,67,0.3) | — | `text-grey-4` |

**Klikk overrides:**
- Primary (tint): `#2B2D6E` navy
- Secondary (accent): `#FF3D7F` pink

### 1.6 Materials and Blur (iOS)

iOS navigation bars, tab bars, and sheets use vibrancy/blur materials:

```scss
// Tab bar — matches iOS chrome material
background: rgba(255, 255, 255, 0.95);
backdrop-filter: saturate(180%) blur(20px);
-webkit-backdrop-filter: saturate(180%) blur(20px);
border-top: 0.5px solid rgba(0, 0, 0, 0.14);

// Navigation bar
background: rgba(255, 255, 255, 0.92);
backdrop-filter: saturate(180%) blur(20px);
-webkit-backdrop-filter: saturate(180%) blur(20px);
```

Material thickness reference:
- `.systemUltraThinMaterial` — most transparent (overlays on media)
- `.systemThinMaterial` — subtle separation
- `.systemMaterial` — default (sheets, cards)
- `.systemThickMaterial` — strong separation
- `.systemChromeMaterial` — nav bars, tab bars

### 1.7 iOS Animation

**Default:** ease-in-out, ~0.35s
**Spring (preferred):** `stiffness 1400 / damping 0.9` for snappy, `stiffness 300 / damping 0.9` for fluid

```css
/* iOS-feel transition */
transition: all 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94);

/* Spring-like via CSS */
transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
```

**Quasar transitions (agent-app):**
```typescript
// usePlatform.ts
enterTransition: 'fadeIn'   // iOS: fade
leaveTransition: 'fadeOut'
// Android: slideInRight / slideOutLeft
```

**Reduce Motion:** Always check `prefers-reduced-motion` — disable animations when set.

---

## Part 2: Android Material Design 3 (Material You)

### 2.1 Typography Scale — Roboto

| Style | Size | Weight | Line Height | Quasar equivalent |
|-------|------|--------|-------------|-------------------|
| Display Large | 57sp | 400 | 64sp | Rarely used in mobile apps |
| Display Medium | 45sp | 400 | 52sp | Hero headings only |
| Display Small | 36sp | 400 | 44sp | Large titles |
| Headline Large | 32sp | 400 | 40sp | Screen titles |
| Headline Medium | 28sp | 400 | 36sp | `text-h5` |
| Headline Small | 24sp | 400 | 32sp | `text-h6` |
| Title Large | 22sp | 400 | 28sp | Card titles |
| Title Medium | 16sp | 500 | 24sp | `text-subtitle1` |
| Title Small | 14sp | 500 | 20sp | `text-subtitle2` |
| Body Large | 16sp | 400 | 24sp | `text-body1` |
| Body Medium | 14sp | 400 | 20sp | `text-body2` |
| Body Small | 12sp | 400 | 16sp | `text-caption` |
| Label Large | 14sp | 500 | 20sp | Button text |
| Label Medium | 12sp | 500 | 16sp | Tab labels, chip text |
| Label Small | 11sp | 500 | 16sp | Small labels |

### 2.2 Spacing System

**Base unit:** 4dp (common increments: 4, 8, 12, 16, 24, 32, 48dp)

| Context | Value |
|---------|-------|
| Horizontal page margin | 16dp |
| Section gap | 16–24dp |
| Card padding | 16dp |
| Component internal padding | 8–12dp |
| List item padding | 16dp |

**Responsive columns:**
- Compact (< 600dp, phone portrait): 4 columns, 16dp margins, 8dp gutters
- Medium (600–840dp): 8 columns, 24dp margins, 16dp gutters
- Expanded (> 840dp, tablet): 12 columns, 24dp margins, 24dp gutters

### 2.3 Navigation

**Bottom Navigation Bar:**
- Container height: 80dp
- Icon: 24dp
- Active indicator: 64×32dp pill shape behind icon
- Label: Label Medium (12sp) — shown for all items
- Touch target: 48dp minimum

**Top App Bar:**
- Small (default): 64dp height, title left-aligned (`text-h6`)
- Center-aligned: 64dp, title centered
- Medium: 112dp expanded → 64dp scrolled
- Large: 152dp expanded → 64dp scrolled
- Use small/center-aligned for most agent-app screens

**FAB (Floating Action Button):**
- Standard: 56×56dp, icon 24dp, corner radius 16dp (Large)
- Extended: 56dp height, icon + label
- Color: secondary (`#FF3D7F`) — high contrast on most backgrounds
- Position: `bottom-right`, offset `[18, 88]` (above bottom nav)

**Quasar FAB on Android:**
```html
<q-page-sticky
  v-if="isAndroid && route.meta.showFab !== false"
  position="bottom-right"
  :offset="[18, 88]"
>
  <q-btn fab icon="add" color="secondary" />
</q-page-sticky>
```

**Drawer / Navigation Drawer:**
- Acceptable on Android (hamburger pattern)
- Width: 360dp or 85% of screen, whichever is smaller
- Not idiomatic on iOS — avoid

### 2.4 Component Sizes

**Buttons (all: 40dp height, full pill radius):**

| Type | Quasar prop | Use case |
|------|-------------|---------|
| Filled | `unelevated color="primary"` | Primary action |
| Filled Tonal | `unelevated color="secondary"` | Secondary action |
| Elevated | `color="primary"` (default Quasar) | When surface context needed |
| Outlined | `outline color="primary"` | Tertiary action |
| Text | `flat color="primary"` | Least emphasis |

- All have `border-radius: 20dp` (full pill on Android)
- On iOS: use `:rounded="isIos"` for pill shape
- Touch target: 48dp minimum (Quasar adds tap zone automatically)
- Always add icon (18dp) for primary actions when space allows

**Text Fields:**
- Height: 56dp
- Filled variant: top corners radius 4dp, no bottom radius
- Outlined variant: corner radius 4dp all corners
- Floating label: 12sp when active
- Input text: Body Large (16sp)
- Helper/error: 4dp gap below, Body Small (12sp)
- Quasar: `:rounded="isIos"` differentiates — on Android use `outlined`

**Cards (M3 types):**
- Elevated: `box-shadow: 0 1dp 3dp rgba(0,0,0,0.2)`, corner radius 12dp
- Filled: tonal surface bg, no shadow, 12dp radius
- Outlined: 1dp border, no shadow, 12dp radius
- Standard in agent-app: `border: 1px solid rgba(0,0,0,0.08); border-radius: 12px`

**Dialogs:**
- Corner radius: 28dp (ExtraLarge) — rounder than iOS
- Width: 280–560dp, centered
- Title: Headline Small (24sp)
- Action buttons: right-aligned text buttons

**Bottom Sheets:**
- Top corner radius: 28dp
- Handle: 4dp × 32dp, centered, 22dp from top
- Supports partial height (standard) and full-height modal variants

**Chips:**
- Height: 32dp
- Horizontal padding: 16dp
- Corner radius: 8dp (Small)

**Lists:**
- One-line item: 56dp
- Two-line item: 72dp
- Three-line item: 88dp
- Leading icon: 24dp in 40dp zone
- Horizontal padding: 16dp

**Avatars:**
- Profile: 48dp → `:size="AVATAR_PROFILE"`
- List item: 40dp → `:size="AVATAR_LIST"`
- Compact: 36dp → `:size="AVATAR_COMPACT"`

**Touch targets:** 48×48dp minimum — all interactive elements. Quasar adds 48dp tap zones automatically on icon buttons.

### 2.5 Color System — Material You

M3 uses color roles (tokens), not fixed named colors. Dynamic Color on Android 12+ generates palette from wallpaper. Always use Quasar's Quasar CSS vars which map to your brand tokens.

**Quasar → M3 role mapping:**

| M3 Role | Quasar token | Klikk value |
|---------|--------------|-------------|
| `primary` | `var(--q-primary)` | `#2B2D6E` |
| `on-primary` | white | `#FFFFFF` |
| `secondary` | `var(--q-secondary)` | `#FF3D7F` |
| `error` | `var(--q-negative)` | `#DB2828` |
| `success` | `var(--q-positive)` | `#21BA45` |
| `warning` | `var(--q-warning)` | `#F2C037` |
| `surface` | `$surface` | `#F5F5F8` |
| `on-surface` | `text-grey-9` | — |
| `outline` | `rgba(0,0,0,0.12)` | Card borders |
| `scrim` | `rgba(0,0,0,0.5)` | Modal overlays |

### 2.6 Elevation System (M3)

M3 uses **tonal color overlay** (not just shadows) to express elevation:

| Level | Shadow | Tonal overlay | Typical use |
|-------|--------|---------------|-------------|
| 0 | 0dp | 0% | Cards (flat), text fields |
| 1 | 1dp | 5% | Elevated cards, menus |
| 2 | 3dp | 8% | Navigation drawer |
| 3 | 6dp | 11% | Modal bottom sheets |
| 4 | 8dp | 12% | Navigation bars (scrolled) |
| 5 | 12dp | 14% | FAB, dialogs |

In dark mode, use more tonal overlay (less harsh shadows).

### 2.7 Shape Scale

| Token | Radius | Used for |
|-------|--------|---------|
| ExtraSmall | 4dp | Text fields, snackbars |
| Small | 8dp | Chips, menu items |
| Medium | 12dp | Cards |
| Large | 16dp | Buttons, nav rail indicators |
| ExtraLarge | 28dp | FAB, dialogs, bottom sheets |
| Full | 50% | All standard buttons |

In the agent-app, use `border-radius: 12px` for cards, `border-radius: 28px` for pill buttons (`:rounded`).

### 2.8 Motion System (M3)

**Easing curves:**

| Curve | Bezier | Duration range | Use case |
|-------|--------|---------------|---------|
| Standard | `0.2, 0, 0, 1` | 200–500ms | Elements staying on screen |
| Standard Decelerate | `0, 0, 0, 1` | 250–400ms | Elements entering screen |
| Standard Accelerate | `0.3, 0, 1, 1` | 200–350ms | Elements leaving screen |
| Emphasized Decelerate | `0.05, 0.7, 0.1, 1` | 400–600ms | Large elements entering (sheets, drawers) |
| Emphasized Accelerate | `0.3, 0, 0.8, 0.15` | 200–350ms | Large elements exiting |
| Linear | `0, 0, 1, 1` | — | Continuous effects (progress, color) |

**Duration tokens:**

| Duration | Value | Typical use |
|----------|-------|-------------|
| Short 1–4 | 50–200ms | Small component changes (ripple, icon swap) |
| Medium 1–4 | 250–400ms | Standard transitions (page enter/exit) |
| Long 1–4 | 450–600ms | Large component transitions |
| Extra Long 1–4 | 700–1000ms | Full-screen complex sequences |

**Ripple effect (Android):**
- All touchable surfaces show ripple on press
- Ripple color: `on-surface` at ~12% opacity for press
- Bounded for contained elements (buttons, cards)
- Unbounded for icon buttons
- Quasar adds `v-ripple` directive automatically to `q-btn`, `q-item`, etc.

**Spring parameters:**

| Preset | Damping | Stiffness | Use case |
|--------|---------|-----------|---------|
| FastSpatial | 0.9 | 1400 | Chips, FAB tap response |
| DefaultSpatial | 0.9 | 700 | Cards, bottom sheets |
| SlowSpatial | 0.9 | 300 | Full-screen page transitions |

---

## Part 3: Quasar/Capacitor Implementation Guide

### 3.1 Platform Detection

```typescript
// composables/usePlatform.ts
import { computed } from 'vue'
import { useQuasar } from 'quasar'

export function usePlatform() {
  const $q = useQuasar()
  const isIos     = computed(() => $q.platform.is.ios)
  const isAndroid = computed(() => $q.platform.is.android)
  // ...
}
```

**Usage pattern:**
```html
<!-- Rounded inputs/buttons on iOS, standard on Android -->
<q-input :rounded="isIos" outlined />
<q-btn :rounded="isIos" unelevated />
```

### 3.2 Navigation Patterns by Platform

| Pattern | iOS | Android |
|---------|-----|---------|
| Back navigation | Swipe right from left edge + nav bar back btn | System gesture (bottom swipe) + optional back btn |
| Primary nav | Tab bar (bottom, 3–5 tabs, always visible) | Bottom nav bar (3–5 items) |
| FAB | Avoid | First-class, standard secondary action |
| Drawer / hamburger | Avoid | Acceptable for auxiliary navigation |
| Modal presentation | Sheet (slides from bottom) | Dialog (centered) or Bottom Sheet |
| Page transition | Fade (feels native on iOS) | Slide right / left |

### 3.3 Critical Platform Behaviors

**iOS Keyboard:**
- View shifts up when keyboard appears — test all forms with keyboard open
- Bottom-pinned inputs fail if not using safe area correctly
- Use `@capacitor/keyboard` plugin for fine-grained control:
  ```typescript
  Keyboard.addListener('keyboardWillShow', info => { /* adjust layout */ })
  Keyboard.addListener('keyboardDidHide', () => { /* restore */ })
  ```

**Android Keyboard:**
- Configure `windowSoftInputMode` in `AndroidManifest.xml`
- `adjustResize` (default) resizes layout — content shifts up
- `adjustPan` pans view without resize

**iOS Safe Areas:**
```scss
// Always in your page/layout CSS
padding-top: env(safe-area-inset-top, 0px);
padding-bottom: env(safe-area-inset-bottom, 0px);
padding-left: env(safe-area-inset-left, 0px);
padding-right: env(safe-area-inset-right, 0px);
```

**Android Back Button:**
```typescript
// Always handle hardware back
import { App } from '@capacitor/app'
App.addListener('backButton', ({ canGoBack }) => {
  if (!canGoBack) { App.exitApp() }
  else { router.back() }
})
```

**Status Bar:**
- iOS: always overlays content (use safe area top inset)
- Android: configure in `@capacitor/status-bar`:
  ```typescript
  StatusBar.setStyle({ style: Style.Light })
  StatusBar.setBackgroundColor({ color: '#2B2D6E' })
  ```

**Dark Mode:**
- Never hardcode colors — always use `var(--q-primary)`, `$primary`, Quasar color classes
- Test UI in both light and dark system mode
- Quasar's dark mode plugin: `$q.dark.isActive`

**Scroll Behavior:**
- iOS: momentum (rubber-band) scrolling — never inhibit with CSS `overflow: hidden` on scroll containers
- Android: edge overscroll effect — use `overscroll-behavior: contain` if needed

### 3.4 Icon Usage

| Platform | Preferred icon set | Import |
|----------|--------------------|--------|
| iOS feel | Ionicons v7 | `@quasar/extras/ionicons-v7` |
| Android / Material | Material Icons | `@quasar/extras/material-icons` |
| Universal | Material Symbols Outlined | `@quasar/extras/material-symbols-outlined` |

**Icon sizes:**
- Navigation bar icons: 22–24dp/pt
- List item leading icons: 24dp/pt
- Button icons: 18–20dp/pt
- FAB icon: 24dp/pt
- Tab bar icons: 22dp/pt

### 3.5 Design Tokens in Code

```typescript
// agent-app/src/utils/designTokens.ts
export const SPINNER_SIZE_PAGE   = '36px'   // Full-page loaders
export const SPINNER_SIZE_INLINE = '24px'   // Tab/inline loaders
export const EMPTY_ICON_SIZE     = '48px'   // Empty state icons
export const AVATAR_PROFILE      = '48px'   // Profile/prospect avatars
export const AVATAR_LIST         = '40px'   // Standard list avatars
export const AVATAR_COMPACT      = '36px'   // Compact list avatars
```

### 3.6 CSS / SCSS Rules

```scss
// Use — CSS custom property (unscoped <style> or template)
color: var(--q-primary);
background: rgba(var(--q-primary-rgb, 43, 45, 110), 0.08);

// Use — SCSS variable (scoped <style lang="scss"> blocks)
color: $primary;
border-color: rgba($primary, 0.08);
background: $surface;

// Never — hardcoded brand hex in any style block
color: #2B2D6E;    // BAD
color: #FF3D7F;    // BAD
```

**Card border standard:**
```scss
border: 1px solid rgba(0, 0, 0, 0.08);  // All cards — consistent
border-radius: 12px;
overflow: hidden;
```

**Shared `.section-card` class** (in `app.scss` — do NOT redefine in scoped styles):
```scss
.section-card {
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  overflow: hidden;
  margin-bottom: 16px;
}
```

---

## Part 4: Cross-Platform Comparison Reference

### Typography quick-map

| iOS Style | Size | Android Style | Size |
|-----------|------|---------------|------|
| Large Title | 34pt | Headline Large | 32sp |
| Title 1 | 28pt | Headline Medium | 28sp |
| Title 2 | 22pt | Title Large | 22sp |
| Headline | 17pt (semibold) | Title Medium | 16sp (500) |
| Body | 17pt | Body Large | 16sp |
| Caption 1 | 12pt | Body Small | 12sp |
| Caption 2 | 11pt | Label Medium | 12sp |

### Component size quick-map

| Component | iOS | Android |
|-----------|-----|---------|
| Touch target minimum | 44×44pt | 48×48dp |
| Button height | ~50pt (full-width) | 40dp |
| Text field height | 44pt | 56dp |
| List row (1-line) | 44pt | 56dp |
| List row (2-line) | 56pt+ | 72dp |
| Tab bar height | 49pt + safe area | 80dp |
| Navigation bar | 44pt | 64dp |
| FAB | Rare | 56dp standard |
| Card corner radius | 12pt | 12dp (Medium) |
| Modal corner radius | 12–16pt (top) | 28dp (top, ExtraLarge) |
| Chip height | — | 32dp |

### Navigation paradigm difference

| Aspect | iOS | Android |
|--------|-----|---------|
| Back | Swipe from left edge | Bottom gesture / system back |
| Primary nav | Tab bar (always visible) | Bottom nav (80dp) |
| Secondary | Push navigation stack | Same + system back |
| Overflow | "More" tab (avoid >5 tabs) | Navigation drawer |
| Search | Nav bar search field | Top app bar search |
| FAB | Rare, non-idiomatic | First-class, primary action |

---

## Part 5: UX Quality Checklist

Before shipping any mobile screen, verify:

### iOS
- [ ] Touch targets ≥ 44×44pt (all buttons, links, list rows)
- [ ] Safe area insets applied (top and bottom)
- [ ] Tab bar uses blur material (`backdrop-filter: blur(20px)`)
- [ ] Navigation bar has correct height (44pt)
- [ ] Modal presented as bottom sheet (not centered dialog)
- [ ] Back gesture works (swipe from left)
- [ ] No FAB unless explicitly justified
- [ ] Keyboard doesn't cover input fields
- [ ] Large title used only on top-level screens
- [ ] Icon set is Ionicons (iOS feel) or Material Symbols
- [ ] Spring physics for interactive animations

### Android
- [ ] Touch targets ≥ 48×48dp (all interactive elements)
- [ ] Ripple effect on all touchable surfaces (Quasar adds automatically)
- [ ] FAB present for primary creation action
- [ ] Bottom navigation bar height 80dp
- [ ] Hardware back button handled
- [ ] Status bar color/style configured
- [ ] Buttons are pill-shaped (full radius)
- [ ] Bottom sheets use 28dp top corner radius
- [ ] Elevation expressed via tonal color overlay (not just shadow)
- [ ] Snackbar for transient feedback (not alerts)

### Both Platforms
- [ ] No hardcoded hex colors for brand/semantic colors
- [ ] No hardcoded size values — use design tokens
- [ ] Empty states have icon (48px) + message + CTA
- [ ] Loading states use spinner tokens (36px page, 24px inline)
- [ ] Avatars use correct size token for context
- [ ] Card borders are `rgba(0,0,0,0.08)` consistently
- [ ] Dark mode tested (system colors adapt automatically)
- [ ] Large text / accessibility font sizes tested
- [ ] `prefers-reduced-motion` respected
- [ ] Error states shown inline below fields (not alerts for validation)

---

## References

- Apple Human Interface Guidelines: https://developer.apple.com/design/human-interface-guidelines/designing-for-ios
- Apple HIG Typography: https://developer.apple.com/design/human-interface-guidelines/typography
- Apple HIG SF Symbols: https://developer.apple.com/design/human-interface-guidelines/sf-symbols
- Material Design 3 Overview: https://m3.material.io/
- M3 Typography: https://m3.material.io/styles/typography/overview
- M3 Layout: https://m3.material.io/foundations/layout/understanding-layout/overview
- M3 Motion: https://m3.material.io/styles/motion/overview
- M3 Color: https://m3.material.io/styles/color/overview
- Quasar Framework (Capacitor): https://quasar.dev/quasar-cli-vite/developing-capacitor-apps/introduction
