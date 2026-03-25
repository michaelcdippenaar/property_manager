import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../services/maintenance_service.dart';
import '../../theme/app_colors.dart';

class IssuesScreen extends StatefulWidget {
  const IssuesScreen({super.key});
  @override State<IssuesScreen> createState() => _IssuesScreenState();
}

class _IssuesScreenState extends State<IssuesScreen> {
  List<MaintenanceIssue> _issues = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final list = await maintenanceService.listIssues();
      if (mounted) setState(() { _issues = list; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F6FA),
      body: Column(
        children: [
          // Header
          Container(
            color: AppColors.primaryNavy,
            padding: EdgeInsets.fromLTRB(20, MediaQuery.of(context).padding.top + 20, 20, 20),
            child: const Row(
              children: [
                Text('My Repairs', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w700)),
              ],
            ),
          ),
          // Body
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
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return _errorView();
    if (_issues.isEmpty) return _emptyView();
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: _issues.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (ctx, i) => _IssueListTile(issue: _issues[i]),
    );
  }

  Widget _errorView() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_outlined, size: 48, color: AppColors.textSecondary),
            const SizedBox(height: 16),
            Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.textSecondary)),
            const SizedBox(height: 20),
            FilledButton(onPressed: _load, style: FilledButton.styleFrom(backgroundColor: AppColors.primaryNavy), child: const Text('Retry')),
          ],
        ),
      ),
    );
  }

  Widget _emptyView() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.check_circle_outline_rounded, size: 56, color: Color(0xFF34D399)),
          const SizedBox(height: 16),
          const Text('No repairs logged', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          const Text('Tap + to report a new issue', style: TextStyle(color: AppColors.textSecondary)),
        ],
      ),
    );
  }
}

class _IssueListTile extends StatelessWidget {
  const _IssueListTile({required this.issue});
  final MaintenanceIssue issue;

  Color get _statusColor {
    switch (issue.status) {
      case 'open': return const Color(0xFF3B82F6);
      case 'in_progress': return const Color(0xFFF97316);
      case 'resolved': return const Color(0xFF34D399);
      case 'closed': return const Color(0xFF9CA3AF);
      default: return const Color(0xFF6B7280);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => context.push('/issues/${issue.id}'),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                width: 42, height: 42,
                decoration: BoxDecoration(color: _statusColor.withOpacity(0.12), borderRadius: BorderRadius.circular(10)),
                child: Icon(Icons.build_rounded, color: _statusColor, size: 20),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(issue.title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15, color: Color(0xFF1A1A2E))),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(color: _statusColor.withOpacity(0.12), borderRadius: BorderRadius.circular(6)),
                          child: Text(issue.status.replaceAll('_', ' '), style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: _statusColor)),
                        ),
                        const SizedBox(width: 8),
                        if (issue.ticketRef.isNotEmpty)
                          Text(issue.ticketRef, style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
                      ],
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: AppColors.textSecondary, size: 20),
            ],
          ),
        ),
      ),
    );
  }
}
