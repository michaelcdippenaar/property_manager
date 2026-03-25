import 'package:flutter_test/flutter_test.dart';
import 'package:klikk_tenant/services/auth_service.dart';

import '../../helpers/test_data.dart';

void main() {
  group('AuthUser.fromJson', () {
    test('parses valid JSON correctly', () {
      final json = authUserJson();
      final user = AuthUser.fromJson(json);

      expect(user.id, 1);
      expect(user.email, 'test@example.com');
      expect(user.fullName, 'Test User');
      expect(user.role, 'tenant');
    });

    test('handles missing full_name by falling back to email', () {
      final json = {'id': 2, 'email': 'a@b.com'};
      final user = AuthUser.fromJson(json);

      expect(user.fullName, 'a@b.com');
    });

    test('handles null optional fields with empty defaults', () {
      final json = {'id': 3};
      final user = AuthUser.fromJson(json);

      expect(user.email, '');
      expect(user.fullName, '');
      expect(user.role, '');
    });

    test('preserves all field types correctly', () {
      final user = AuthUser.fromJson(authUserJson(id: 42, email: 'x@y.z', fullName: 'Jane', role: 'admin'));

      expect(user.id, isA<int>());
      expect(user.email, isA<String>());
      expect(user.id, 42);
      expect(user.role, 'admin');
    });
  });
}
