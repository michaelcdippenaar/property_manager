import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'package:klikk_tenant/providers/auth_provider.dart';
import 'package:klikk_tenant/screens/auth/login_email_screen.dart';
import 'package:klikk_tenant/services/auth_service.dart';
import 'package:klikk_tenant/theme/app_theme.dart';

import '../../../helpers/mock_secure_storage.dart';

void main() {
  Widget buildSubject() {
    final router = GoRouter(
      initialLocation: '/login',
      routes: [
        GoRoute(path: '/login', builder: (_, __) => const LoginEmailScreen()),
        GoRoute(path: '/home', builder: (_, __) => const Scaffold(body: Text('Home'))),
        GoRoute(path: '/login/mobile', builder: (_, __) => const Scaffold(body: Text('Mobile Login'))),
        GoRoute(path: '/signup', builder: (_, __) => const Scaffold(body: Text('Signup'))),
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

  group('LoginEmailScreen', () {
    testWidgets('renders email and password fields', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Email'), findsOneWidget);
      expect(find.text('Password'), findsOneWidget);
    });

    testWidgets('renders login button', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('LOGIN'), findsOneWidget);
    });

    testWidgets('shows validation errors on empty submit', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      // Clear any prefilled text
      final emailField = find.byType(TextFormField).first;
      final passwordField = find.byType(TextFormField).last;
      await tester.enterText(emailField, '');
      await tester.enterText(passwordField, '');

      // Tap login
      await tester.tap(find.text('LOGIN'));
      await tester.pump();

      expect(find.text('Enter a valid email'), findsOneWidget);
      expect(find.text('Minimum 6 characters'), findsOneWidget);
    });

    testWidgets('has signup link', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Sign Up'), findsOneWidget);
    });

    testWidgets('has mobile login link', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Login with mobile number'), findsOneWidget);
    });

    testWidgets('has forgot password link', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Forgot password?'), findsOneWidget);
    });
  });
}
