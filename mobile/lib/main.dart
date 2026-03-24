import 'package:flutter/material.dart';
import 'theme/app_theme.dart';
import 'router/app_router.dart';

void main() {
  runApp(const KlikkApp());
}

class KlikkApp extends StatelessWidget {
  const KlikkApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Klikk',
      theme: AppTheme.light,
      routerConfig: appRouter,
      debugShowCheckedModeBanner: false,
    );
  }
}
