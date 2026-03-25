import 'api_client.dart';

/// Minimal lease summary for tenant flows (full lease lives on the server).
class TenantLease {
  TenantLease({
    required this.id,
    required this.status,
    required this.unitLabel,
  });

  final int id;
  final String status;
  final String unitLabel;

  factory TenantLease.fromJson(Map<String, dynamic> j) => TenantLease(
        id: j['id'] as int,
        status: j['status'] as String? ?? '',
        unitLabel: j['unit_label'] as String? ?? '',
      );
}

class LeaseService {
  Future<List<TenantLease>> listLeases() async {
    final data = await apiClient.getList('/leases/');
    return (data as List)
        .map((e) => TenantLease.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

final leaseService = LeaseService();
