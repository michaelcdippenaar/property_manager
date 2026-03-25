import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:klikk_tenant/screens/issues/issues_screen.dart';
import 'package:klikk_tenant/theme/app_theme.dart';
import 'package:klikk_tenant/widgets/state_views.dart';

void main() {
  Widget buildSubject() {
    return MaterialApp(
      theme: AppTheme.light,
      home: const IssuesScreen(),
    );
  }

  group('IssuesScreen', () {
    testWidgets('renders the issues screen', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(IssuesScreen), findsOneWidget);
    });

    testWidgets('shows header title', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('My Repairs'), findsOneWidget);
    });

    testWidgets('shows loading indicator initially', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(LoadingView), findsOneWidget);
    });

    testWidgets('has FAB for reporting', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(FloatingActionButton), findsOneWidget);
      expect(find.byIcon(Icons.add_rounded), findsOneWidget);
    });
  });
}
