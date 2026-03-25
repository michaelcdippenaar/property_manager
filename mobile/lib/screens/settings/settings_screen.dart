import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_radius.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/app_header.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.user;

    return Scaffold(
      backgroundColor: AppColors.scaffoldBackground,
      body: Column(
        children: [
          AppHeader(
            title: user?.fullName ?? '—',
            subtitle: user?.email ?? '',
            leading: CircleAvatar(
              radius: 28,
              backgroundColor: Colors.white24,
              child: Text(
                user?.fullName.isNotEmpty == true ? user!.fullName[0].toUpperCase() : '?',
                style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold),
              ),
            ),
          ),
          Expanded(
            child: ListView(
              children: [
                const SizedBox(height: AppSpacing.xl),
                _section('Account', [
                  _tile(Icons.person_outline_rounded, 'Name', user?.fullName ?? '—'),
                  _tile(Icons.email_outlined, 'Email', user?.email ?? '—'),
                  _tile(Icons.badge_outlined, 'Role', user?.role ?? '—'),
                ]),
                const SizedBox(height: AppSpacing.xl),
                Padding(
                  padding: AppSpacing.screenPadding,
                  child: ListTile(
                    tileColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: AppRadius.cardBorder,
                      side: const BorderSide(color: AppColors.border),
                    ),
                    leading: const Icon(Icons.logout_rounded, color: AppColors.danger500),
                    title: const Text('Log out', style: TextStyle(color: AppColors.danger500, fontWeight: FontWeight.w600)),
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
      padding: AppSpacing.screenPadding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(left: 4, bottom: AppSpacing.sm),
            child: Text(title.toUpperCase(), style: AppTextStyles.sectionLabel),
          ),
          Material(
            color: Colors.white,
            borderRadius: AppRadius.cardBorder,
            clipBehavior: Clip.antiAlias,
            child: Container(
              decoration: BoxDecoration(
                borderRadius: AppRadius.cardBorder,
                border: Border.all(color: AppColors.border),
              ),
              child: Column(
                children: [
                  for (int i = 0; i < tiles.length; i++) ...[
                    tiles[i],
                    if (i < tiles.length - 1)
                      const Divider(height: 1, indent: 56, color: AppColors.divider),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _tile(IconData icon, String label, String value) {
    return ListTile(
      leading: Icon(icon, color: AppColors.primaryNavy, size: 20),
      title: Text(label, style: AppTextStyles.cardLabel),
      subtitle: Text(value, style: AppTextStyles.cardTitle),
    );
  }
}
