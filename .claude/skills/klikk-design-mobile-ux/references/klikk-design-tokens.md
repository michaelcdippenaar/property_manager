# Klikk Design Tokens & Shared Utilities (Mobile)

All token files live in the Quasar/Capacitor apps (`agent-app`, `tenant-app`).

---

## CSS Custom Properties (`app.scss :root`)

Never hardcode hex values — use these tokens in `<template>` inline styles and unscoped CSS.

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

| Use case | Token |
|----------|-------|
| Card/component borders | `var(--klikk-border)` |
| Card border-radius | `var(--klikk-radius-card)` |
| Input border-radius | `var(--klikk-radius-input)` |
| Tab bar / nav borders | `var(--klikk-border-strong)` |
| Form labels, section headers | `var(--klikk-text-secondary)` |
| Input text, headings | `var(--klikk-text-primary)` |
| Placeholders, hints | `var(--klikk-text-faint)` |
| Inactive tab icons | `var(--klikk-text-muted)` |

---

## SCSS Brand Tokens (`quasar.variables.scss`)

Use in `<style lang="scss">` scoped blocks:

```scss
$primary:   #2B2D6E;   // Klikk Navy
$secondary: #FF3D7F;   // Klikk Pink Accent
$accent:    #FF3D7F;   // Klikk Pink Accent
$dark:      #1A1B44;
$surface:   #F5F5F8;   // Page background
$positive:  #21BA45;
$negative:  #DB2828;
$info:      #31CCEC;
$warning:   #F2C037;
// Note: teal #0D9488 is the success-600 shade (use $positive-like success states), not the brand accent
```

- In `<style lang="scss">`: use `$primary`, `rgba($primary, 0.12)`, etc.
- In `<template>` or unscoped CSS: use `var(--q-primary)`, `var(--klikk-text-primary)`, etc.
- **Never write** `color: #2B2D6E` or `color: #0D9488` directly.

---

## Design Tokens File (`designTokens.ts`)

**File:** `agent-app/src/utils/designTokens.ts`

Import from here — never redefine these values.

```typescript
export const SPINNER_SIZE_PAGE   = '36px'   // Full-page loaders
export const SPINNER_SIZE_INLINE = '24px'   // Tab/inline loaders
export const EMPTY_ICON_SIZE     = '48px'   // Empty state icons
export const AVATAR_PROFILE      = '48px'   // Profile/prospect avatars
export const AVATAR_LIST         = '40px'   // Standard list avatars
export const AVATAR_COMPACT      = '36px'   // Compact list avatars

export const RULES = {
  required:       (v: unknown) => !!v || 'Required',
  requiredSelect: (v: unknown) => !!v || 'Please select an option',
  positiveNumber: (v: unknown) => (!!v && Number(v) > 0) || 'Enter a valid amount',
  email:          (v: string) => !v || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) || 'Enter a valid email',
} as const

export function formatZAR(amount: string | number): string {
  return Number(amount).toLocaleString('en-ZA')
}
```

**In forms:**
```html
<!-- GOOD -->
<q-input :rules="[RULES.required]" />
<q-select :rules="[RULES.requiredSelect]" />

<!-- BAD — inline rules (duplicated across pages) -->
<q-input :rules="[v => !!v || 'Required']" />
```

---

## Shared Formatters (`formatters.ts`)

**File:** `agent-app/src/utils/formatters.ts`

| Function | Purpose | Example |
|----------|---------|---------|
| `formatDate(iso)` | Short date | "10 Apr 2026" |
| `formatDateTime(iso)` | Full date-time | "Thursday, 10 April, 09:00" |
| `formatDateTimeShort(iso)` | Short date-time | "Thu, 10 Apr, 09:00" |
| `formatTime(iso)` | Time only | "09:00" |
| `timeAgo(iso)` | Relative time | "2h ago" |
| `daysRemaining(iso)` | Days until date | `45` or `null` |
| `fmtLabel(value)` | Snake_case → display | "in_progress" → "In Progress" |
| `statusColor(status)` | Viewing status → Quasar color | "scheduled" → "info" |
| `statusIcon(status)` | Viewing status → Material icon | "scheduled" → "event" |
| `statusDotColor(status)` | Calendar dot color | Uses `var(--q-*)` CSS vars |
| `leaseStatusColor(status)` | Lease status → color | "active" → "positive" |
| `unitStatusColor(status)` | Unit status → color | "available" → "positive" |
| `maintenancePriorityColor(p)` | Priority → color | "urgent" → "negative" |
| `maintenanceStatusColor(s)` | Maintenance status → color | "open" → "info" |
| `maintenanceCategoryIcon(c)` | Category → Material icon | "plumbing" → "plumbing" |

---

## Reusable CSS Classes (`app.scss`)

Use these global classes instead of writing equivalent scoped styles.

### `.section-card`
```html
<q-card flat class="section-card">
```
```scss
.section-card {
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-border);
  overflow: hidden;
  margin-bottom: 16px;
}
```

### `.section-header`
```html
<div class="section-header">Lease Terms</div>
```
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

### `.empty-state`
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

### `.prospect-badge`
```html
<span class="prospect-badge status-scheduled">Scheduled</span>
<span class="prospect-badge status-confirmed">Confirmed</span>
<span class="prospect-badge status-completed">Completed</span>
<span class="prospect-badge status-cancelled">Cancelled</span>
<span class="prospect-badge status-converted">Converted</span>
```

### `.page-container`
```scss
.page-container { padding: 16px; max-width: 600px; margin: 0 auto; }
```

---

## Error Handling (Mandatory)

Every API call must have error feedback. Never use `catch {}` or `catch { /* ignore */ }`.

**Data loading on mount:**
```typescript
onMounted(async () => {
  try {
    data.value = await fetchData(props.id)
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to load data.', icon: 'error' })
  }
})
```

**Form submission:**
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

---

## Accessibility

**Icon-only buttons:**
```html
<q-btn flat round dense icon="call" color="primary"
       :href="`tel:${phone}`" tag="a" aria-label="Call prospect" />
```

**Dynamic labels:**
```html
<q-btn flat round dense
  :icon="showPassword ? 'visibility_off' : 'visibility'"
  :aria-label="showPassword ? 'Hide password' : 'Show password'"
  @click="showPassword = !showPassword"
/>
```

**Focus-visible** (already in `app.scss`):
```scss
:focus-visible { outline: 2px solid var(--q-primary); outline-offset: 2px; }
```

**Images:**
```html
<q-img :src="property.image_url" :alt="`Photo of ${property.name}`" />
```
