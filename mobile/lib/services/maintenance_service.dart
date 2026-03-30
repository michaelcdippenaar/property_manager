import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../config/api_config.dart';
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

class MaintenanceActivity {
  MaintenanceActivity({
    required this.id,
    required this.activityType,
    required this.message,
    this.file,
    this.createdByName,
    this.createdByRole,
    required this.createdAt,
    this.metadata,
  });

  final int id;
  final String activityType;
  final String message;
  final String? file;
  final String? createdByName;
  final String? createdByRole;
  final String createdAt;
  final Map<String, dynamic>? metadata;

  bool get isAi => metadata?['source'] == 'ai_agent';
  bool get hasFile => file != null && file!.isNotEmpty;
  bool get isImage => hasFile && RegExp(r'\.(jpg|jpeg|png|gif|webp)$', caseSensitive: false).hasMatch(file!);

  factory MaintenanceActivity.fromJson(Map<String, dynamic> j) => MaintenanceActivity(
    id: j['id'] as int,
    activityType: j['activity_type'] as String? ?? 'note',
    message: j['message'] as String? ?? '',
    file: j['file'] as String?,
    createdByName: j['created_by_name'] as String?,
    createdByRole: j['created_by_role'] as String?,
    createdAt: j['created_at'] as String? ?? '',
    metadata: j['metadata'] as Map<String, dynamic>?,
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
    int? conversationId,
  }) async {
    final body = <String, dynamic>{
      'title': title,
      'description': description,
      'category': category,
      'priority': priority,
    };
    if (conversationId != null) {
      body['conversation_id'] = conversationId;
    }
    final data = await apiClient.post('/maintenance/', body: body);
    return MaintenanceIssue.fromJson(data);
  }

  Future<List<MaintenanceActivity>> getActivities(int issueId) async {
    final data = await apiClient.getList('/maintenance/$issueId/activity/');
    return (data as List)
        .map((e) => MaintenanceActivity.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<MaintenanceActivity> postActivity(int issueId, String message, {String activityType = 'note'}) async {
    final data = await apiClient.post('/maintenance/$issueId/activity/', body: {
      'message': message,
      'activity_type': activityType,
    });
    return MaintenanceActivity.fromJson(data);
  }

  Future<MaintenanceActivity> postActivityWithFile(int issueId, String filePath, {String message = ''}) async {
    final token = await const FlutterSecureStorage().read(key: 'access_token');
    final uri = Uri.parse('${ApiConfig.baseUrl}/maintenance/$issueId/activity/');
    final req = http.MultipartRequest('POST', uri);
    if (token != null) req.headers['Authorization'] = 'Bearer $token';
    req.fields['message'] = message;
    req.fields['activity_type'] = 'note';
    final name = filePath.split(Platform.pathSeparator).last;
    req.files.add(await http.MultipartFile.fromPath('file', filePath, filename: name));
    final streamed = await req.send();
    final res = await http.Response.fromStream(streamed);
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw Exception('Upload failed (${res.statusCode})');
    }
    return MaintenanceActivity.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }
}

final maintenanceService = MaintenanceService();
