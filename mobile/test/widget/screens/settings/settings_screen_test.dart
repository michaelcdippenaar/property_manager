import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'package:klikk_tenant/providers/auth_provider.dart';
import 'package:klikk_tenant/screens/settings/settings_screen.dart';
import 'package:klikk_tenant/services/auth_service.dart';
import 'package:klikk_tenant/theme/app_theme.dart';

import '../../../helpers/mock_secure_storage.dart';

void main() {
  Widget buildSubject() {
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(path: '/', builder: (_, __) => const SettingsScreen()),
        GoRoute(path: '/login', builder: (_, __) => const Scaffold(body: Text('Login'))),
      ],
    );

    return ChangeNotifierProvider<AuthProvider>(
      create: (_) => AuthProvider(AuthService(storage: MockSecureStorage())),
      child: MaterialApp.router(
        routerConfig: router,
        theme: AppTheme.light,
      ),
    );
  }

  group('SettingsScreen', () {
    testWidgets('renders the settings screen', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(SettingsScreen), findsOneWidget);
    });

    testWidgets('shows account section', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('ACCOUNT'), findsOneWidget);
    });

    testWidgets('shows account info labels', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Name'), findsOneWidget);
      expect(find.text('Email'), findsOneWidget);
      expect(find.text('Role'), findsOneWidget);
    });

    testWidgets('shows logout button', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Log out'), findsOneWidget);
    });

    testWidgets('logout navigates to login', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      await tester.tap(find.text('Log out'));
      await tester.pumpAndSettle();

      expect(find.text('Login'), findsOneWidget);
    });
  });
}
