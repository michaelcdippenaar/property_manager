import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../services/maintenance_service.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/accent_card.dart';
import '../../widgets/app_header.dart';
import '../../widgets/filter_pills.dart';
import '../../widgets/state_views.dart';
import '../../widgets/status_badge.dart';

class IssuesScreen extends StatefulWidget {
  const IssuesScreen({super.key});
  @override
  State<IssuesScreen> createState() => _IssuesScreenState();
}

class _IssuesScreenState extends State<IssuesScreen> {
  List<MaintenanceIssue> _issues = [];
  bool _loading = true;
  String? _error;
  String _filter = 'all';

  static const _filterOptions = [
    FilterOption(label: 'All', value: 'all'),
    FilterOption(label: 'Open', value: 'open'),
    FilterOption(label: 'In Progress', value: 'in_progress'),
    FilterOption(label: 'Resolved', value: 'resolved'),
    FilterOption(label: 'Closed', value: 'closed'),
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final params = _filter == 'all' ? null : {'status': _filter};
      final list = await maintenanceService.listIssues(params: params);
      if (mounted) setState(() { _issues = list; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _loading = false; });
    }
  }

  void _onFilterChanged(String value) {
    setState(() => _filter = value);
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffoldBackground,
      body: Column(
        children: [
          const AppHeader(title: 'My Repairs'),
          const SizedBox(height: AppSpacing.md),
          FilterPills(
            options: _filterOptions,
            selectedValue: _filter,
            onChanged: _onFilterChanged,
          ),
          const SizedBox(height: AppSpacing.sm),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _load,
              child: _buildBody(),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.push('/issues/report'),
        backgroundColor: AppColors.accentPink,
        child: const Icon(Icons.add_rounded, color: Colors.white),
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) return const LoadingView();
    if (_error != null) return ErrorView(message: _error!, onRetry: _load);
    if (_issues.isEmpty) {
      return const EmptyView(
        icon: Icons.check_circle_outline_rounded,
        title: 'No repairs logged',
        subtitle: 'Tap + to report a new issue',
        iconColor: AppColors.success500,
      );
    }
    return ListView.separated(
      padding: AppSpacing.listPadding,
      itemCount: _issues.length,
      separatorBuilder: (_, __) =>
          const SizedBox(height: AppSpacing.listGap),
      itemBuilder: (ctx, i) => _IssueListTile(issue: _issues[i]),
    );
  }
}

class _IssueListTile extends StatelessWidget {
  const _IssueListTile({required this.issue});
  final MaintenanceIssue issue;

  @override
  Widget build(BuildContext context) {
    return AccentCard(
      accentColor: AppColors.priorityColor(issue.priority),
      onTap: () => context.push('/issues/${issue.id}'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(issue.title, style: AppTextStyles.cardTitle),
              ),
              const Icon(Icons.chevron_right,
                  color: AppColors.textSecondary, size: 20),
            ],
          ),
          if (issue.description.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.xs),
            Text(
              issue.description,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AppTextStyles.cardSubtitle,
            ),
          ],
          const SizedBox(height: AppSpacing.sm),
          Row(
            children: [
              StatusBadge.status(issue.status),
              const SizedBox(width: AppSpacing.sm),
              StatusBadge.priority(issue.priority),
              const Spacer(),
              if (issue.createdAt.isNotEmpty)
                Text(
                  issue.createdAt.substring(0, 10),
                  style: AppTextStyles.cardLabel,
                ),
            ],
          ),
        ],
      ),
    );
  }
}
