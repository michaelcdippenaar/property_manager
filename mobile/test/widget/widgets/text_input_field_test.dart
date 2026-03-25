import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:klikk_tenant/widgets/text_input_field.dart';

import '../../helpers/pump_app.dart';

void main() {
  group('TextInputField', () {
    testWidgets('renders label', (tester) async {
      final ctrl = TextEditingController();
      await pumpWidget(
        tester,
        TextInputField(label: 'Email', controller: ctrl),
      );
      await tester.pump();

      expect(find.text('Email'), findsOneWidget);
    });

    testWidgets('toggles password visibility', (tester) async {
      final ctrl = TextEditingController(text: 'secret');
      await pumpWidget(
        tester,
        TextInputField(label: 'Password', controller: ctrl, isPassword: true),
      );
      await tester.pump();

      // Initially obscured — find the visibility toggle icon
      expect(find.byIcon(Icons.visibility_outlined), findsOneWidget);

      // Tap the visibility toggle
      await tester.tap(find.byIcon(Icons.visibility_outlined));
      await tester.pump();

      // Now should show visibility_off
      expect(find.byIcon(Icons.visibility_off_outlined), findsOneWidget);
    });

    testWidgets('accepts text input', (tester) async {
      final ctrl = TextEditingController();
      await pumpWidget(
        tester,
        TextInputField(label: 'Name', controller: ctrl),
      );
      await tester.pump();

      await tester.enterText(find.byType(TextFormField), 'Alice');
      expect(ctrl.text, 'Alice');
    });

    testWidgets('runs validator', (tester) async {
      final ctrl = TextEditingController();
      final formKey = GlobalKey<FormState>();
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Form(
              key: formKey,
              child: TextInputField(
                label: 'Email',
                controller: ctrl,
                validator: (v) => v == null || v.isEmpty ? 'Required' : null,
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      formKey.currentState!.validate();
      await tester.pump();

      expect(find.text('Required'), findsOneWidget);
    });
  });
}
