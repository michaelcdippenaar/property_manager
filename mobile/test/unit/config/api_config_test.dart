import 'package:flutter_test/flutter_test.dart';
import 'package:klikk_tenant/config/api_config.dart';

void main() {
  group('ApiConfig', () {
    test('baseUrl returns a non-empty string', () {
      final url = ApiConfig.baseUrl;
      expect(url, isNotEmpty);
    });

    test('baseUrl does not end with a slash', () {
      final url = ApiConfig.baseUrl;
      expect(url.endsWith('/'), isFalse);
    });

    test('baseUrl contains /api/v1', () {
      final url = ApiConfig.baseUrl;
      expect(url, contains('/api/v1'));
    });

    test('baseUrl starts with http', () {
      final url = ApiConfig.baseUrl;
      expect(url.startsWith('http'), isTrue);
    });
  });
}
