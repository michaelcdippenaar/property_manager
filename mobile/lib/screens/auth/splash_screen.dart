import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../theme/app_colors.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});
  @override State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    final auth = context.read<AuthProvider>();
    try {
      await auth.restore().timeout(const Duration(seconds: 5));
    } catch (_) {
      // Timeout or error — proceed to login
    }
    if (!mounted) return;
    if (auth.isLoggedIn) {
      context.go('/home');
      return;
    }
    context.go('/login');
  }

  @override
  Widget build(BuildContext context) => const Scaffold(
    backgroundColor: AppColors.primaryNavy,
    body: Center(child: CircularProgressIndicator(color: Colors.white)),
  );
}
