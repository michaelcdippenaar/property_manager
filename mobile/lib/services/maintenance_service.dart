import 'api_client.dart';

class MaintenanceIssue {
  MaintenanceIssue({
    required this.id,
    required this.title,
    required this.description,
    required this.status,
    required this.priority,
    required this.category,
    required this.ticketRef,
    required this.createdAt,
  });

  final int id;
  final String title;
  final String description;
  final String status;
  final String priority;
  final String category;
  final String ticketRef;
  final String createdAt;

  factory MaintenanceIssue.fromJson(Map<String, dynamic> j) => MaintenanceIssue(
    id: j['id'] as int,
    title: j['title'] as String? ?? '',
    description: j['description'] as String? ?? '',
    status: j['status'] as String? ?? '',
    priority: j['priority'] as String? ?? '',
    category: j['category'] as String? ?? '',
    ticketRef: j['ticket_reference'] as String? ?? '',
    createdAt: j['created_at'] as String? ?? '',
  );
}

class MaintenanceService {
  Future<List<MaintenanceIssue>> listIssues({Map<String, String>? params}) async {
    final data = await apiClient.getList('/maintenance/', params: params);
    return (data as List).map((e) => MaintenanceIssue.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<MaintenanceIssue> getIssue(int id) async {
    final data = await apiClient.get('/maintenance/$id/');
    return MaintenanceIssue.fromJson(data);
  }

  Future<MaintenanceIssue> createIssue({
    required String title,
    required String description,
    required String category,
    required String priority,
  }) async {
    final data = await apiClient.post('/maintenance/', body: {
      'title': title,
      'description': description,
      'category': category,
      'priority': priority,
    });
    return MaintenanceIssue.fromJson(data);
  }
}

final maintenanceService = MaintenanceService();
