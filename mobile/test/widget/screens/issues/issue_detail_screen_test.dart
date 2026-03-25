import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'package:klikk_tenant/screens/issues/issue_detail_screen.dart';
import 'package:klikk_tenant/theme/app_theme.dart';
import 'package:klikk_tenant/widgets/state_views.dart';

void main() {
  Widget buildSubject({int issueId = 1}) {
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(path: '/', builder: (_, __) => IssueDetailScreen(issueId: issueId)),
      ],
    );
    return MaterialApp.router(
      routerConfig: router,
      theme: AppTheme.light,
    );
  }

  group('IssueDetailScreen', () {
    testWidgets('renders the screen', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(IssueDetailScreen), findsOneWidget);
    });

    testWidgets('shows default title in app bar', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Repair Request'), findsOneWidget);
    });

    testWidgets('shows loading indicator initially', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(LoadingView), findsOneWidget);
    });

    testWidgets('has back button', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byIcon(Icons.arrow_back_rounded), findsOneWidget);
    });
  });
}
