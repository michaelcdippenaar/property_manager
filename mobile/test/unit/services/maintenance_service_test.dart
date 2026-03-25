import 'package:flutter_test/flutter_test.dart';
import 'package:klikk_tenant/services/maintenance_service.dart';

import '../../helpers/test_data.dart';

void main() {
  group('MaintenanceIssue model', () {
    test('fromJson parses all fields', () {
      final issue = MaintenanceIssue.fromJson(maintenanceIssueJson());

      expect(issue.id, 1);
      expect(issue.title, 'Leaking tap');
      expect(issue.description, 'Kitchen tap is dripping');
      expect(issue.status, 'open');
      expect(issue.priority, 'medium');
      expect(issue.category, 'plumbing');
      expect(issue.ticketRef, 'MNT-001');
    });

    test('fromJson handles missing fields gracefully', () {
      final issue = MaintenanceIssue.fromJson({'id': 10});

      expect(issue.title, isEmpty);
      expect(issue.description, isEmpty);
      expect(issue.status, isEmpty);
    });

    test('fromJson with custom values', () {
      final issue = MaintenanceIssue.fromJson(
        maintenanceIssueJson(id: 50, status: 'closed', priority: 'urgent'),
      );

      expect(issue.id, 50);
      expect(issue.status, 'closed');
      expect(issue.priority, 'urgent');
    });
  });

  group('MaintenanceService', () {
    test('instance can be created', () {
      final service = MaintenanceService();
      expect(service, isNotNull);
    });
  });
}
