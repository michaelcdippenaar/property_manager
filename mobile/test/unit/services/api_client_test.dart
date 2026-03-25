import 'package:flutter_test/flutter_test.dart';
import 'package:klikk_tenant/services/api_client.dart';

import '../../helpers/mock_secure_storage.dart';

void main() {
  group('ApiClient', () {
    late ApiClient client;
    late MockSecureStorage storage;

    setUp(() {
      storage = MockSecureStorage();
      client = ApiClient(storage: storage);
    });

    test('creates without error', () {
      expect(client, isNotNull);
    });

    test('is an instance of ApiClient', () {
      expect(client, isA<ApiClient>());
    });
  });

  group('ApiException', () {
    test('stores message and statusCode', () {
      final e = ApiException('fail', statusCode: 404);
      expect(e.message, 'fail');
      expect(e.statusCode, 404);
      expect(e.toString(), 'fail');
    });

    test('statusCode is optional', () {
      final e = ApiException('no code');
      expect(e.statusCode, isNull);
    });

    test('implements Exception', () {
      expect(ApiException('x'), isA<Exception>());
    });
  });

  group('ApiClient token refresh lock', () {
    test('client can be instantiated with mock storage', () {
      final storage = MockSecureStorage();
      final client = ApiClient(storage: storage);
      expect(client, isNotNull);
    });

    test('tryRefresh returns false when no refresh token', () async {
      final storage = MockSecureStorage();
      final client = ApiClient(storage: storage);
      final result = await client.tryRefresh();
      expect(result, isFalse);
    });
  });
}
