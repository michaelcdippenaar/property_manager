import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';

class ApiException implements Exception {
  ApiException(this.message, {this.statusCode});
  final String message;
  final int? statusCode;
  @override String toString() => message;
}

class ApiClient {
  ApiClient({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;
  static const _kAccess = 'access_token';
  static const _kRefresh = 'refresh_token';

  Future<String?> get _token => _storage.read(key: _kAccess);

  Map<String, String> _headers(String? token) => {
    'Content-Type': 'application/json',
    if (token != null) 'Authorization': 'Bearer $token',
  };

  Future<Map<String, dynamic>> get(String path, {Map<String, String>? params}) async {
    final token = await _token;
    final uri = Uri.parse('${ApiConfig.baseUrl}$path').replace(queryParameters: params);
    var res = await http.get(uri, headers: _headers(token));
    if (res.statusCode == 401) {
      final refreshed = await _tryRefresh();
      if (!refreshed) throw ApiException('Session expired', statusCode: 401);
      final newToken = await _token;
      res = await http.get(uri, headers: _headers(newToken));
    }
    return _parse(res);
  }

  Future<dynamic> getList(String path, {Map<String, String>? params}) async {
    final token = await _token;
    final uri = Uri.parse('${ApiConfig.baseUrl}$path').replace(queryParameters: params);
    var res = await http.get(uri, headers: _headers(token));
    if (res.statusCode == 401) {
      final refreshed = await _tryRefresh();
      if (!refreshed) throw ApiException('Session expired', statusCode: 401);
      final newToken = await _token;
      res = await http.get(uri, headers: _headers(newToken));
    }
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException('Request failed (${res.statusCode})', statusCode: res.statusCode);
    }
    final body = jsonDecode(res.body);
    if (body is Map && body.containsKey('results')) return body['results'];
    return body;
  }

  Future<Map<String, dynamic>> post(String path, {Map<String, dynamic>? body}) async {
    final token = await _token;
    final uri = Uri.parse('${ApiConfig.baseUrl}$path');
    var res = await http.post(uri, headers: _headers(token), body: jsonEncode(body ?? {}));
    if (res.statusCode == 401) {
      final refreshed = await _tryRefresh();
      if (!refreshed) throw ApiException('Session expired', statusCode: 401);
      final newToken = await _token;
      res = await http.post(uri, headers: _headers(newToken), body: jsonEncode(body ?? {}));
    }
    return _parse(res);
  }

  Future<Map<String, dynamic>> patch(String path, {Map<String, dynamic>? body}) async {
    final token = await _token;
    final uri = Uri.parse('${ApiConfig.baseUrl}$path');
    var res = await http.patch(uri, headers: _headers(token), body: jsonEncode(body ?? {}));
    if (res.statusCode == 401) {
      final refreshed = await _tryRefresh();
      if (!refreshed) throw ApiException('Session expired', statusCode: 401);
      final newToken = await _token;
      res = await http.patch(uri, headers: _headers(newToken), body: jsonEncode(body ?? {}));
    }
    return _parse(res);
  }

  Map<String, dynamic> _parse(http.Response res) {
    if (res.statusCode < 200 || res.statusCode >= 300) {
      String msg = 'Request failed (${res.statusCode})';
      try {
        final b = jsonDecode(res.body);
        if (b is Map) {
          msg = b['detail']?.toString() ?? b['error']?.toString() ?? msg;
        }
      } catch (_) {}
      throw ApiException(msg, statusCode: res.statusCode);
    }
    if (res.body.isEmpty) return {};
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<bool> _tryRefresh() async {
    final refresh = await _storage.read(key: _kRefresh);
    if (refresh == null) return false;
    try {
      final uri = Uri.parse('${ApiConfig.baseUrl}/auth/token/refresh/');
      final res = await http.post(
        uri,
        headers: const {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh': refresh}),
      );
      if (res.statusCode != 200) {
        await _storage.delete(key: _kAccess);
        await _storage.delete(key: _kRefresh);
        return false;
      }
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      final access = data['access'] as String?;
      if (access == null) return false;
      await _storage.write(key: _kAccess, value: access);
      return true;
    } catch (_) {
      return false;
    }
  }
}

final apiClient = ApiClient();
