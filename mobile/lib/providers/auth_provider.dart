import 'package:flutter/foundation.dart';

import '../services/auth_service.dart';

class AuthProvider extends ChangeNotifier {
  AuthProvider(this._auth);

  final AuthService _auth;

  AuthUser? user;
  bool _restored = false;

  bool get isLoggedIn => user != null;
  bool get restored => _restored;

  Future<void> restore() async {
    final token = await _auth.accessToken;
    if (token == null) {
      _restored = true;
      notifyListeners();
      return;
    }
    try {
      user = await _auth.fetchMe();
    } on AuthException {
      user = null;
    } catch (_) {
      user = null;
    }
    _restored = true;
    notifyListeners();
  }

  Future<void> login(String email, String password) async {
    user = await _auth.login(email, password);
    notifyListeners();
  }

  Future<void> logout() async {
    await _auth.clearTokens();
    user = null;
    notifyListeners();
  }
}
