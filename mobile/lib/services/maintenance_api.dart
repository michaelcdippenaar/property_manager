import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import '../config/api_config.dart';

class MaintenanceIssue {
  MaintenanceIssue({
    required this.id,
    required this.title,
    required this.status,
    required this.priority,
    required this.createdAt,
  });

  final int id;
  final String title;
  final String status;
  final String priority;
  final String createdAt;

  factory MaintenanceIssue.fromJson(Map<String, dynamic> json) {
    return MaintenanceIssue(
      id: json['id'] as int,
      title: json['title'] as String? ?? '',
      status: json['status'] as String? ?? '',
      priority: json['priority'] as String? ?? '',
      createdAt: json['created_at'] as String? ?? '',
    );
  }
}

class MaintenanceApi {
  MaintenanceApi({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  Future<Map<String, String>> _headers() async {
    final t = await _storage.read(key: 'access_token');
    return {
      'Content-Type': 'application/json',
      if (t != null) 'Authorization': 'Bearer $t',
    };
  }

  Future<List<MaintenanceIssue>> listIssues() async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/maintenance/');
    var res = await http.get(uri, headers: await _headers());
    if (res.statusCode == 401) {
      throw MaintenanceException('Session expired');
    }
    if (res.statusCode != 200) {
      throw MaintenanceException('Could not load issues');
    }
    final decoded = jsonDecode(res.body);
    List<dynamic> raw;
    if (decoded is Map<String, dynamic> && decoded['results'] is List) {
      raw = decoded['results'] as List<dynamic>;
    } else if (decoded is List) {
      raw = decoded;
    } else {
      raw = [];
    }
    return raw
        .map((e) => MaintenanceIssue.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

class MaintenanceException implements Exception {
  MaintenanceException(this.message);
  final String message;
  @override
  String toString() => message;
}
