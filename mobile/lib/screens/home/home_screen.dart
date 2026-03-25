import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../services/maintenance_service.dart';
import '../../services/info_service.dart';
import '../../theme/app_colors.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override State<HomeScreen> createState() => _HomeScreenState();
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
      final issues = await maintenanceService.listIssues();
      final info = await infoService.listUnitInfo();
      if (mounted) setState(() {
        _issues = issues.where((i) => i.status == 'open' || i.status == 'in_progress').toList();
        _info = info.take(3).toList();
        _loading = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final firstName = (auth.user?.fullName.trim().split(' ').firstOrNull) ?? 'there';

    return Scaffold(
      backgroundColor: const Color(0xFFF5F6FA),
      body: RefreshIndicator(
        onRefresh: _load,
        child: CustomScrollView(
          slivers: [
            // Header
            SliverToBoxAdapter(
              child: Container(
                color: AppColors.primaryNavy,
                padding: EdgeInsets.fromLTRB(20, MediaQuery.of(context).padding.top + 20, 20, 24),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Hi, $firstName 👋', style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w700)),
                          const SizedBox(height: 4),
                          const Text('Welcome home', style: TextStyle(color: Colors.white60, fontSize: 14)),
                        ],
                      ),
                    ),
                    CircleAvatar(
                      radius: 20,
                      backgroundColor: Colors.white24,
                      child: Text(
                        firstName.isNotEmpty ? firstName[0].toUpperCase() : '?',
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
              ),
            ),

            if (_loading)
              const SliverToBoxAdapter(
                child: Padding(
                  padding: EdgeInsets.only(top: 80),
                  child: Center(child: CircularProgressIndicator()),
                ),
              )
            else ...[
              // Active repairs section
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(20, 24, 20, 12),
                  child: Row(
                    children: [
                      const Text('Active Repairs', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: Color(0xFF1A1A2E))),
                      const Spacer(),
                      if (_issues.isNotEmpty)
                        TextButton(
                          onPressed: () {}, // handled by bottom nav
                          child: const Text('See all', style: TextStyle(fontSize: 13)),
                        ),
                    ],
                  ),
                ),
              ),
              if (_issues.isEmpty)
                const SliverToBoxAdapter(
                  child: Padding(
                    padding: EdgeInsets.symmetric(horizontal: 20),
                    child: _EmptyCard(
                      icon: Icons.check_circle_outline_rounded,
                      text: 'No active repairs',
                      color: Color(0xFF34D399),
                    ),
                  ),
                )
              else
                SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (ctx, i) => Padding(
                      padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
                      child: _IssueCard(issue: _issues[i]),
                    ),
                    childCount: _issues.length.clamp(0, 3),
                  ),
                ),

              // Unit info section
              if (_info.isNotEmpty) ...[
                const SliverToBoxAdapter(
                  child: Padding(
                    padding: EdgeInsets.fromLTRB(20, 20, 20, 12),
                    child: Text('Property Info', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: Color(0xFF1A1A2E))),
                  ),
                ),
                SliverToBoxAdapter(
                  child: SizedBox(
                    height: 100,
                    child: ListView.builder(
                      scrollDirection: Axis.horizontal,
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      itemCount: _info.length,
                      itemBuilder: (ctx, i) => Padding(
                        padding: const EdgeInsets.only(right: 12),
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
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
        elevation: 4,
        label: const Text('AI', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, letterSpacing: 0.5)),
        icon: const Icon(Icons.auto_awesome_rounded, size: 20),
      ),
    );
  }
}

class _IssueCard extends StatelessWidget {
  const _IssueCard({required this.issue});
  final MaintenanceIssue issue;

  Color get _priorityColor {
    switch (issue.priority) {
      case 'urgent': return const Color(0xFFEF4444);
      case 'high': return const Color(0xFFF97316);
      case 'medium': return const Color(0xFF3B82F6);
      default: return const Color(0xFF6B7280);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Container(
              width: 4, height: 40,
              decoration: BoxDecoration(color: _priorityColor, borderRadius: BorderRadius.circular(2)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(issue.title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14, color: Color(0xFF1A1A2E))),
                  const SizedBox(height: 4),
                  Text(
                    issue.status.replaceAll('_', ' ').toUpperCase(),
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: _priorityColor),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: Color(0xFF9CA3AF), size: 20),
          ],
        ),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.item});
  final UnitInfoItem item;

  IconData get _icon {
    switch (item.iconType) {
      case 'wifi': return Icons.wifi_rounded;
      case 'alarm': return Icons.security_rounded;
      case 'garbage': return Icons.delete_outline_rounded;
      case 'parking': return Icons.local_parking_rounded;
      case 'electricity': return Icons.bolt_rounded;
      case 'water': return Icons.water_drop_outlined;
      default: return Icons.info_outline_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 140,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(_icon, color: AppColors.primaryNavy, size: 22),
          const SizedBox(height: 8),
          Text(item.label, style: const TextStyle(fontSize: 11, color: Color(0xFF6B7280), fontWeight: FontWeight.w500)),
          Text(item.value, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Color(0xFF1A1A2E)), maxLines: 1, overflow: TextOverflow.ellipsis),
        ],
      ),
    );
  }
}

class _EmptyCard extends StatelessWidget {
  const _EmptyCard({required this.icon, required this.text, required this.color});
  final IconData icon;
  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: color.withOpacity(0.08), borderRadius: BorderRadius.circular(14), border: Border.all(color: color.withOpacity(0.2))),
      child: Row(
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(width: 12),
          Text(text, style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 14)),
        ],
      ),
    );
  }
}
