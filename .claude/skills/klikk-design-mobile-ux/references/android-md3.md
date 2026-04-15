# Android Material Design 3 (Material You)

Reference: https://m3.material.io/

---

## Typography Scale — Roboto

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

---

## Spacing System

**Base unit:** 4dp (common increments: 4, 8, 12, 16, 24, 32, 48dp)

| Context | Value |
|---------|-------|
| Horizontal page margin | 16dp |
| Section gap | 16-24dp |
| Card padding | 16dp |
| List item padding | 16dp |

---

## Navigation

**Bottom Navigation Bar:**
- Height: 80dp
- Active indicator: 64×32dp pill behind icon
- Class: `.md-bottom-nav` in `app.scss`

**Top App Bar:**
- Height: 64dp
- Class: `.md-header` in `app.scss`

**FAB (Floating Action Button):**
- 56×56dp, icon 24dp, corner radius 16dp
- Color: `$secondary` (teal)
- Position: `bottom-right`, offset `[18, 88]` (above bottom nav)

---

## Component Sizes

| Component | Spec |
|-----------|------|
| Buttons | 40dp height, full pill radius (`border-radius: 20px`) |
| Text Fields | 56dp height, outlined with 4dp radius |
| Cards | `border-radius: 12dp`, `box-shadow: 0 1px 3px rgba(0,0,0,0.12)` |
| Dialogs | Corner radius 28dp (ExtraLarge) |
| Touch targets | **48×48dp minimum** for all interactive elements |

---

## Color System

| M3 Role | Quasar token | Klikk value |
|---------|--------------|-------------|
| `primary` | `var(--q-primary)` | `#2B2D6E` |
| `secondary` | `var(--q-secondary)` | `#0D9488` |
| `error` | `var(--q-negative)` | `#DB2828` |
| `success` | `var(--q-positive)` | `#21BA45` |
| `warning` | `var(--q-warning)` | `#F2C037` |
| `surface` | `$surface` | `#F5F5F8` |

---

## Elevation System (M3)

| Level | Shadow | Typical use |
|-------|--------|-------------|
| 0 | 0dp | Cards (flat), text fields |
| 1 | 1dp | Elevated cards, menus |
| 3 | 6dp | Modal bottom sheets |
| 5 | 12dp | FAB, dialogs |

---

## Motion System

**Easing curves:**
- Standard: `cubic-bezier(0.2, 0, 0, 1)` — elements staying on screen
- Standard Decelerate: `cubic-bezier(0, 0, 0, 1)` — entering screen
- Standard Accelerate: `cubic-bezier(0.3, 0, 1, 1)` — leaving screen

**Quasar transitions:** `slideInRight` / `slideOutLeft` for Android (set in `usePlatform.ts`)

**Ripple:** Quasar adds `v-ripple` automatically to `q-btn`, `q-item`, etc.

---

## Android Checklist

- [ ] Touch targets >= 48×48dp
- [ ] FAB present for primary creation action
- [ ] Bottom navigation bar height 80dp
- [ ] Hardware back button handled
- [ ] Ripple effect on touchable surfaces (automatic via Quasar)
- [ ] Buttons are pill-shaped (full radius)
