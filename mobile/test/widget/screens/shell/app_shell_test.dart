import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:klikk_tenant/providers/auth_provider.dart';
import 'package:klikk_tenant/screens/shell/app_shell.dart';
import 'package:klikk_tenant/services/auth_service.dart';
import 'package:klikk_tenant/theme/app_theme.dart';

import '../../../helpers/mock_secure_storage.dart';

void main() {
  Widget buildSubject() {
    return ChangeNotifierProvider<AuthProvider>(
      create: (_) => AuthProvider(AuthService(storage: MockSecureStorage())),
      child: MaterialApp(
        theme: AppTheme.light,
        home: const AppShell(),
      ),
    );
  }

  group('AppShell', () {
    testWidgets('shows bottom navigation with 4 destinations', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(NavigationBar), findsOneWidget);
      expect(find.byType(NavigationDestination), findsNWidgets(4));
    });

    testWidgets('shows Home, Repairs, Info, Settings labels', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Home'), findsOneWidget);
      expect(find.text('Repairs'), findsOneWidget);
      expect(find.text('Info'), findsOneWidget);
      expect(find.text('Settings'), findsOneWidget);
    });

    testWidgets('renders AppShell widget', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(AppShell), findsOneWidget);
      expect(find.byType(IndexedStack), findsOneWidget);
    });
  });
}
