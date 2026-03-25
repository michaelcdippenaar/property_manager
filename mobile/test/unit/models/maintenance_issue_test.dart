import 'package:flutter_test/flutter_test.dart';
import 'package:klikk_tenant/services/maintenance_service.dart';

import '../../helpers/test_data.dart';

void main() {
  group('MaintenanceIssue.fromJson', () {
    test('parses full JSON', () {
      final json = maintenanceIssueJson();
      final issue = MaintenanceIssue.fromJson(json);

      expect(issue.id, 1);
      expect(issue.title, 'Leaking tap');
      expect(issue.description, 'Kitchen tap is dripping');
      expect(issue.status, 'open');
      expect(issue.priority, 'medium');
      expect(issue.category, 'plumbing');
      expect(issue.ticketRef, 'MNT-001');
      expect(issue.createdAt, '2025-01-15T10:00:00Z');
    });

    test('handles missing optional fields with empty defaults', () {
      final json = {'id': 5};
      final issue = MaintenanceIssue.fromJson(json);

      expect(issue.id, 5);
      expect(issue.title, '');
      expect(issue.description, '');
      expect(issue.status, '');
      expect(issue.priority, '');
      expect(issue.category, '');
      expect(issue.ticketRef, '');
      expect(issue.createdAt, '');
    });

    test('preserves all field types', () {
      final issue = MaintenanceIssue.fromJson(maintenanceIssueJson(id: 99, status: 'resolved'));

      expect(issue.id, isA<int>());
      expect(issue.id, 99);
      expect(issue.status, 'resolved');
    });
  });
}
