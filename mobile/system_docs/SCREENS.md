# Klikk Tenant Mobile App — Screen Reference

## Auth Screens

### SplashScreen (`/`)
**File:** `screens/auth/splash_screen.dart`

Entry point. Navy background with loading indicator. Calls `AuthProvider.restore()` on init with 5-second timeout. Routes to `/home` if authenticated, `/onboarding` or `/login` otherwise.

### OnboardingScreen (`/onboarding`)
**File:** `screens/auth/onboarding_screen.dart`

7-stage animated carousel showcasing the tenant journey:
1. Find Your Home (info500)
2. Apply Online (purple #A78BFA)
3. Sign Your Lease (pink #EC4899)
4. Keys & Move In (success500)
5. 24/7 AI Support (warning500)
6. Renewal Reminders (info500)
7. Clean Exit (warning600)

**Animations:** Icon scale + opacity (elastic bounce), text slide + fade, radial glow background. Auto-advances every 4 seconds. Swipeable via invisible `PageView` overlay.

**Persistence:** Writes `onboarding_seen=true` to FlutterSecureStorage on skip/finish.

### LoginEmailScreen (`/login`)
**File:** `screens/auth/login_email_screen.dart`

Form with email + password fields. Calls `AuthProvider.login()`. Shows SnackBar on error. Links to `/login/mobile`, `/signup`, and forgot password.

Dev mode: pre-fills credentials from `--dart-define=DEV_EMAIL` and `DEV_PASS`.

### LoginMobileScreen (`/login/mobile`)
**File:** `screens/auth/login_mobile_screen.dart`

Phone number input with `CountryCodePicker`. Sends OTP and navigates to `/login/otp`.

### OtpScreen (`/login/otp` or `/signup/otp`)
**File:** `screens/auth/otp_screen.dart`

6-digit PIN input via `pin_code_fields`. Accepts `OtpMode.login` or `OtpMode.signup` enum and phone string via route extra.

### SignupScreen (`/signup`)
**File:** `screens/auth/signup_screen.dart`

Registration form: email, phone, password. Navigates to `/signup/otp` on submit.

---

## Main App (Shell)

### AppShell (`/home`)
**File:** `screens/shell/app_shell.dart`

Bottom navigation with 4 tabs using `IndexedStack` (all tabs stay alive):

| Index | Label | Icon | Screen |
|-------|-------|------|--------|
| 0 | Home | home_rounded | HomeScreen |
| 1 | Repairs | build_rounded | IssuesScreen |
| 2 | Info | info_outline_rounded | InfoScreen |
| 3 | Settings | settings_rounded | SettingsScreen |

Uses `NavigationBar` (Material 3) with `NavigationDestination` items.

---

## Tab 1: Home

### HomeScreen
**File:** `screens/home/home_screen.dart`

**Header:** "Hi, $firstName" + avatar circle (first letter of name)

**Sections (CustomScrollView):**
1. **Active Repairs** — Top 3 open/in-progress issues as `AccentCard` widgets with priority-colored left border, `StatusBadge.status()` and `.priority()` badges. "See all" link → `/issues`.
2. **Lease Signing CTA** — `AccentCard` linking to `/signing`.
3. **Property Info** — Horizontal scrollable row of info cards (max 3 items).

**FAB:** Extended pink FAB "AI" → `/chat`

**Data:** Fetches issues (`?status=open,in_progress`) and unit info on init. Pull-to-refresh via `RefreshIndicator`.

**Empty state:** Green card with checkmark "No active repairs".

---

## Tab 2: Repairs

### IssuesScreen
**File:** `screens/issues/issues_screen.dart`

**Header:** "My Repairs"

**Filter:** `FilterPills` row with 5 options:
- All (empty value) | Open | In Progress | Resolved | Closed

**List:** `AccentCard` per issue showing:
- Title (cardTitle style)
- 1-line description preview
- `StatusBadge.status()` + `StatusBadge.priority()` row
- Created date (secondary text)
- Left accent border colored by `AppColors.priorityColor()`

**States:** LoadingView (skeleton shimmer), ErrorView (retry), EmptyView (green checkmark)

**FAB:** Pink → `/issues/report`

### IssueDetailScreen (`/issues/:id`)
**File:** `screens/issues/issue_detail_screen.dart`

**AppBar:** "Repair Request" with back button

**Layout:**
- Status + priority badges row at top
- Metadata card: ticket ref, category, created date (with dividers between rows)
- Description card (if present)

**Data:** Fetches single issue by ID. LoadingView while loading.

### ReportIssueScreen (`/issues/report`)
**File:** `screens/issues/report_issue_screen.dart`

**AppBar:** "Report a Repair" with back button

**Form fields:**
- Title (required)
- Description (multiline, required)
- Category dropdown: plumbing, electrical, roof, appliance, security, pest, garden, other
- Priority dropdown: low, medium, high, urgent (with colored dots)

**Submit:** Creates issue via `maintenanceService.createIssue()`. Success SnackBar (green). Error SnackBar (red).

**Draft support:** Accepts `initialDraft` map via route extra to pre-fill from AI chat suggestions.

---

## Tab 3: Property Info

### InfoScreen
**File:** `screens/info/info_screen.dart`

**Header:** "Property Info"

**List:** Each `UnitInfoItem` rendered as a card tile with:
- Colored icon container (color varies by type: wifi=info, alarm=danger, electricity=warning, water=info, default=navy)
- Label + value
- **Sensitive items** (wifi, alarm): value masked as dots, tap to reveal/hide

**States:** LoadingView, ErrorView (retry), EmptyView

---

## Tab 4: Settings

### SettingsScreen
**File:** `screens/settings/settings_screen.dart`

**Header:** User full name + email + avatar

**Account section:** Name, email, role tiles in a white card with dividers

**Logout:** Red tile at bottom. Calls `AuthProvider.logout()` → navigates to `/login`.

---

## Chat

### ChatListScreen (`/chat`)
**File:** `screens/chat/chat_list_screen.dart`

**Header:** "AI Assistant"

**List:** Conversation cards showing:
- Purple avatar with robot icon
- Conversation title
- Last message preview (truncated)
- Timestamp

**FAB:** Pink "+" → creates new conversation, navigates to `/chat/:id`

**Empty state:** "No conversations yet"

### ChatDetailScreen (`/chat/:id`)
**File:** `screens/chat/chat_detail_screen.dart`

**AppBar:** Conversation title

**Messages:** Reverse-scrolled list
- **User bubbles:** Right-aligned, navy gradient background, white text
- **AI bubbles:** Left-aligned, white background, dark text
- **Typing indicator:** Animated 3-dot bounce (shown while waiting for AI response)

**Attachments:**
- Attachment button → bottom sheet (Camera, Gallery, Video)
- Uses `ImagePicker` package
- Pending attachment shown as preview above input
- Sent via `postMultipart()` to `/tenant-portal/conversations/{id}/messages/`

**Maintenance CTA:** When AI suggests a maintenance report (`maintenance_report_suggested == true`), shows a tappable card that navigates to `/issues/report` with pre-filled draft data.

**Optimistic updates:** User message appears immediately, removed on send failure.

---

## E-Signing

### LeaseSigningScreen (`/signing`)
**File:** `screens/esigning/lease_signing_screen.dart`

**AppBar:** "Lease signing"

**Flow:**
1. Loads tenant's active lease via `leaseService.listLeases()`
2. Fetches submissions for that lease via `esigningService.listForLease(leaseId)`
3. For each submission: card showing signers, their status, and flow order
4. Identifies actionable signer for current user via `actionableSignerForUser()`
5. "Open signing" button → navigates to `/signing/web` with embed URL

**Post-signing:** Refreshes on return from WebView, shows success state.

### DocusealWebViewScreen (`/signing/web`)
**File:** `screens/esigning/docuseal_webview_screen.dart`

Loads DocuSeal embed URL in `WebViewController`. Polls submission status every 10 seconds via `esigningService.getSubmission()`. Auto-closes (pops with `true` result) when status is `completed` or `declined`.
