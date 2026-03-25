import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import 'api_client.dart';

class AuthUser {
  AuthUser({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
  });

  final int id;
  final String email;
  final String fullName;
  final String role;

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    return AuthUser(
      id: json['id'] as int,
      email: json['email'] as String? ?? '',
      fullName: json['full_name'] as String? ?? json['email'] as String? ?? '',
      role: json['role'] as String? ?? '',
    );
  }
}

class AuthException implements Exception {
  AuthException(this.message);
  final String message;
  @override
  String toString() => message;
}

class AuthService {
  AuthService({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  static const _kAccess = 'access_token';
  static const _kRefresh = 'refresh_token';

  Future<String?> get accessToken => _storage.read(key: _kAccess);

  Future<void> _saveTokens(String access, String refresh) async {
    await _storage.write(key: _kAccess, value: access);
    await _storage.write(key: _kRefresh, value: refresh);
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: _kAccess);
    await _storage.delete(key: _kRefresh);
  }

  Future<AuthUser> login(String email, String password) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/auth/login/');
    final res = await http.post(
      uri,
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );
    if (res.statusCode != 200) {
      String msg = 'Login failed';
      try {
        final body = jsonDecode(res.body);
        if (body is Map<String, dynamic>) {
          final detail = body['detail'];
          if (detail is String) msg = detail;
          final nfe = body['non_field_errors'];
          if (nfe is List && nfe.isNotEmpty) {
            msg = nfe.first.toString();
          }
        }
      } catch (_) {}
      throw AuthException(msg);
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    final access = data['access'] as String?;
    final refresh = data['refresh'] as String?;
    if (access == null || refresh == null) {
      throw AuthException('Invalid server response');
    }
    await _saveTokens(access, refresh);
    final userJson = data['user'] as Map<String, dynamic>?;
    if (userJson != null) {
      return AuthUser.fromJson(userJson);
    }
    return fetchMe();
  }

  Future<AuthUser> fetchMe() async {
    final token = await _storage.read(key: _kAccess);
    if (token == null) throw AuthException('Not signed in');
    final uri = Uri.parse('${ApiConfig.baseUrl}/auth/me/');
    final res = await http.get(
      uri,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
    );
    if (res.statusCode == 401) {
      await clearTokens();
      throw AuthException('Session expired');
    }
    if (res.statusCode != 200) {
      throw AuthException('Could not load profile');
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    return AuthUser.fromJson(data);
  }

  /// Delegates to [ApiClient] to avoid duplicate refresh logic.
  Future<bool> tryRefresh() => apiClient.tryRefresh();
}
