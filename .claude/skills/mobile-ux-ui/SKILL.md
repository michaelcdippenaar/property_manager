---
name: mobile-ux-ui
description: Platform-correct iOS (HIG) and Android (Material Design 3) UX/UI engineering for the Klikk Agent App and Tenant App (Quasar/Capacitor). Enforces exact specs from Apple HIG and Google Material Design 3, plus the Klikk design standard — CSS custom properties, shared utilities, reusable component classes, error handling, and accessibility. Use this skill whenever building or modifying any mobile UI in agent-app or tenant-app, even for small changes like adding a button or fixing spacing.
---

# Mobile UX/UI — iOS HIG + Android Material Design 3

**Stack:** Quasar Framework v2 + Vue 3 + Capacitor (agent-app, tenant-app)
**Brand:** Primary `#2B2D6E` (navy) · Secondary `#0D9488` (teal)
**Design tokens file:** `agent-app/src/utils/designTokens.ts`
**Shared formatters:** `agent-app/src/utils/formatters.ts`
**Global styles:** `agent-app/src/css/app.scss`
**SCSS variables:** `agent-app/src/css/quasar.variables.scss`
**Platform detection:** `agent-app/src/composables/usePlatform.ts`

---

## MANDATE

When building or reviewing mobile UI for the Klikk agent-app or tenant-app:

1. **Always detect platform** — use `usePlatform()` composable (`isIos`, `isAndroid`)
2. **Apply platform-correct specs** — iOS dimensions in points (pt), Android in density-independent pixels (dp)
3. **Never hardcode colors** — use CSS custom properties (`var(--klikk-*)`, `var(--q-primary)`) in templates, `$primary` in SCSS
4. **Never hardcode sizes** — use tokens from `designTokens.ts`
5. **Respect safe areas** — iOS notch/Dynamic Island top, home indicator bottom (34pt)
6. **Touch targets** — iOS minimum 44x44pt · Android minimum 48x48dp
7. **Never silent catches** — every API call must have error feedback via `$q.notify()`
8. **Use shared utilities** — never duplicate `formatZAR`, `fmtLabel`, `RULES`, or status color functions
9. **Accessibility** — `aria-label` on all icon-only buttons, `:focus-visible` styling respected

---

## Part 1: Klikk Design Standard (CSS Custom Properties + Shared Utilities)

This section defines the Klikk-specific design tokens and patterns that sit on top of the platform specs. These are enforced across ALL pages in both apps.

### 1.1 CSS Custom Properties (`app.scss :root`)

All UI colors that are not Quasar brand tokens (`$primary`, `$positive`, etc.) must use these CSS custom properties. Never hardcode hex values or `rgba()` for borders, text, or backgrounds that have a token.

```scss
:root {
  --klikk-border: rgba(0, 0, 0, 0.08);         // Card borders, separators
  --klikk-border-strong: rgba(0, 0, 0, 0.14);  // Tab bar top border, strong dividers
  --klikk-radius-card: 12px;                    // All cards
  --klikk-radius-input: 10px;                   // Input fields (iOS)
  --klikk-radius-btn: 16px;                     // Buttons
  --klikk-text-primary: #1a1a2e;                // Primary text (headings, input values)
  --klikk-text-secondary: #6b7280;              // Secondary text (labels, section headers)
  --klikk-text-muted: #9e9e9e;                  // Muted text (hints, inactive tabs)
  --klikk-text-faint: #bdbdbd;                  // Faint text (placeholders, empty state subs)
  --klikk-chat-bg: #efeae2;                     // Chat message area background
  --klikk-chat-sent: #d4f0ed;                   // Sent message bubble
  --klikk-chat-received: #ffffff;               // Received message bubble
  --klikk-empty-text: #9e9e9e;                  // Empty state title text
}
```

**When to use which:**
- Card/component borders: `var(--klikk-border)` — NOT `rgba(0,0,0,0.08)` inline
- Card border-radius: `var(--klikk-radius-card)` — NOT `12px` inline
- Input border-radius: `var(--klikk-radius-input)` — NOT `10px` inline
- Tab bar / nav borders: `var(--klikk-border-strong)`
- Form labels, section headers: `var(--klikk-text-secondary)`
- Input text, headings: `var(--klikk-text-primary)`
- Placeholders, hints: `var(--klikk-text-faint)`
- Inactive tab icons: `var(--klikk-text-muted)`

### 1.2 SCSS Brand Tokens (`quasar.variables.scss`)

These are the Quasar brand variables used in `<style lang="scss">` blocks:

```scss
$primary:   #2B2D6E;   // Klikk Navy
$secondary: #0D9488;   // Klikk Teal (accent)
$accent:    #0D9488;
$dark:      #1A1B44;
$surface:   #F5F5F8;   // Page background
$positive:  #21BA45;
$negative:  #DB2828;
$info:      #31CCEC;
$warning:   #F2C037;
```

**Rules:**
- In `<style lang="scss">` scoped blocks: use `$primary`, `rgba($primary, 0.12)`, etc.
- In `<template>` inline styles or unscoped CSS: use `var(--q-primary)`, `var(--klikk-text-primary)`, etc.
- Never write `color: #2B2D6E` or `color: #0D9488` anywhere.

### 1.3 Design Tokens (`designTokens.ts`)

Central file for all reusable constants and utilities. Import from here — never redefine these values.

```typescript
// Sizing constants
export const SPINNER_SIZE_PAGE   = '36px'   // Full-page loaders
export const SPINNER_SIZE_INLINE = '24px'   // Tab/inline loaders
export const EMPTY_ICON_SIZE     = '48px'   // Empty state icons
export const AVATAR_PROFILE      = '48px'   // Profile/prospect avatars
export const AVATAR_LIST         = '40px'   // Standard list avatars
export const AVATAR_COMPACT      = '36px'   // Compact list avatars

// Shared validation rules — use in ALL forms, never write inline rules
export const RULES = {
  required:       (v: unknown) => !!v || 'Required',
  requiredSelect: (v: unknown) => !!v || 'Please select an option',
  positiveNumber: (v: unknown) => (!!v && Number(v) > 0) || 'Enter a valid amount',
  email:          (v: string) => !v || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) || 'Enter a valid email',
} as const

// Currency formatter — never use inline toLocaleString for ZAR
export function formatZAR(amount: string | number): string {
  return Number(amount).toLocaleString('en-ZA')
}
```

**Usage in forms:**
```html
<!-- GOOD — shared rules -->
<q-input :rules="[RULES.required]" />
<q-input :rules="[RULES.positiveNumber]" type="number" prefix="R" />
<q-select :rules="[RULES.requiredSelect]" />

<!-- BAD — inline rules (duplicated across pages) -->
<q-input :rules="[v => !!v || 'Required']" />
```

**Usage for currency:**
```html
<!-- GOOD -->
R{{ formatZAR(lease.monthly_rent) }}

<!-- BAD -->
R{{ Number(lease.monthly_rent).toLocaleString('en-ZA') }}
```

### 1.4 Shared Formatters (`formatters.ts`)

Import these — never duplicate in page components:

| Function | Purpose | Example |
|----------|---------|---------|
| `formatDate(iso)` | Short date | "10 Apr 2026" |
| `formatDateTime(iso)` | Full date-time | "Thursday, 10 April, 09:00" |
| `formatDateTimeShort(iso)` | Short date-time | "Thu, 10 Apr, 09:00" |
| `formatTime(iso)` | Time only | "09:00" |
| `timeAgo(iso)` | Relative time | "2h ago" |
| `daysRemaining(iso)` | Days until date | `45` or `null` |
| `fmtLabel(value)` | Snake_case to display | "in_progress" -> "In Progress" |
| `statusColor(status)` | Viewing status -> Quasar color | "scheduled" -> "info" |
| `statusIcon(status)` | Viewing status -> Material icon | "scheduled" -> "event" |
| `statusDotColor(status)` | Calendar dot color | Uses `var(--q-*)` CSS vars |
| `leaseStatusColor(status)` | Lease status -> Quasar color | "active" -> "positive" |
| `unitStatusColor(status)` | Unit status -> Quasar color | "available" -> "positive" |
| `maintenancePriorityColor(p)` | Priority -> Quasar color | "urgent" -> "negative" |
| `maintenanceStatusColor(s)` | Maintenance status -> color | "open" -> "info" |
| `maintenanceCategoryIcon(c)` | Category -> Material icon | "plumbing" -> "plumbing" |

### 1.5 Reusable CSS Classes (`app.scss`)

These global classes exist in `app.scss`. Use them instead of writing equivalent scoped styles.

#### `.section-card` — Standard card container
```scss
.section-card {
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-border);
  overflow: hidden;
  margin-bottom: 16px;
}
```
Usage: `<q-card flat class="section-card">`

#### `.section-header` — Section label above cards
```scss
.section-header {
  font-size: 12px;
  font-weight: 600;
  color: var(--klikk-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
  margin-left: 4px;
}
```
Usage: `<div class="section-header">Lease Terms</div>`

#### `.empty-state` — Consistent empty/zero-data states
```scss
.empty-state {
  text-align: center;
  padding: 40px 16px;
}
.empty-state-icon  { color: var(--klikk-text-faint); }
.empty-state-title { font-size: 14px; color: var(--klikk-empty-text); margin-top: 8px; }
.empty-state-sub   { font-size: 12px; color: var(--klikk-text-faint); margin-top: 4px; }
.empty-state-action { margin-top: 16px; }
```
Usage:
```html
<div class="empty-state">
  <q-icon name="event_busy" :size="EMPTY_ICON_SIZE" class="empty-state-icon" />
  <div class="empty-state-title">No viewings yet</div>
  <div class="empty-state-sub">Schedule a viewing to get started</div>
  <div class="empty-state-action">
    <q-btn unelevated color="primary" label="Book Viewing" icon="add" no-caps />
  </div>
</div>
```

#### `.prospect-badge` — Inline status badges
```html
<span class="prospect-badge status-scheduled">Scheduled</span>
<span class="prospect-badge status-confirmed">Confirmed</span>
<span class="prospect-badge status-completed">Completed</span>
<span class="prospect-badge status-cancelled">Cancelled</span>
<span class="prospect-badge status-converted">Converted</span>
```

#### `.page-container` — Centered content wrapper
```scss
.page-container {
  padding: 16px;
  max-width: 600px;
  margin: 0 auto;
}
```

### 1.6 Error Handling (Mandatory)

**Every API call must have error feedback.** Never use a bare `catch {}` or `catch { /* ignore */ }`.

```typescript
// GOOD — user sees feedback on failure
try {
  property.value = await getProperty(props.propertyId)
} catch {
  $q.notify({ type: 'negative', message: 'Failed to load property details.', icon: 'error' })
}

// BAD — silent failure, user sees blank screen with no explanation
try {
  property.value = await getProperty(props.propertyId)
} catch {}
```

**Pattern for data loading on mount:**
```typescript
onMounted(async () => {
  try {
    data.value = await fetchData(props.id)
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to load data.', icon: 'error' })
  }
})
```

**Pattern for form submission:**
```typescript
async function submit() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  submitting.value = true
  submitError.value = ''

  try {
    await createThing(payload)
    $q.notify({ type: 'positive', message: 'Created successfully', icon: 'check_circle' })
    void router.replace('/destination')
  } catch (err: unknown) {
    const axiosErr = err as { response?: { data?: Record<string, unknown> } }
    const data = axiosErr.response?.data
    submitError.value = data
      ? Object.values(data).flat().join(' ')
      : 'Failed to create. Please try again.'
  } finally {
    submitting.value = false
  }
}
```

### 1.7 Accessibility

**Icon-only buttons must have `aria-label`:**
```html
<q-btn flat round dense icon="call" color="primary"
       :href="`tel:${phone}`" tag="a"
       aria-label="Call prospect" />

<q-btn flat round dense icon="chevron_left" color="primary"
       aria-label="Previous month" @click="prevMonth" />
```

**Dynamic aria-labels for toggle buttons:**
```html
<q-btn flat round dense
  :icon="showPassword ? 'visibility_off' : 'visibility'"
  :aria-label="showPassword ? 'Hide password' : 'Show password'"
  @click="showPassword = !showPassword"
/>
```

**Focus-visible styling** (already in `app.scss`):
```scss
:focus-visible {
  outline: 2px solid var(--q-primary);
  outline-offset: 2px;
}
```

**Image alt text:**
```html
<q-img :src="property.image_url" :alt="`Photo of ${property.name}`" />
```

---

## Part 2: iOS Human Interface Guidelines (iOS 17/18)

### 2.1 Typography — San Francisco (SF Pro)

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

### 2.2 Spacing and Layout

**Base grid:** 8pt (use 4pt for fine adjustments)

| Context | Value |
|---------|-------|
| Horizontal page margin | 16-20pt |
| Standard padding | 16pt |
| Card inner padding | 12-16pt |
| List row height (minimum) | 44pt |
| Section gap | 16-24pt |

**Safe Area Insets (NEVER hardcode — always use `env(safe-area-inset-*)`):**
```scss
padding-bottom: env(safe-area-inset-bottom, 0px);
padding-top: env(safe-area-inset-top, 0px);
```

### 2.3 Navigation

**Navigation Bar:**
- Height: 44pt (portrait) / 32pt (landscape)
- Title: centered, `text-weight-semibold`
- Uses frosted glass: `.ios-header` class in `app.scss`

**Tab Bar:**
- Height: 49pt + `safe-area-inset-bottom`
- Max 5 tabs (3-5 recommended)
- Icons: 22-25pt, Labels: 11pt (Caption 2)
- Selected: filled icon + `$primary`, Unselected: outline + `var(--klikk-text-muted)`
- Uses frosted glass: `.ios-tab-bar` class in `app.scss`

**Sheets / Modals:**
- Always slides up from bottom (`q-dialog` with `position="bottom"`)
- Corner radius: 12-16pt on top corners

### 2.4 Component Sizes

**Buttons:**
- Touch target: 44x44pt minimum
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

### 2.5 iOS Color System

Use semantic tokens — never hardcode iOS system colors:

| iOS | Quasar mapping |
|-----|----------------|
| systemBlue (tint) | `var(--q-primary)` (`#2B2D6E`) |
| systemRed | `var(--q-negative)` |
| systemGreen | `var(--q-positive)` |
| systemOrange | `var(--q-warning)` |
| secondarySystemBackground | `$surface` |

### 2.6 Materials and Blur

```scss
// Tab bar — iOS chrome material
background: rgba(255, 255, 255, 0.92);
backdrop-filter: saturate(180%) blur(20px);
-webkit-backdrop-filter: saturate(180%) blur(20px);
border-top: 0.5px solid var(--klikk-border-strong);
```

### 2.7 iOS Animation

**Default:** ease-in-out, ~0.35s
**Quasar transitions:** `fadeIn` / `fadeOut` for iOS (set in `usePlatform.ts`)
**Reduce Motion:** Always respect `prefers-reduced-motion`.

---

## Part 3: Android Material Design 3 (Material You)

### 3.1 Typography Scale — Roboto

| Style | Size | Weight | Quasar equivalent |
|-------|------|--------|-------------------|
| Headline Large | 32sp | 400 | Screen titles |
| Headline Medium | 28sp | 400 | `text-h5` |
| Title Large | 22sp | 400 | Card titles |
| Title Medium | 16sp | 500 | `text-subtitle1` |
| Body Large | 16sp | 400 | `text-body1` |
| Body Medium | 14sp | 400 | `text-body2` |
| Body Small | 12sp | 400 | `text-caption` |
| Label Large | 14sp | 500 | Button text |
| Label Medium | 12sp | 500 | Tab labels |

### 3.2 Spacing System

**Base unit:** 4dp (common increments: 4, 8, 12, 16, 24, 32, 48dp)

| Context | Value |
|---------|-------|
| Horizontal page margin | 16dp |
| Section gap | 16-24dp |
| Card padding | 16dp |
| List item padding | 16dp |

### 3.3 Navigation

**Bottom Navigation Bar:**
- Height: 80dp
- Active indicator: 64x32dp pill behind icon
- Uses `.md-bottom-nav` class in `app.scss`

**Top App Bar:**
- Height: 64dp
- Uses `.md-header` class in `app.scss`

**FAB (Floating Action Button):**
- 56x56dp, icon 24dp, corner radius 16dp
- Color: `$secondary` (teal)
- Position: `bottom-right`, offset `[18, 88]` (above bottom nav)

### 3.4 Component Sizes

**Buttons:** 40dp height, full pill radius (`border-radius: 20px`)
**Text Fields:** 56dp height, outlined with 4dp radius
**Cards:** `border-radius: 12dp`, `box-shadow: 0 1px 3px rgba(0,0,0,0.12)`
**Dialogs:** Corner radius 28dp (ExtraLarge)
**Touch targets:** 48x48dp minimum for all interactive elements

### 3.5 Color System

| M3 Role | Quasar token | Klikk value |
|---------|--------------|-------------|
| `primary` | `var(--q-primary)` | `#2B2D6E` |
| `secondary` | `var(--q-secondary)` | `#0D9488` |
| `error` | `var(--q-negative)` | `#DB2828` |
| `success` | `var(--q-positive)` | `#21BA45` |
| `warning` | `var(--q-warning)` | `#F2C037` |
| `surface` | `$surface` | `#F5F5F8` |

### 3.6 Elevation System (M3)

| Level | Shadow | Typical use |
|-------|--------|-------------|
| 0 | 0dp | Cards (flat), text fields |
| 1 | 1dp | Elevated cards, menus |
| 3 | 6dp | Modal bottom sheets |
| 5 | 12dp | FAB, dialogs |

### 3.7 Motion System

**Easing curves:**
- Standard: `cubic-bezier(0.2, 0, 0, 1)` — elements staying on screen
- Standard Decelerate: `cubic-bezier(0, 0, 0, 1)` — entering screen
- Standard Accelerate: `cubic-bezier(0.3, 0, 1, 1)` — leaving screen

**Quasar transitions:** `slideInRight` / `slideOutLeft` for Android (set in `usePlatform.ts`)
**Ripple:** Quasar adds `v-ripple` automatically to `q-btn`, `q-item`, etc.

---

## Part 4: Platform Detection and Implementation

### 4.1 Platform Detection

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
<q-input :rounded="isIos" outlined />
<q-btn :rounded="isIos" unelevated />
```

### 4.2 Navigation Patterns by Platform

| Pattern | iOS | Android |
|---------|-----|---------|
| Back navigation | Swipe right + nav bar back btn | System gesture + optional back btn |
| Primary nav | Tab bar (3-5 tabs, always visible) | Bottom nav bar (3-5 items) |
| FAB | Avoid | First-class primary action |
| Modal presentation | Sheet (slides from bottom) | Dialog (centered) or Bottom Sheet |
| Page transition | Fade | Slide right / left |

### 4.3 Critical Platform Behaviors

**iOS Keyboard:** View shifts up — test all forms with keyboard open. Use `@capacitor/keyboard` for control.

**iOS Safe Areas:**
```scss
padding-top: env(safe-area-inset-top, 0px);
padding-bottom: env(safe-area-inset-bottom, 0px);
```

**Android Back Button:**
```typescript
import { App } from '@capacitor/app'
App.addListener('backButton', ({ canGoBack }) => {
  if (!canGoBack) { App.exitApp() }
  else { router.back() }
})
```

**Status Bar:**
```typescript
StatusBar.setStyle({ style: Style.Light })
StatusBar.setBackgroundColor({ color: '#2B2D6E' })
```

**Scroll Behavior:**
- iOS: momentum (rubber-band) scrolling — never inhibit
- Android: edge overscroll — use `overscroll-behavior: contain` if needed

### 4.4 Icon Usage

| Platform | Preferred icon set |
|----------|--------------------|
| iOS feel | Ionicons v7 |
| Android / Material | Material Icons |
| Universal | Material Symbols Outlined |

Icon sizes: Nav 22-24dp, List leading 24dp, Button 18-20dp, FAB 24dp, Tab 22dp.

---

## Part 5: Cross-Platform Quick Reference

### Typography mapping

| iOS Style | Size | Android Style | Size |
|-----------|------|---------------|------|
| Large Title | 34pt | Headline Large | 32sp |
| Title 1 | 28pt | Headline Medium | 28sp |
| Title 2 | 22pt | Title Large | 22sp |
| Headline | 17pt (semibold) | Title Medium | 16sp (500) |
| Body | 17pt | Body Large | 16sp |
| Caption 1 | 12pt | Body Small | 12sp |
| Caption 2 | 11pt | Label Medium | 12sp |

### Component size mapping

| Component | iOS | Android |
|-----------|-----|---------|
| Touch target minimum | 44x44pt | 48x48dp |
| Button height | ~48pt (full-width) | 40dp |
| Text field height | 44pt | 56dp |
| List row (1-line) | 44pt | 56dp |
| Tab bar height | 49pt + safe area | 80dp |
| Navigation bar | 44pt | 64dp |
| Card corner radius | 12pt | 12dp |
| Modal corner radius | 12-16pt (top) | 28dp (ExtraLarge) |

---

## Part 6: UX Quality Checklist

Before shipping any mobile screen, verify:

### Klikk Design Standard
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

### iOS
- [ ] Touch targets >= 44x44pt
- [ ] Safe area insets applied (top and bottom)
- [ ] Tab bar uses frosted glass (`.ios-tab-bar`)
- [ ] No FAB unless explicitly justified
- [ ] Keyboard doesn't cover input fields
- [ ] `:rounded="isIos"` on buttons and inputs where appropriate

### Android
- [ ] Touch targets >= 48x48dp
- [ ] FAB present for primary creation action
- [ ] Bottom navigation bar height 80dp
- [ ] Hardware back button handled
- [ ] Ripple effect on touchable surfaces (automatic via Quasar)
- [ ] Buttons are pill-shaped (full radius)

### Both Platforms
- [ ] Loading states use spinner tokens (`SPINNER_SIZE_PAGE` / `SPINNER_SIZE_INLINE`)
- [ ] Avatars use correct size token for context
- [ ] `prefers-reduced-motion` respected
- [ ] `hide-bottom-space` on stacked form inputs to prevent uneven spacing
- [ ] Forms use `q-form` with `ref` for `.validate()` on submit
- [ ] Submit buttons show `:loading="submitting"` state

---

## References

- Apple Human Interface Guidelines: https://developer.apple.com/design/human-interface-guidelines/designing-for-ios
- Material Design 3: https://m3.material.io/
- Quasar Framework (Capacitor): https://quasar.dev/quasar-cli-vite/developing-capacitor-apps/introduction
