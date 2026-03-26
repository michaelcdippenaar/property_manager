# Klikk Tenant Mobile App — Testing Guide

## Test Structure

```
mobile/test/
├── helpers/
│   ├── pump_app.dart              # Widget test harness
│   ├── test_data.dart             # JSON fixture factories
│   └── mock_secure_storage.dart   # In-memory FlutterSecureStorage mock
├── unit/
│   ├── config/
│   │   └── api_config_test.dart
│   ├── models/
│   │   ├── auth_user_test.dart
│   │   ├── maintenance_issue_test.dart
│   │   └── unit_info_item_test.dart
│   ├── providers/
│   │   └── auth_provider_test.dart
│   └── services/
│       ├── api_client_test.dart
│       ├── auth_service_test.dart
│       ├── maintenance_service_test.dart
│       ├── info_service_test.dart
│       └── esigning_signer_logic_test.dart
├── widget/
│   ├── app_test.dart
│   ├── screens/
│   │   ├── auth/
│   │   │   ├── login_email_screen_test.dart
│   │   │   ├── splash_screen_test.dart
│   │   │   └── onboarding_screen_test.dart
│   │   ├── home/
│   │   │   └── home_screen_test.dart
│   │   ├── issues/
│   │   │   ├── issues_screen_test.dart
│   │   │   └── issue_detail_screen_test.dart
│   │   ├── chat/
│   │   │   └── chat_list_screen_test.dart
│   │   ├── info/
│   │   │   └── info_screen_test.dart
│   │   ├── settings/
│   │   │   └── settings_screen_test.dart
│   │   └── shell/
│   │       └── app_shell_test.dart
│   └── widgets/
│       ├── primary_button_test.dart
│       ├── text_input_field_test.dart
│       ├── klikk_logo_test.dart
│       ├── auth_card_test.dart
│       └── auth_header_test.dart
└── widget_test.dart               # Smoke test
```

**Total: 107 tests (all passing)**

---

## Running Tests

```bash
# All tests
cd mobile && flutter test

# Specific file
flutter test test/unit/services/api_client_test.dart

# With coverage
flutter test --coverage

# Analyze (lint)
flutter analyze
```

---

## Test Helpers

### MockSecureStorage (`test/helpers/mock_secure_storage.dart`)

In-memory implementation of `FlutterSecureStorage` for tests:

```dart
class MockSecureStorage extends FlutterSecureStorage {
  final Map<String, String> _store = {};
  // read, write, delete, deleteAll implemented with _store
}
```

### Test Data (`test/helpers/test_data.dart`)

Factory functions returning JSON maps for model tests:

```dart
Map<String, dynamic> authUserJson({int id = 1, ...})
Map<String, dynamic> maintenanceIssueJson({int id = 1, ...})
Map<String, dynamic> unitInfoItemJson({int id = 1, ...})
```

### PumpApp (`test/helpers/pump_app.dart`)

Wraps a widget with required providers and MaterialApp for widget testing:

```dart
Future<void> pumpApp(WidgetTester tester, Widget child, {AuthProvider? authProvider})
```

---

## Test Patterns

### Unit Tests (Models)
Test `fromJson` factory with valid, partial, and edge-case JSON:

```dart
test('parses valid JSON', () {
  final json = authUserJson();
  final user = AuthUser.fromJson(json);
  expect(user.id, 1);
  expect(user.email, 'test@example.com');
});
```

### Unit Tests (Services)
Services use `ApiClient` singleton, so service tests mock at the HTTP level using `mockito`:

```dart
@GenerateMocks([http.Client])
// Setup mock responses, inject into ApiClient, test service methods
```

### Unit Tests (Providers)
Test state transitions and listener notifications:

```dart
test('login sets user and notifies', () async {
  final provider = AuthProvider(AuthService(storage: MockSecureStorage()));
  // ... setup mock, call login, verify user != null
});
```

### Widget Tests (Screens)
Build the screen with minimal wrappers, pump, and assert:

```dart
testWidgets('shows header title', (tester) async {
  await tester.pumpWidget(MaterialApp(
    theme: AppTheme.light,
    home: const IssuesScreen(),
  ));
  await tester.pump();
  expect(find.text('My Repairs'), findsOneWidget);
});
```

**Key patterns for widget tests:**
- Screens that need `AuthProvider`: wrap in `ChangeNotifierProvider<AuthProvider>`
- Screens that need routing: use `MaterialApp.router` with `GoRouter`
- Loading states: look for `LoadingView` (which renders `SkeletonListView`)
- Don't look for `CircularProgressIndicator` — loading uses skeleton shimmer now

### Widget Tests (Widgets)
Test individual reusable widgets in isolation:

```dart
testWidgets('PrimaryButton shows spinner when loading', (tester) async {
  await tester.pumpWidget(MaterialApp(
    home: Scaffold(body: PrimaryButton(label: 'Go', onPressed: () {}, loading: true)),
  ));
  expect(find.byType(CircularProgressIndicator), findsOneWidget);
});
```

---

## Important Notes for Test Authors

1. **LoadingView renders SkeletonListView** (not CircularProgressIndicator). To test loading state, assert `find.byType(LoadingView)` or `find.byType(SkeletonListView)`.

2. **StatusBadge constructor** takes `label`, `backgroundColor`, `textColor`. Use factories `StatusBadge.status('open')` and `StatusBadge.priority('high')` for standard badges.

3. **Services are global singletons** — they cannot be easily injected in tests. Widget tests currently test the initial render state (loading) without mocking service responses.

4. **FlutterSecureStorage** must be mocked in tests — use `MockSecureStorage` from helpers.

5. **GoRouter screens** (like IssueDetailScreen) need `MaterialApp.router` with a `GoRouter` config in tests, not plain `MaterialApp`.
