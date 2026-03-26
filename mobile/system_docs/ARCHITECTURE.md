# Klikk Tenant Mobile App — Architecture

## Overview

Flutter-based tenant portal for the Klikk/Tremly property management platform. Tenants use this app to view their home dashboard, report and track maintenance repairs, chat with AI support, view property info, sign leases digitally, and manage their account.

**Stack:** Flutter 3.x · Dart · Material 3 · GoRouter · Provider (ChangeNotifier) · HTTP + FlutterSecureStorage

---

## Project Structure

```
mobile/lib/
├── main.dart                          # Entry point, Provider setup
├── config/
│   └── api_config.dart               # API base URL (env/platform-aware)
├── providers/
│   └── auth_provider.dart            # AuthProvider (ChangeNotifier)
├── router/
│   └── app_router.dart               # GoRouter route definitions
├── services/
│   ├── api_client.dart               # HTTP client, token refresh, singleton
│   ├── auth_service.dart             # Login, fetchMe, token storage
│   ├── maintenance_service.dart      # CRUD maintenance issues
│   ├── info_service.dart             # Unit info items
│   ├── lease_service.dart            # Tenant leases
│   └── esigning_service.dart         # DocuSeal e-signing submissions
├── screens/
│   ├── auth/                         # Splash, onboarding, login, signup, OTP
│   ├── shell/                        # AppShell (bottom nav, IndexedStack)
│   ├── home/                         # Dashboard tab
│   ├── issues/                       # Repairs tab, detail, report form
│   ├── info/                         # Property info tab
│   ├── settings/                     # Account & logout tab
│   ├── chat/                         # AI assistant list + detail
│   └── esigning/                     # Lease signing + DocuSeal WebView
├── theme/
│   ├── app_colors.dart               # Full color palette + semantic helpers
│   ├── app_radius.dart               # Border radius tokens
│   ├── app_spacing.dart              # Spacing tokens + EdgeInsets presets
│   ├── app_text_styles.dart          # Typography presets
│   └── app_theme.dart                # ThemeData definition
├── utils/
│   └── icon_mapper.dart              # Icon type string → IconData
└── widgets/
    ├── app_header.dart               # Navy header (safe area aware)
    ├── auth_header.dart              # Auth page header with logo
    ├── auth_card.dart                # White card container for auth forms
    ├── primary_button.dart           # Full-width CTA button
    ├── text_input_field.dart         # Text input with password toggle
    ├── phone_input_field.dart        # Phone + country code picker
    ├── otp_input_row.dart            # 6-digit OTP input
    ├── klikk_logo.dart               # Brand logo widget
    ├── accent_card.dart              # Card with left accent border
    ├── status_badge.dart             # Status/priority pill badges
    ├── filter_pills.dart             # Horizontal filter chip row
    └── state_views.dart              # Loading, Error, Empty, Skeleton
```

---

## Entry Point

**`main.dart`** initializes the app:

```dart
void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    ChangeNotifierProvider<AuthProvider>(
      create: (_) => AuthProvider(AuthService()),
      child: const KlikkApp(),
    ),
  );
}
```

`KlikkApp` uses `MaterialApp.router` with `appRouter` (GoRouter) and `AppTheme.light`.

---

## State Management

**Single provider:** `AuthProvider` (ChangeNotifier) wraps the entire app.

```dart
class AuthProvider extends ChangeNotifier {
  AuthUser? user;        // null = logged out
  bool _restored = false; // token restoration complete?

  bool get isLoggedIn => user != null;
  bool get restored => _restored;

  Future<void> restore()   // Read stored token → fetch /auth/me/
  Future<void> login(email, password)
  Future<void> logout()    // Clear tokens, null user, notify
}
```

**Services are global singletons:**
- `apiClient` — HTTP layer with automatic token refresh
- `maintenanceService`, `infoService`, `leaseService`, `esigningService`
- Services are imported directly (not injected via Provider)

**Screen-level state** uses `StatefulWidget` with local `_loading`, `_error`, `_items` fields and `setState()`. Pull-to-refresh is implemented on most list screens.

---

## Routing

**GoRouter** defined in `router/app_router.dart`:

| Path | Screen | Notes |
|------|--------|-------|
| `/` | SplashScreen | Token restoration → redirect |
| `/onboarding` | OnboardingScreen | 7-stage carousel |
| `/login` | LoginEmailScreen | Email + password form |
| `/login/mobile` | LoginMobileScreen | Phone + OTP flow |
| `/login/otp` | OtpScreen | 6-digit verification |
| `/signup` | SignupScreen | Registration form |
| `/signup/otp` | OtpScreen | Signup verification |
| `/home` | AppShell | Bottom nav (4 tabs) |
| `/issues/report` | ReportIssueScreen | Accepts `initialDraft` extra |
| `/issues/:id` | IssueDetailScreen | Path param: `issueId` |
| `/chat` | ChatListScreen | AI conversations |
| `/chat/:id` | ChatDetailScreen | Path param: `conversationId` |
| `/signing` | LeaseSigningScreen | Active lease + submissions |
| `/signing/web` | DocusealWebViewScreen | WebView embed URL |

**Redirect rule:** `/dashboard` → `/home`

---

## Auth Flow

```
SplashScreen
  ├── Has stored token? → fetchMe() → /home
  ├── First launch? → /onboarding
  └── No token → /login

LoginEmailScreen
  └── AuthProvider.login() → /home

SettingsScreen
  └── AuthProvider.logout() → clear tokens → /login
```

**Token management** lives in `ApiClient`:
- Tokens stored in `FlutterSecureStorage` (keys: `access_token`, `refresh_token`)
- 401 responses trigger automatic refresh via `tryRefresh()`
- Concurrent refresh prevented by `Completer`-based lock (`_refreshLock`)
- Failed refresh clears all tokens

---

## Services Layer

### ApiClient (singleton)

```dart
class ApiClient {
  Future<Map<String, dynamic>> get(String path, {Map<String, String>? params})
  Future<List<dynamic>> getList(String path, {Map<String, String>? params})
  Future<Map<String, dynamic>> post(String path, {Map<String, dynamic>? body})
  Future<Map<String, dynamic>> patch(String path, {Map<String, dynamic>? body})
  Future<Map<String, dynamic>> postMultipart(String path, {String? content, String? filePath})
  Future<bool> tryRefresh()
}
```

- `getList()` extracts the `results` key from paginated responses
- `postMultipart()` supports file uploads (used by chat attachments)
- All methods add `Authorization: Bearer <token>` header when token exists
- Throws `ApiException(message, {statusCode})` on errors

### Data Models

Models are defined inside their respective service files:

| Model | Service File | Key Fields |
|-------|-------------|------------|
| `AuthUser` | auth_service.dart | id, email, fullName, role |
| `MaintenanceIssue` | maintenance_service.dart | id, title, description, status, priority, category, ticketRef, createdAt |
| `UnitInfoItem` | info_service.dart | id, iconType, label, value |
| `TenantLease` | lease_service.dart | id, status, unitLabel |
| `ESigningSubmission` | esigning_service.dart | id, leaseId, leaseLabel, status, signingMode, signedPdfUrl, signers[] |
| `ESigningSigner` | esigning_service.dart | id, name, email, role, status, embedSrc, order |

All models have `factory X.fromJson(Map<String, dynamic> json)` constructors.

---

## API Configuration

```dart
class ApiConfig {
  static String get baseUrl {
    // 1. Check --dart-define=API_BASE_URL
    // 2. Android emulator: http://10.0.2.2:8000/api/v1
    // 3. Default: http://127.0.0.1:8000/api/v1
  }
}
```

Dev credentials can be pre-filled via `--dart-define=DEV_EMAIL=... --dart-define=DEV_PASS=...`.

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| go_router | ^14.0.0 | Declarative routing |
| provider | ^6.1.0 | State management |
| http | ^1.2.0 | HTTP client |
| flutter_secure_storage | ^9.0.0 | Encrypted token storage |
| country_code_picker | ^3.0.0 | Phone country code selector |
| pin_code_fields | ^8.0.0 | OTP digit input |
| image_picker | ^1.1.2 | Photo/video capture |
| url_launcher | ^6.3.1 | Open external URLs |
| webview_flutter | ^4.10.0 | DocuSeal e-signing embed |
| mockito | ^5.4.0 | Test mocking (dev) |
| build_runner | ^2.4.0 | Code generation (dev) |
