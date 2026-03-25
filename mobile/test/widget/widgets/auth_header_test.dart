import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:klikk_tenant/widgets/auth_header.dart';

void main() {
  group('AuthHeader', () {
    testWidgets('renders without error', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: AuthHeader()),
        ),
      );
      await tester.pump();

      expect(find.byType(AuthHeader), findsOneWidget);
    });
  });
}
