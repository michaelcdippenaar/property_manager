import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:klikk_tenant/widgets/primary_button.dart';

import '../../helpers/pump_app.dart';

void main() {
  group('PrimaryButton', () {
    testWidgets('renders label text uppercased', (tester) async {
      await pumpWidget(tester, const PrimaryButton(label: 'Login'));
      await tester.pump();

      expect(find.text('LOGIN'), findsOneWidget);
    });

    testWidgets('shows CircularProgressIndicator when loading', (tester) async {
      await pumpWidget(
        tester,
        const PrimaryButton(label: 'Login', isLoading: true),
      );
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text('LOGIN'), findsNothing);
    });

    testWidgets('disables button when loading', (tester) async {
      bool tapped = false;
      await pumpWidget(
        tester,
        PrimaryButton(label: 'Go', isLoading: true, onPressed: () => tapped = true),
      );
      await tester.pump();

      await tester.tap(find.byType(ElevatedButton));
      expect(tapped, isFalse);
    });

    testWidgets('calls onPressed when tapped', (tester) async {
      bool tapped = false;
      await pumpWidget(
        tester,
        PrimaryButton(label: 'Go', onPressed: () => tapped = true),
      );
      await tester.pump();

      await tester.tap(find.byType(ElevatedButton));
      expect(tapped, isTrue);
    });
  });
}
