import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../services/maintenance_service.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_radius.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/state_views.dart';
import '../../widgets/status_badge.dart';

class IssueDetailScreen extends StatefulWidget {
  const IssueDetailScreen({super.key, required this.issueId});
  final int issueId;
  @override
  State<IssueDetailScreen> createState() => _IssueDetailScreenState();
}

class _IssueDetailScreenState extends State<IssueDetailScreen> {
  MaintenanceIssue? _issue;
  bool _loading = true;
  String? _error;

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
      final issue = await maintenanceService.getIssue(widget.issueId);
      if (mounted) setState(() { _issue = issue; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffoldBackground,
      appBar: AppBar(
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
        title: Text(_issue?.ticketRef.isNotEmpty == true
            ? _issue!.ticketRef
            : 'Repair Request'),
        leading: IconButton(
            icon: const Icon(Icons.arrow_back_rounded),
            onPressed: () => context.pop()),
      ),
      body: _loading
          ? const LoadingView()
          : _error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : _buildBody(),
    );
  }

  Widget _buildBody() {
    final issue = _issue!;

    return ListView(
      padding: AppSpacing.listPadding,
      children: [
        // Status + Priority badges
        Row(
          children: [
            StatusBadge.status(issue.status),
            const SizedBox(width: AppSpacing.sm),
            StatusBadge.priority(issue.priority),
          ],
        ),
        const SizedBox(height: AppSpacing.xl),

        // Title
        Text(issue.title,
            style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary)),
        const SizedBox(height: AppSpacing.xl),

        // Metadata card
        Container(
          padding: const EdgeInsets.all(AppSpacing.lg),
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(color: AppColors.border),
          ),
          child: Column(
            children: [
              _DetailRow(label: 'Category', value: issue.category),
              _DetailRow(label: 'Priority', value: issue.priority),
              if (issue.ticketRef.isNotEmpty)
                _DetailRow(label: 'Reference', value: issue.ticketRef),
              _DetailRow(
                label: 'Logged',
                value: issue.createdAt.isNotEmpty
                    ? issue.createdAt.substring(0, 10)
                    : '—',
                showDivider: false,
              ),
            ],
          ),
        ),

        // Description card
        if (issue.description.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.lg),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(AppSpacing.lg),
            decoration: BoxDecoration(
              color: AppColors.cardBackground,
              borderRadius: BorderRadius.circular(AppRadius.card),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Description',
                    style: AppTextStyles.cardLabel
                        .copyWith(fontWeight: FontWeight.w600)),
                const SizedBox(height: AppSpacing.sm),
                Text(issue.description, style: AppTextStyles.body),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.label,
    required this.value,
    this.showDivider = true,
  });
  final String label;
  final String value;
  final bool showDivider;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
          child: Row(
            children: [
              SizedBox(
                  width: 90,
                  child: Text(label, style: AppTextStyles.cardLabel)),
              Expanded(child: Text(value, style: AppTextStyles.cardValue)),
            ],
          ),
        ),
        if (showDivider) const Divider(height: 1, color: AppColors.divider),
      ],
    );
  }
}
