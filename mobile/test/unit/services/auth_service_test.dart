import 'package:flutter_test/flutter_test.dart';
import 'package:klikk_tenant/services/auth_service.dart';

import '../../helpers/mock_secure_storage.dart';

void main() {
  group('AuthService', () {
    late AuthService service;

    setUp(() {
      service = AuthService(storage: MockSecureStorage());
    });

    test('creates without error', () {
      expect(service, isNotNull);
    });

    test('accessToken is null when no token stored', () async {
      final token = await service.accessToken;
      expect(token, isNull);
    });

    test('clearTokens completes without error', () async {
      await service.clearTokens();
      final token = await service.accessToken;
      expect(token, isNull);
    });

    test('fetchMe throws AuthException when no token', () {
      expect(
        () => service.fetchMe(),
        throwsA(isA<AuthException>()),
      );
    });

    test('login throws on network failure (no server)', () {
      expect(
        () => service.login('a@b.com', 'pass'),
        throwsA(isA<Exception>()),
      );
    });

    test('tryRefresh returns false when no refresh token', () async {
      final result = await service.tryRefresh();
      expect(result, isFalse);
    });
  });

  group('AuthException', () {
    test('stores message', () {
      final e = AuthException('oops');
      expect(e.message, 'oops');
      expect(e.toString(), 'oops');
    });

    test('implements Exception', () {
      expect(AuthException('x'), isA<Exception>());
    });
  });

  group('AuthUser', () {
    test('fromJson parses correctly', () {
      final user = AuthUser.fromJson({
        'id': 1,
        'email': 'a@b.com',
        'full_name': 'Alice',
        'role': 'tenant',
      });
      expect(user.id, 1);
      expect(user.email, 'a@b.com');
      expect(user.fullName, 'Alice');
      expect(user.role, 'tenant');
    });
  });
}
