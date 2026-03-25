import 'package:flutter_test/flutter_test.dart';
import 'package:klikk_tenant/providers/auth_provider.dart';
import 'package:klikk_tenant/services/auth_service.dart';

import '../../helpers/mock_secure_storage.dart';

void main() {
  late AuthService authService;
  late AuthProvider provider;

  setUp(() {
    authService = AuthService(storage: MockSecureStorage());
    provider = AuthProvider(authService);
  });

  group('AuthProvider', () {
    test('initial state: user is null and not restored', () {
      expect(provider.user, isNull);
      expect(provider.isLoggedIn, isFalse);
      expect(provider.restored, isFalse);
    });

    test('restore with no token sets restored=true, user=null', () async {
      await provider.restore();

      expect(provider.restored, isTrue);
      expect(provider.user, isNull);
      expect(provider.isLoggedIn, isFalse);
    });

    test('logout clears user', () async {
      // Even when user is already null, logout should work cleanly.
      await provider.logout();

      expect(provider.user, isNull);
      expect(provider.isLoggedIn, isFalse);
    });

    test('notifyListeners fires on restore', () async {
      int callCount = 0;
      provider.addListener(() => callCount++);

      await provider.restore();

      expect(callCount, greaterThan(0));
    });

    test('notifyListeners fires on logout', () async {
      int callCount = 0;
      provider.addListener(() => callCount++);

      await provider.logout();

      expect(callCount, greaterThan(0));
    });

    test('login throws propagates AuthException', () async {
      expect(
        () => provider.login('bad@email.com', 'wrong'),
        throwsA(isA<Exception>()),
      );
    });

    test('isLoggedIn reflects user state', () {
      expect(provider.isLoggedIn, isFalse);
      // We cannot easily set user without mocking the network,
      // but we verify the getter logic.
    });
  });
}
