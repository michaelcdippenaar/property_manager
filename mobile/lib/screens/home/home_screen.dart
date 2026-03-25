import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../services/maintenance_service.dart';
import '../../services/info_service.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_radius.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import '../../utils/icon_mapper.dart';
import '../../widgets/accent_card.dart';
import '../../widgets/app_header.dart';
import '../../widgets/state_views.dart';
import '../../widgets/status_badge.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<MaintenanceIssue> _issues = [];
  List<UnitInfoItem> _info = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final issues = await maintenanceService.listIssues(
          params: {'status': 'open,in_progress'});
      final info = await infoService.listUnitInfo();
      if (mounted) {
        setState(() {
          _issues = issues;
          _info = info.take(3).toList();
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final firstName =
        (auth.user?.fullName.trim().split(' ').firstOrNull) ?? 'there';

    return Scaffold(
      backgroundColor: AppColors.scaffoldBackground,
      body: RefreshIndicator(
        onRefresh: _load,
        child: CustomScrollView(
          slivers: [
            SliverToBoxAdapter(
              child: AppHeader(
                title: 'Hi, $firstName 👋',
                subtitle: 'Welcome home',
                trailing: CircleAvatar(
                  radius: 20,
                  backgroundColor: Colors.white24,
                  child: Text(
                    firstName.isNotEmpty ? firstName[0].toUpperCase() : '?',
                    style: const TextStyle(
                        color: Colors.white, fontWeight: FontWeight.bold),
                  ),
                ),
              ),
            ),
            if (_loading)
              const SliverToBoxAdapter(child: LoadingView())
            else ...[
              // Active repairs section
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(AppSpacing.screenH,
                      AppSpacing.xxl, AppSpacing.screenH, AppSpacing.sectionGap),
                  child: Row(
                    children: [
                      const Text('Active Repairs',
                          style: AppTextStyles.sectionTitle),
                      const Spacer(),
                      if (_issues.isNotEmpty)
                        TextButton(
                          onPressed: () {
                            // Navigate to Repairs tab (index 1 in shell)
                            final shell = context
                                .findAncestorStateOfType<State>();
                            if (shell != null) {
                              context.go('/issues');
                            }
                          },
                          child: const Text('See all',
                              style: TextStyle(fontSize: 13)),
                        ),
                    ],
                  ),
                ),
              ),
              if (_issues.isEmpty)
                const SliverToBoxAdapter(
                  child: Padding(
                    padding: AppSpacing.screenPadding,
                    child: _EmptyCard(
                      icon: Icons.check_circle_outline_rounded,
                      text: 'No active repairs',
                      color: AppColors.success500,
                    ),
                  ),
                )
              else
                SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (ctx, i) => Padding(
                      padding: const EdgeInsets.fromLTRB(AppSpacing.screenH, 0,
                          AppSpacing.screenH, AppSpacing.listGap),
                      child: _IssueCard(issue: _issues[i]),
                    ),
                    childCount: _issues.length.clamp(0, 3),
                  ),
                ),

              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(
                    AppSpacing.screenH,
                    AppSpacing.md,
                    AppSpacing.screenH,
                    0,
                  ),
                  child: AccentCard(
                    accentColor: AppColors.info500,
                    onTap: () => context.push('/signing'),
                    child: Row(
                      children: [
                        const Icon(Icons.draw_rounded,
                            color: AppColors.primaryNavy, size: 22),
                        const SizedBox(width: AppSpacing.md),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Lease signing',
                                  style: AppTextStyles.cardTitle),
                              const SizedBox(height: 2),
                              const Text(
                                'Review and sign your lease in the app',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const Icon(Icons.chevron_right,
                            color: AppColors.textSecondary, size: 20),
                      ],
                    ),
                  ),
                ),
              ),

              // Unit info section
              if (_info.isNotEmpty) ...[
                const SliverToBoxAdapter(
                  child: Padding(
                    padding: EdgeInsets.fromLTRB(AppSpacing.screenH,
                        AppSpacing.xl, AppSpacing.screenH, AppSpacing.sectionGap),
                    child:
                        Text('Property Info', style: AppTextStyles.sectionTitle),
                  ),
                ),
                SliverToBoxAdapter(
                  child: SizedBox(
                    height: 100,
                    child: ListView.builder(
                      scrollDirection: Axis.horizontal,
                      padding: AppSpacing.screenPadding,
                      itemCount: _info.length,
                      itemBuilder: (ctx, i) => Padding(
                        padding: const EdgeInsets.only(right: AppSpacing.md),
                        child: _InfoCard(item: _info[i]),
                      ),
                    ),
                  ),
                ),
              ],

              const SliverToBoxAdapter(child: SizedBox(height: 100)),
            ],
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/chat'),
        backgroundColor: AppColors.accentPink,
        foregroundColor: Colors.white,
        elevation: 4,
        label: const Text('AI',
            style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.5)),
        icon: const Icon(Icons.auto_awesome_rounded, size: 20),
      ),
    );
  }
}

class _IssueCard extends StatelessWidget {
  const _IssueCard({required this.issue});
  final MaintenanceIssue issue;

  @override
  Widget build(BuildContext context) {
    return AccentCard(
      accentColor: AppColors.priorityColor(issue.priority),
      onTap: () => context.push('/issues/${issue.id}'),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(issue.title, style: AppTextStyles.cardTitle),
                const SizedBox(height: AppSpacing.xs),
                Row(
                  children: [
                    StatusBadge.status(issue.status),
                    const SizedBox(width: AppSpacing.sm),
                    StatusBadge.priority(issue.priority),
                  ],
                ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right,
              color: AppColors.textSecondary, size: 20),
        ],
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.item});
  final UnitInfoItem item;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 140,
      padding: AppSpacing.cardPadding,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(IconMapper.fromType(item.iconType),
              color: AppColors.primaryNavy, size: 22),
          const SizedBox(height: AppSpacing.sm),
          Text(item.label, style: AppTextStyles.cardLabel),
          Text(item.value,
              style: AppTextStyles.cardValue,
              maxLines: 1,
              overflow: TextOverflow.ellipsis),
        ],
      ),
    );
  }
}

class _EmptyCard extends StatelessWidget {
  const _EmptyCard(
      {required this.icon, required this.text, required this.color});
  final IconData icon;
  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: AppSpacing.cardPadding,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(width: AppSpacing.md),
          Text(text,
              style: TextStyle(
                  color: color, fontWeight: FontWeight.w600, fontSize: 14)),
        ],
      ),
    );
  }
}
