import 'package:flutter_test/flutter_test.dart';
import 'package:klikk_tenant/services/info_service.dart';

import '../../helpers/test_data.dart';

void main() {
  group('UnitInfoItem.fromJson', () {
    test('parses valid JSON', () {
      final json = unitInfoItemJson();
      final item = UnitInfoItem.fromJson(json);

      expect(item.id, 1);
      expect(item.iconType, 'wifi');
      expect(item.label, 'WiFi Password');
      expect(item.value, 'secret123');
    });

    test('defaults iconType to "other" when missing', () {
      final json = {'id': 2, 'label': 'Test', 'value': 'V'};
      final item = UnitInfoItem.fromJson(json);

      expect(item.iconType, 'other');
    });

    test('handles null label and value', () {
      final json = {'id': 3};
      final item = UnitInfoItem.fromJson(json);

      expect(item.label, '');
      expect(item.value, '');
    });
  });
}
