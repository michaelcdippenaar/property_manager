# Mobile App UI/UX Alignment with Admin Design System

## Context
The Flutter mobile app (tenant-facing) and the Vue admin portal share the Klikk brand but have drifted apart visually. Colors, badge patterns, card styles, loading states, and status indicators don't match. This plan aligns the mobile app's visual language with the admin design system (source of truth) while preserving mobile-appropriate adaptations (larger touch targets, bottom nav, etc.).

---

## Phase 1: Foundation — Design Tokens (do first, everything depends on this)

### 1.1 `mobile/lib/theme/app_colors.dart`

**Fix mismatched colors:**

| Token | Current | Target (admin) |
|-------|---------|----------------|
| `scaffoldBackground` | `#F5F6FA` | `#F5F5F8` |
| `textPrimary` | `#1A1A2E` | `#111111` |
| `textSecondary` | `#888888` | `#6B7280` (gray-500) |
| `inputBorder` | `#DDDDDD` | `#D1D5DB` (gray-300) |
| `divider` | `#EEEEEE` | `#E5E7EB` (gray-200) |

**Add semantic color scales** (for admin's `bg-{color}-50 text-{color}-700` badge pattern):
- success: 50/500/600/700
- warning: 50/500/600/700
- danger: 50/500/600/700
- info: 50/500/600/700
- gray: 100/400/600

**Fix `statusColor()` to match admin mapping:**
- `open` → `danger500` (admin uses red, mobile currently uses blue)
- `in_progress` → `warning600` (`#d97706`, not `#F97316`)
- `resolved` → `success500` (`#10b981`, not `#34D399`)
- `closed` → `gray600`

**Fix `priorityColor()`:**
- `high` → `warning500` (`#f59e0b`, not orange)
- `low` → `success500` (admin uses green, mobile uses gray)

**Add badge helpers:** `statusBadgeBg/Text()`, `priorityBadgeBg/Text()` returning 50/700 pairs.

### 1.2 `mobile/lib/theme/app_radius.dart`
- `large`: 14 → 12 (match admin `rounded-xl`)
- Add `static const double card = 12;`

### 1.3 `mobile/lib/theme/app_theme.dart`
- Fix `scaffoldBackgroundColor` → use corrected `scaffoldBackground`
- Add `CardTheme`: elevation 0, shape with 12px radius + `AppColors.border` side

---

## Phase 2: Components — Shared Widgets

### 2.1 `mobile/lib/widgets/status_badge.dart`
- Border radius: 8 → pill (28) to match admin `rounded-full`
- Background: use `*-50` color (not `color.withOpacity(0.12)`)
- Text: use `*-700` color
- Font weight: w600 → w500 (admin `font-medium`)
- Add factory constructors: `StatusBadge.status(s)`, `StatusBadge.priority(p)`

### 2.2 `mobile/lib/widgets/state_views.dart`
- Add `SkeletonCard` widget (pulse-animated gray rectangles matching admin's `animate-pulse` pattern)
- Add `SkeletonListView` (renders 4-6 skeleton cards)
- `LoadingView` default → skeleton shimmer instead of spinner
- Keep `LoadingView.spinner()` for inline button states

### 2.3 NEW `mobile/lib/widgets/filter_pills.dart`
- Horizontal scrollable pill row (matching admin FilterPills)
- Inactive: white bg, gray-200 border, gray-600 text, rounded-full
- Active: navy bg, white text
- Params: `List<FilterOption>`, `selectedValue`, `onChanged`

### 2.4 NEW `mobile/lib/widgets/accent_card.dart`
- White card with 12px radius, gray-200 border, shadow-sm
- Left border: 4px, colored by priority (matching admin `border-l-4`)
- Reusable for issue cards on both home and issues screens

---

## Phase 3: Screens

### 3.1 Issues Screen (`issues_screen.dart`) — highest impact
- Add `FilterPills` below header (All / Open / In Progress / Resolved / Closed)
- Wire filter to API `status` param
- Replace `LoadingView` → `SkeletonListView`
- Redesign `_IssueListTile` using `AccentCard`:
  - Left accent border by priority
  - Show both status + priority badges
  - Add 1-line description preview
  - Add created date in secondary text

### 3.2 Issue Detail (`issue_detail_screen.dart`)
- Wrap metadata in white card with 2-column grid layout
- Use `StatusBadge.status()` and `StatusBadge.priority()` factories
- Add description in its own card section
- Add section headers matching admin pattern

### 3.3 Home Screen (`home_screen.dart`)
- Fix hardcoded `Color(0xFF34D399)` → `AppColors.success500`
- Wire empty "See all" button to navigate to Repairs tab
- Replace `LoadingView` → skeleton shimmer
- Use `AccentCard` for issue items

### 3.4 Report Issue (`report_issue_screen.dart`)
- Fix hardcoded colors: success `Color(0xFF34D399)` → `AppColors.success500`, error `Colors.red` → `AppColors.danger500`
- Add colored dot indicators next to priority dropdown items

### 3.5 Chat Detail (`chat_detail_screen.dart`)
- User bubble gradient: use navy palette (`#23255a` → `#3b3e8f`) instead of custom dark blues
- Replace bare `CircularProgressIndicator` → skeleton

### 3.6 Chat List (`chat_list_screen.dart`)
- Avatar background: `Color(0xFFEEF2FF)` → `AppColors.info50`
- Add card borders
- Replace loading → skeleton

### 3.7 Info Screen (`info_screen.dart`)
- Replace hardcoded icon colors with `AppColors` constants
- Add card borders + shadow-sm
- Replace loading → skeleton

### 3.8 Settings Screen (`settings_screen.dart`)
- Logout color: `Color(0xFFEF4444)` → `AppColors.danger500`
- Add card borders, dividers between tiles

### 3.9 Onboarding (`onboarding_screen.dart`)
- Fix hardcoded step colors: `Color(0xFF34D399)` → `AppColors.success500`, `Color(0xFFF97316)` → `AppColors.warning600`

---

## Hardcoded Color Audit (must fix)

| File | Current | Target |
|------|---------|--------|
| `home_screen.dart` | `Color(0xFF34D399)` | `AppColors.success500` |
| `report_issue_screen.dart` | `Color(0xFF34D399)`, `Colors.red` | `AppColors.success500`, `AppColors.danger500` |
| `issues_screen.dart` | `Color(0xFF34D399)` | `AppColors.success500` |
| `settings_screen.dart` | `Color(0xFFEF4444)` | `AppColors.danger500` |
| `info_screen.dart` | Various hardcoded | `AppColors.info500` etc. |
| `chat_list_screen.dart` | `Color(0xFFEEF2FF)` | `AppColors.info50` |
| `chat_detail_screen.dart` | `Color(0xFF0F2744)`, `Color(0xFF1B3F6B)` | Navy palette |
| `onboarding_screen.dart` | `Color(0xFF34D399)`, `Color(0xFFF97316)` | Semantic colors |

---

## Implementation Order

| Step | Scope | Files |
|------|-------|-------|
| 1 | Token fixes | `app_colors.dart`, `app_radius.dart`, `app_theme.dart` |
| 2 | Widget upgrades | `status_badge.dart`, `state_views.dart` |
| 3 | New widgets | `filter_pills.dart`, `accent_card.dart` |
| 4 | Issues screens | `issues_screen.dart`, `issue_detail_screen.dart` |
| 5 | Home + report | `home_screen.dart`, `report_issue_screen.dart` |
| 6 | Chat + info + settings | `chat_*.dart`, `info_screen.dart`, `settings_screen.dart` |
| 7 | Onboarding | `onboarding_screen.dart` |

---

## Verification
1. `cd mobile && flutter analyze` — no errors
2. `flutter run` on simulator — check each screen visually
3. Compare side-by-side: admin maintenance issues list vs mobile issues list
4. Verify badges use 50/700 color pattern (not opacity-based)
5. Verify skeleton loading appears instead of spinner on issues, home, info, chat
6. Verify filter pills work and filter the issue list
7. Verify left accent borders show on issue cards colored by priority
