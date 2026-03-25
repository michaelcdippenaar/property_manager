import 'dart:io';

/// Backend API base including `/api/v1`.
///
/// **Physical phone (iOS or Android):** `127.0.0.1` and `10.0.2.2` only work on
/// simulators/emulators. On a real device, pass your Mac's LAN IP:
/// `flutter run --dart-define=API_BASE_URL=http://192.168.x.x:8000/api/v1`
class ApiConfig {
  ApiConfig._();

  static String get baseUrl {
    const fromEnv = String.fromEnvironment('API_BASE_URL');
    if (fromEnv.isNotEmpty) {
      return fromEnv.endsWith('/') ? fromEnv.substring(0, fromEnv.length - 1) : fromEnv;
    }
    // Android emulator: host machine loopback. Not for physical Android.
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000/api/v1';
    }
    // iOS simulator and default iOS: host loopback. Not for physical iPhone.
    return 'http://127.0.0.1:8000/api/v1';
  }
}
