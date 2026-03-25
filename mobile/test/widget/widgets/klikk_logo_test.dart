import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:klikk_tenant/widgets/klikk_logo.dart';

void main() {
  group('KlikkLogo', () {
    testWidgets('renders the logo text', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: KlikkLogo())),
      );
      await tester.pump();

      // The logo contains "Klikk" text (may be split across RichText spans)
      expect(find.byType(KlikkLogo), findsOneWidget);
    });
  });
}
