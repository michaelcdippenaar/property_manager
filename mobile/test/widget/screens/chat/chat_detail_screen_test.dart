import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'package:klikk_tenant/screens/chat/chat_detail_screen.dart';
import 'package:klikk_tenant/theme/app_theme.dart';

void main() {
  Widget buildSubject({int conversationId = 1}) {
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(path: '/', builder: (_, __) => ChatDetailScreen(conversationId: conversationId)),
      ],
    );
    return MaterialApp.router(
      routerConfig: router,
      theme: AppTheme.light,
    );
  }

  group('ChatDetailScreen', () {
    testWidgets('renders the chat detail screen', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(ChatDetailScreen), findsOneWidget);
    });

    testWidgets('shows default AI Assistant title', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('AI Assistant'), findsOneWidget);
    });

    testWidgets('shows loading indicator initially', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('has back button', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byIcon(Icons.arrow_back_rounded), findsOneWidget);
    });

    testWidgets('has message input field', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(TextField), findsOneWidget);
    });

    testWidgets('has send button', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byIcon(Icons.send_rounded), findsOneWidget);
    });

    testWidgets('has attachment button', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byIcon(Icons.attach_file_rounded), findsOneWidget);
    });
  });
}
