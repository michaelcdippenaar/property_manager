import 'dart:async';
import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../config/api_config.dart';
import 'maintenance_service.dart';

/// Real-time WebSocket connection for a maintenance issue's activity feed.
///
/// Connects to `ws://host/ws/maintenance/{issueId}/activity/?token={jwt}`.
/// Emits [MaintenanceActivity] items via [activities] stream.
class MaintenanceChatSocket {
  MaintenanceChatSocket({required this.issueId});

  final int issueId;

  WebSocketChannel? _channel;
  final _controller = StreamController<SocketEvent>.broadcast();
  Timer? _reconnectTimer;
  bool _disposed = false;
  int _reconnectAttempts = 0;
  static const _maxReconnectAttempts = 5;
  static const _reconnectBaseDelay = Duration(seconds: 2);

  /// Stream of incoming activities (both history batches and single new messages).
  Stream<SocketEvent> get events => _controller.stream;

  /// Connect to the WebSocket server.
  Future<void> connect() async {
    if (_disposed) return;

    final token = await const FlutterSecureStorage().read(key: 'access_token');
    if (token == null) {
      _controller.addError(Exception('No auth token'));
      return;
    }

    // Convert http(s) base URL to ws(s) and strip /api/v1 suffix.
    final httpBase = ApiConfig.baseUrl
        .replaceFirst(RegExp(r'/api/v1$'), '');
    final wsBase = httpBase
        .replaceFirst('https://', 'wss://')
        .replaceFirst('http://', 'ws://');

    final uri = Uri.parse('$wsBase/ws/maintenance/$issueId/activity/?token=$token');

    try {
      _channel = IOWebSocketChannel.connect(
        uri,
        pingInterval: const Duration(seconds: 30),
      );
      _reconnectAttempts = 0;

      _channel!.stream.listen(
        _onData,
        onError: _onError,
        onDone: _onDone,
      );
    } catch (e) {
      _controller.addError(e);
      _scheduleReconnect();
    }
  }

  void _onData(dynamic raw) {
    try {
      final data = jsonDecode(raw as String) as Map<String, dynamic>;
      final type = data['type'] as String? ?? '';

      if (type == 'history') {
        final list = (data['activities'] as List)
            .map((e) => MaintenanceActivity.fromJson(e as Map<String, dynamic>))
            .toList();
        _controller.add(SocketEvent.history(list));
      } else if (type == 'activity') {
        final activity = MaintenanceActivity.fromJson(
            data['activity'] as Map<String, dynamic>);
        _controller.add(SocketEvent.message(activity));
      } else if (type == 'error') {
        _controller.addError(Exception(data['message'] ?? 'Unknown error'));
      }
    } catch (e) {
      _controller.addError(e);
    }
  }

  void _onError(Object error) {
    _controller.addError(error);
    _scheduleReconnect();
  }

  void _onDone() {
    if (!_disposed) {
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (_disposed || _reconnectAttempts >= _maxReconnectAttempts) return;
    _reconnectTimer?.cancel();
    final delay = _reconnectBaseDelay * (1 << _reconnectAttempts);
    _reconnectAttempts++;
    _reconnectTimer = Timer(delay, connect);
  }

  /// Send a chat message through the WebSocket.
  void sendMessage(String message, {String activityType = 'note'}) {
    final payload = jsonEncode({
      'message': message,
      'activity_type': activityType,
    });
    _channel?.sink.add(payload);
  }

  /// Close the connection and release resources.
  void dispose() {
    _disposed = true;
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _controller.close();
  }
}

/// Internal event type for the socket stream.
class SocketEvent {
  SocketEvent.history(this.history) : activity = null, isHistory = true;
  SocketEvent.message(this.activity) : history = null, isHistory = false;

  final bool isHistory;
  final List<MaintenanceActivity>? history;
  final MaintenanceActivity? activity;
}
