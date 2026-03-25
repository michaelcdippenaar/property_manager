import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../theme/app_colors.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.user;

    return Scaffold(
      backgroundColor: const Color(0xFFF5F6FA),
      body: Column(
        children: [
          Container(
            color: AppColors.primaryNavy,
            padding: EdgeInsets.fromLTRB(20, MediaQuery.of(context).padding.top + 20, 20, 24),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 28,
                  backgroundColor: Colors.white24,
                  child: Text(
                    user?.fullName.isNotEmpty == true ? user!.fullName[0].toUpperCase() : '?',
                    style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(user?.fullName ?? '—', style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w700)),
                      Text(user?.email ?? '', style: const TextStyle(color: Colors.white60, fontSize: 13)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView(
              children: [
                const SizedBox(height: 20),
                _section('Account', [
                  _tile(Icons.person_outline_rounded, 'Name', user?.fullName ?? '—'),
                  _tile(Icons.email_outlined, 'Email', user?.email ?? '—'),
                  _tile(Icons.badge_outlined, 'Role', user?.role ?? '—'),
                ]),
                const SizedBox(height: 20),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: ListTile(
                    tileColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    leading: const Icon(Icons.logout_rounded, color: Color(0xFFEF4444)),
                    title: const Text('Log out', style: TextStyle(color: Color(0xFFEF4444), fontWeight: FontWeight.w600)),
                    onTap: () async {
                      await context.read<AuthProvider>().logout();
                      if (context.mounted) context.go('/login');
                    },
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _section(String title, List<Widget> tiles) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(left: 4, bottom: 8),
            child: Text(title.toUpperCase(), style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppColors.textSecondary, letterSpacing: 1)),
          ),
          Material(
            color: Colors.white,
            borderRadius: BorderRadius.circular(14),
            child: Column(children: tiles),
          ),
        ],
      ),
    );
  }

  Widget _tile(IconData icon, String label, String value) {
    return ListTile(
      leading: Icon(icon, color: AppColors.primaryNavy, size: 20),
      title: Text(label, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
      subtitle: Text(value, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Color(0xFF1A1A2E))),
    );
  }
}
