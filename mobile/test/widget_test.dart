import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:klikk_tenant/main.dart';
import 'package:klikk_tenant/providers/auth_provider.dart';
import 'package:klikk_tenant/services/auth_service.dart';

import 'helpers/mock_secure_storage.dart';

void main() {
  testWidgets('app builds', (WidgetTester tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => AuthProvider(AuthService(storage: MockSecureStorage())),
        child: const KlikkApp(),
      ),
    );
    await tester.pump();
    expect(find.byType(MaterialApp), findsOneWidget);

    // SplashScreen starts a timer — let it complete to avoid pending timer error.
    await tester.pumpAndSettle(const Duration(seconds: 6));
  });
}
