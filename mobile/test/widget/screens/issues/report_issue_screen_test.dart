import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'package:klikk_tenant/screens/issues/report_issue_screen.dart';
import 'package:klikk_tenant/theme/app_theme.dart';

void main() {
  Widget buildSubject({Map<String, dynamic>? initialDraft}) {
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(path: '/', builder: (_, __) => ReportIssueScreen(initialDraft: initialDraft)),
      ],
    );

    return MaterialApp.router(
      routerConfig: router,
      theme: AppTheme.light,
    );
  }

  group('ReportIssueScreen', () {
    testWidgets('renders form fields', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Report a Repair'), findsOneWidget);
      expect(find.text('What needs fixing?'), findsOneWidget);
      expect(find.text('Describe the problem'), findsOneWidget);
      expect(find.text('Category'), findsOneWidget);
      expect(find.text('Priority'), findsOneWidget);
    });

    testWidgets('renders submit button', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Submit Request'), findsOneWidget);
    });

    testWidgets('validates required title field', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      // Submit without filling
      await tester.tap(find.text('Submit Request'));
      await tester.pump();

      expect(find.text('Required'), findsWidgets);
    });

    testWidgets('pre-fills from initialDraft', (tester) async {
      await tester.pumpWidget(buildSubject(
        initialDraft: {
          'title': 'Broken window',
          'description': 'Glass cracked',
          'priority': 'high',
          'category': 'security',
        },
      ));
      await tester.pump();

      expect(find.text('Broken window'), findsOneWidget);
      expect(find.text('Glass cracked'), findsOneWidget);
    });

    testWidgets('has close button in app bar', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byIcon(Icons.close_rounded), findsOneWidget);
    });
  });
}
