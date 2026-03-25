import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:klikk_tenant/providers/auth_provider.dart';
import 'package:klikk_tenant/screens/home/home_screen.dart';
import 'package:klikk_tenant/services/auth_service.dart';
import 'package:klikk_tenant/theme/app_theme.dart';
import 'package:klikk_tenant/widgets/state_views.dart';

import '../../../helpers/mock_secure_storage.dart';

void main() {
  Widget buildSubject() {
    return ChangeNotifierProvider<AuthProvider>(
      create: (_) => AuthProvider(AuthService(storage: MockSecureStorage())),
      child: MaterialApp(
        theme: AppTheme.light,
        home: const HomeScreen(),
      ),
    );
  }

  group('HomeScreen', () {
    testWidgets('renders the home screen', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(HomeScreen), findsOneWidget);
    });

    testWidgets('shows greeting', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      // Without a logged-in user, shows default greeting
      expect(find.textContaining('Hi,'), findsOneWidget);
    });

    testWidgets('shows welcome message', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Welcome home'), findsOneWidget);
    });

    testWidgets('shows loading indicator initially', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(LoadingView), findsOneWidget);
    });

    testWidgets('has AI chat FAB', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(FloatingActionButton), findsOneWidget);
      expect(find.text('AI'), findsOneWidget);
    });
  });
}
