import 'package:flutter_test/flutter_test.dart';
import 'package:klikk_tenant/services/info_service.dart';

import '../../helpers/test_data.dart';

void main() {
  group('UnitInfoItem model', () {
    test('fromJson parses all fields', () {
      final item = UnitInfoItem.fromJson(unitInfoItemJson());

      expect(item.id, 1);
      expect(item.iconType, 'wifi');
      expect(item.label, 'WiFi Password');
      expect(item.value, 'secret123');
    });

    test('fromJson defaults iconType to "other"', () {
      final item = UnitInfoItem.fromJson({'id': 2});

      expect(item.iconType, 'other');
      expect(item.label, isEmpty);
      expect(item.value, isEmpty);
    });
  });

  group('InfoService', () {
    test('instance can be created', () {
      final service = InfoService();
      expect(service, isNotNull);
    });
  });
}
