import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../providers/auth_provider.dart';
import '../../theme/app_colors.dart';

/// Tenant home after sign-in: quick actions and clear structure (not an empty placeholder).
class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final name = auth.user?.fullName.trim();
    final greeting = (name != null && name.isNotEmpty) ? name.split(' ').first : 'there';

    return Scaffold(
      backgroundColor: AppColors.splashBackground,
      appBar: AppBar(
        title: const Text('Klikk'),
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
        actions: [
          TextButton(
            onPressed: () async {
              await context.read<AuthProvider>().logout();
              if (context.mounted) context.go('/login');
            },
            child: const Text('Log out', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Hi, $greeting',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          Text(
            auth.user?.role == 'tenant'
                ? 'Report maintenance, track requests, and stay in touch with your property team.'
                : 'Signed in as ${auth.user?.role ?? "user"}. This app is optimised for tenants.',
            style: const TextStyle(fontSize: 14, color: AppColors.textSecondary, height: 1.35),
          ),
          const SizedBox(height: 28),
          _ActionCard(
            icon: Icons.build_circle_outlined,
            title: 'Report an issue',
            subtitle: 'Tell us what needs attention at your unit.',
            accent: AppColors.accentPink,
            onTap: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Report flow coming soon — use the web tenant portal for now.'),
                ),
              );
            },
          ),
          const SizedBox(height: 14),
          _ActionCard(
            icon: Icons.list_alt_rounded,
            title: 'My maintenance issues',
            subtitle: 'View status of requests you have logged.',
            accent: AppColors.primaryNavy,
            onTap: () => context.push('/issues'),
          ),
          const SizedBox(height: 14),
          _ActionCard(
            icon: Icons.info_outline_rounded,
            title: 'Property info',
            subtitle: 'House rules and contacts will appear here.',
            accent: AppColors.primaryNavy,
            onTap: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Property info — coming soon.')),
              );
            },
          ),
          const SizedBox(height: 32),
          const Text(
            'Tip: ensure the Django API is running (e.g. localhost:8000) so issues can load.',
            style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  const _ActionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.accent,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Color accent;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      elevation: 0,
      shadowColor: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.splashBackground,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: accent, size: 26),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      subtitle,
                      style: const TextStyle(fontSize: 14, color: AppColors.textSecondary, height: 1.3),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: AppColors.textSecondary),
            ],
          ),
        ),
      ),
    );
  }
}
