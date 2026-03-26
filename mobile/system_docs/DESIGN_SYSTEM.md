# Klikk Tenant Mobile App — Design System

This document defines all design tokens and reusable widget patterns used in the Flutter app. These tokens are aligned with the admin Vue/Tailwind design system.

---

## Colors (`lib/theme/app_colors.dart`)

### Brand
| Token | Hex | Usage |
|-------|-----|-------|
| `primaryNavy` | #2B2D6E | Primary brand, headers, active states |
| `navyDark` | #23255A | Chat bubble gradient start |
| `navyLight` | #3B3E8F | Chat bubble gradient end |
| `accentPink` | #FF3D7F | FABs, CTA highlights |
| `accentPinkLight` | #FF6B9D | Hover/light pink accent |

### Surfaces
| Token | Hex | Usage |
|-------|-----|-------|
| `splashBackground` | #F0EFF8 | Splash screen |
| `scaffoldBackground` | #F5F5F8 | All screen backgrounds |
| `cardBackground` | #FFFFFF | Card surfaces |
| `inputBackground` | #F9FAFB | Input field fills |

### Text
| Token | Hex | Usage |
|-------|-----|-------|
| `textPrimary` | #111111 | Headings, body text |
| `textSecondary` | #6B7280 | Labels, subtitles |
| `textTertiary` | #9CA3AF | Placeholders, hints |
| `textOnPrimary` | #FFFFFF | Text on navy/colored backgrounds |

### Borders
| Token | Hex | Usage |
|-------|-----|-------|
| `border` | #E5E7EB | Card borders, dividers |
| `inputBorder` | #D1D5DB | Input field borders |
| `divider` | #E5E7EB | List dividers |

### Semantic Colors (50/100/500/600/700 scales)

**Success (green):**
| Token | Hex |
|-------|-----|
| `success50` | #F0FDF4 |
| `success100` | #DCFCE7 |
| `success500` | #22C55E |
| `success600` | #16A34A |
| `success700` | #15803D |

**Warning (amber/orange):**
| Token | Hex |
|-------|-----|
| `warning50` | #FFFBEB |
| `warning100` | #FEF3C7 |
| `warning500` | #F59E0B |
| `warning600` | #D97706 |
| `warning700` | #B45309 |

**Danger (red):**
| Token | Hex |
|-------|-----|
| `danger50` | #FEF2F2 |
| `danger100` | #FEE2E2 |
| `danger500` | #EF4444 |
| `danger600` | #DC2626 |
| `danger700` | #B91C1C |

**Info (blue):**
| Token | Hex |
|-------|-----|
| `info50` | #EFF6FF |
| `info100` | #DBEAFE |
| `info500` | #3B82F6 |
| `info600` | #2563EB |
| `info700` | #1D4ED8 |

**Gray scale:**
| Token | Hex |
|-------|-----|
| `gray50` | #F9FAFB |
| `gray100` | #F3F4F6 |
| `gray200` | #E5E7EB |
| `gray300` | #D1D5DB |
| `gray400` | #9CA3AF |
| `gray500` | #6B7280 |
| `gray600` | #4B5563 |
| `gray700` | #374151 |

### Status & Priority Color Helpers

**Status badge colors** (background / text pairs matching admin's 50/700 pattern):

| Status | Badge Background | Badge Text | Solid Color |
|--------|-----------------|------------|-------------|
| `open` | danger50 | danger700 | danger500 |
| `in_progress` | warning50 | warning700 | warning600 |
| `resolved` | success50 | success700 | success500 |
| `closed` | gray100 | gray700 | gray600 |
| `pending` | info50 | info700 | info500 |

**Priority badge colors:**

| Priority | Badge Background | Badge Text | Solid Color |
|----------|-----------------|------------|-------------|
| `urgent` | danger50 | danger700 | danger500 |
| `high` | warning50 | warning700 | warning500 |
| `medium` | info50 | info700 | info500 |
| `low` | success50 | success700 | success500 |

```dart
// Usage:
AppColors.statusColor('open')       // → danger500
AppColors.statusBadgeBg('open')     // → danger50
AppColors.statusBadgeText('open')   // → danger700
AppColors.priorityColor('high')     // → warning500
AppColors.priorityBadgeBg('high')   // → warning50
AppColors.priorityBadgeText('high') // → warning700
```

---

## Border Radius (`lib/theme/app_radius.dart`)

| Token | Value | Usage |
|-------|-------|-------|
| `small` | 8 | Input fields, small elements |
| `medium` | 12 | General containers |
| `card` | 12 | All cards (matches admin `rounded-xl`) |
| `large` | 12 | Same as card |
| `xl` | 16 | Chat bubbles |
| `pill` | 28 | Buttons, badges, filter pills |

**BorderRadius helpers:** `AppRadius.smallBorder`, `.mediumBorder`, `.cardBorder`, `.largeBorder`, `.xlBorder`, `.pillBorder`

---

## Spacing (`lib/theme/app_spacing.dart`)

| Token | Value | Usage |
|-------|-------|-------|
| `xs` | 4 | Tight gaps |
| `sm` | 8 | Small gaps |
| `md` | 12 | Medium gaps |
| `lg` | 16 | Standard gaps |
| `xl` | 20 | Section spacing |
| `xxl` | 24 | Large spacing |
| `xxxl` | 32 | Extra large |

**Layout presets:**
| Token | Value | Usage |
|-------|-------|-------|
| `screenH` | 20 | Horizontal screen padding |
| `listGap` | 10 | Gap between list items |
| `sectionGap` | 12 | Gap below section titles |

**EdgeInsets presets:**
```dart
AppSpacing.screenPadding   // EdgeInsets.symmetric(horizontal: 20)
AppSpacing.listPadding     // EdgeInsets.fromLTRB(20, 12, 20, 20)
AppSpacing.cardPadding     // EdgeInsets.all(16)
```

---

## Typography (`lib/theme/app_text_styles.dart`)

| Style | Size | Weight | Color | Usage |
|-------|------|--------|-------|-------|
| `headerTitle` | 20 | w700 | white | AppHeader title |
| `headerSubtitle` | 13 | w400 | white70 | AppHeader subtitle |
| `sectionTitle` | 16 | w700 | textPrimary | Section headings |
| `sectionLabel` | 11 | w600 | textSecondary | Uppercase section labels |
| `cardTitle` | 15 | w600 | textPrimary | Card headings |
| `cardSubtitle` | 13 | w400 | textSecondary | Card secondary text |
| `cardLabel` | 12 | w500 | textSecondary | Card labels |
| `cardValue` | 14 | w700 | textPrimary | Card values |
| `badgeText` | 11 | w600 | — | Badge labels |
| `body` | 14 | w400 | textPrimary | Body copy (height 1.45) |
| `bodySecondary` | 14 | w400 | textSecondary | Secondary body |
| `emptyTitle` | 16 | w600 | textPrimary | Empty state titles |
| `emptySubtitle` | 14 | w400 | textSecondary | Empty state subtitles |

---

## Reusable Widgets

### AppHeader (`widgets/app_header.dart`)
Navy-background header with safe area padding. Accepts `title`, `subtitle`, `leading`, `trailing` widgets.

```dart
AppHeader(
  title: 'My Repairs',
  subtitle: 'Track your requests',
  trailing: CircleAvatar(...),
)
```

### StatusBadge (`widgets/status_badge.dart`)
Small colored pill badge. Uses the admin "50/700" color pattern (light background, dark text).

```dart
// Factory constructors:
StatusBadge.status('open')       // Red badge: "open"
StatusBadge.priority('high')     // Amber badge: "high"

// Manual:
StatusBadge(
  label: 'Custom',
  backgroundColor: AppColors.info50,
  textColor: AppColors.info700,
)
```

### AccentCard (`widgets/accent_card.dart`)
White card with optional left accent border (4px). Pill radius, subtle border, ink ripple on tap.

```dart
AccentCard(
  accentColor: AppColors.priorityColor(issue.priority),
  onTap: () => context.push('/issues/${issue.id}'),
  child: Row(...),
)
```

### FilterPills (`widgets/filter_pills.dart`)
Horizontal scrollable row of filter chips. Inactive = white/gray border. Active = navy/white.

```dart
FilterPills(
  options: [FilterOption(label: 'All', value: ''), ...],
  selected: _filter,
  onChanged: _onFilterChanged,
)
```

### State Views (`widgets/state_views.dart`)

| Widget | Usage |
|--------|-------|
| `LoadingView()` | Skeleton shimmer (default) |
| `LoadingView.spinner()` | CircularProgressIndicator |
| `ErrorView(message, onRetry)` | Error icon + message + retry button |
| `EmptyView(icon, title, subtitle?)` | Empty state illustration |
| `SkeletonCard()` | Single animated shimmer card |
| `SkeletonListView(count: 5)` | Multiple shimmer cards |

### PrimaryButton (`widgets/primary_button.dart`)
Full-width elevated button (52px height, pill shape). Shows spinner when `loading: true`.

```dart
PrimaryButton(
  label: 'Sign In',
  onPressed: _submit,
  loading: _isSubmitting,
)
```

### TextInputField (`widgets/text_input_field.dart`)
Form text field with label. Supports `isPassword` toggle (visibility icon).

```dart
TextInputField(
  label: 'Email',
  controller: _emailCtrl,
  validator: (v) => v!.isEmpty ? 'Required' : null,
)
```

---

## Design Patterns

### Card Pattern
All cards across the app follow a consistent pattern:
- White background
- 12px border radius (`AppRadius.card`)
- 1px gray border (`AppColors.border`)
- 16px internal padding (`AppSpacing.cardPadding`)
- No elevation (flat design)

### Badge Pattern (50/700)
Status and priority badges use the "50/700 pattern" matching the admin Tailwind badges:
- Background: semantic-50 (very light)
- Text: semantic-700 (dark)
- Pill shape (`AppRadius.pill`)
- 11px w600 font

### Header Pattern
All main tab screens use `AppHeader` (navy background, white text). Detail screens use standard `AppBar` with back button.

### Loading Pattern
All list screens show `SkeletonListView` (animated shimmer cards) while loading, replacing the previous `CircularProgressIndicator` pattern. `LoadingView.spinner()` is available for inline/small loading states.

### Error → Retry Pattern
Screens that load data show `ErrorView` with a retry callback on failure. Most also support pull-to-refresh via `RefreshIndicator`.
