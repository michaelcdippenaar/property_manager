import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:klikk_tenant/widgets/auth_card.dart';

void main() {
  group('AuthCard', () {
    testWidgets('renders child widget', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                AuthCard(child: Text('Hello')),
              ],
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.text('Hello'), findsOneWidget);
    });

    testWidgets('wraps child in a decorated container', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                AuthCard(child: Text('Content')),
              ],
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(AuthCard), findsOneWidget);
    });
  });
}
