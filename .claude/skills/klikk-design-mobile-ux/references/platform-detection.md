# Platform Detection & Cross-Platform Patterns

---

## Platform Detection

**File:** `agent-app/src/composables/usePlatform.ts`

```typescript
import { computed } from 'vue'
import { useQuasar } from 'quasar'

export function usePlatform() {
  const $q = useQuasar()
  const isIos     = computed(() => $q.platform.is.ios)
  const isAndroid = computed(() => $q.platform.is.android)
  // ...
}
```

**Usage:**
```html
<q-input :rounded="isIos" outlined />
<q-btn :rounded="isIos" unelevated />
```

---

## Navigation Patterns by Platform

| Pattern | iOS | Android |
|---------|-----|---------|
| Back navigation | Swipe right + nav bar back btn | System gesture + optional back btn |
| Primary nav | Tab bar (3-5 tabs, always visible) | Bottom nav bar (3-5 items) |
| FAB | Avoid | First-class primary action |
| Modal presentation | Sheet (slides from bottom) | Dialog (centered) or Bottom Sheet |
| Page transition | Fade | Slide right / left |

---

## Critical Platform Behaviors

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

---

## Icon Usage

| Platform | Preferred icon set |
|----------|--------------------|
| iOS feel | Ionicons v7 |
| Android / Material | Material Icons |
| Universal | Material Symbols Outlined |

Icon sizes: Nav 22-24dp, List leading 24dp, Button 18-20dp, FAB 24dp, Tab 22dp.

---

## Cross-Platform Size Reference

### Typography Mapping

| iOS Style | Size | Android Style | Size |
|-----------|------|---------------|------|
| Large Title | 34pt | Headline Large | 32sp |
| Title 1 | 28pt | Headline Medium | 28sp |
| Title 2 | 22pt | Title Large | 22sp |
| Headline | 17pt (semibold) | Title Medium | 16sp (500) |
| Body | 17pt | Body Large | 16sp |
| Caption 1 | 12pt | Body Small | 12sp |
| Caption 2 | 11pt | Label Medium | 12sp |

### Component Size Mapping

| Component | iOS | Android |
|-----------|-----|---------|
| Touch target minimum | 44×44pt | 48×48dp |
| Button height | ~48pt (full-width) | 40dp |
| Text field height | 44pt | 56dp |
| List row (1-line) | 44pt | 56dp |
| Tab bar height | 49pt + safe area | 80dp |
| Navigation bar | 44pt | 64dp |
| Card corner radius | 12pt | 12dp |
| Modal corner radius | 12-16pt (top) | 28dp (ExtraLarge) |
