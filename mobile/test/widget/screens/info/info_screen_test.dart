import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:klikk_tenant/screens/info/info_screen.dart';
import 'package:klikk_tenant/theme/app_theme.dart';
import 'package:klikk_tenant/widgets/state_views.dart';

void main() {
  Widget buildSubject() {
    return MaterialApp(
      theme: AppTheme.light,
      home: const InfoScreen(),
    );
  }

  group('InfoScreen', () {
    testWidgets('renders the info screen', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(InfoScreen), findsOneWidget);
    });

    testWidgets('shows header title', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Property Info'), findsOneWidget);
    });

    testWidgets('shows loading indicator initially', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(LoadingView), findsOneWidget);
    });
  });
}
