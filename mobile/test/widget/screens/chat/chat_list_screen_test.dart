import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:klikk_tenant/screens/chat/chat_list_screen.dart';
import 'package:klikk_tenant/theme/app_theme.dart';
import 'package:klikk_tenant/widgets/state_views.dart';

void main() {
  Widget buildSubject() {
    return MaterialApp(
      theme: AppTheme.light,
      home: const ChatListScreen(),
    );
  }

  group('ChatListScreen', () {
    testWidgets('renders the chat list screen', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(ChatListScreen), findsOneWidget);
    });

    testWidgets('shows AI Assistant header', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('AI Assistant'), findsOneWidget);
    });

    testWidgets('shows loading indicator initially', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(LoadingView), findsOneWidget);
    });

    testWidgets('has FAB for new chat', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(FloatingActionButton), findsOneWidget);
      expect(find.byIcon(Icons.add_rounded), findsOneWidget);
    });
  });
}
