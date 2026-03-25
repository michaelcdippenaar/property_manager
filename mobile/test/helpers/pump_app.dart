import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'package:klikk_tenant/providers/auth_provider.dart';
import 'package:klikk_tenant/services/auth_service.dart';
import 'package:klikk_tenant/theme/app_theme.dart';

/// Wraps [child] in the full app scaffold for widget tests:
/// MaterialApp.router + AuthProvider + Theme.
///
/// If [authProvider] is null, a default one is created.
/// If [router] is null, a simple one-route router showing [child] is created.
Future<void> pumpApp(
  WidgetTester tester,
  Widget child, {
  AuthProvider? authProvider,
  GoRouter? router,
}) async {
  final effectiveRouter = router ??
      GoRouter(
        initialLocation: '/',
        routes: [
          GoRoute(path: '/', builder: (_, __) => child),
        ],
      );

  await tester.pumpWidget(
    ChangeNotifierProvider<AuthProvider>(
      create: (_) => authProvider ?? AuthProvider(AuthService()),
      child: MaterialApp.router(
        routerConfig: effectiveRouter,
        theme: AppTheme.light,
      ),
    ),
  );
}

/// Convenience: pump a simple scaffold-wrapped widget.
Future<void> pumpWidget(WidgetTester tester, Widget child) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: AppTheme.light,
      home: Scaffold(body: child),
    ),
  );
}
