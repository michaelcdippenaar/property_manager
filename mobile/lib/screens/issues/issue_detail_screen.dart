import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../services/maintenance_service.dart';
import '../../theme/app_colors.dart';

class IssueDetailScreen extends StatefulWidget {
  const IssueDetailScreen({super.key, required this.issueId});
  final int issueId;
  @override State<IssueDetailScreen> createState() => _IssueDetailScreenState();
}

class _IssueDetailScreenState extends State<IssueDetailScreen> {
  MaintenanceIssue? _issue;
  bool _loading = true;
  String? _error;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
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
      backgroundColor: const Color(0xFFF5F6FA),
      appBar: AppBar(
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
        title: Text(_issue?.ticketRef.isNotEmpty == true ? _issue!.ticketRef : 'Repair Request'),
        leading: IconButton(icon: const Icon(Icons.arrow_back_rounded), onPressed: () => context.pop()),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!, style: const TextStyle(color: AppColors.textSecondary)))
              : _buildBody(),
    );
  }

  Widget _buildBody() {
    final issue = _issue!;
    final statusColor = _statusColor(issue.status);

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        // Status banner
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(color: statusColor.withOpacity(0.1), borderRadius: BorderRadius.circular(12), border: Border.all(color: statusColor.withOpacity(0.25))),
          child: Row(
            children: [
              Icon(Icons.circle, color: statusColor, size: 10),
              const SizedBox(width: 10),
              Text(issue.status.replaceAll('_', ' ').toUpperCase(), style: TextStyle(color: statusColor, fontWeight: FontWeight.w700, fontSize: 13, letterSpacing: 0.5)),
            ],
          ),
        ),
        const SizedBox(height: 20),
        Text(issue.title, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: Color(0xFF1A1A2E))),
        const SizedBox(height: 16),
        _DetailRow(label: 'Category', value: issue.category),
        _DetailRow(label: 'Priority', value: issue.priority),
        if (issue.ticketRef.isNotEmpty) _DetailRow(label: 'Reference', value: issue.ticketRef),
        _DetailRow(label: 'Logged', value: issue.createdAt.isNotEmpty ? issue.createdAt.substring(0, 10) : '—'),
        if (issue.description.isNotEmpty) ...[
          const SizedBox(height: 20),
          const Text('Description', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.textSecondary)),
          const SizedBox(height: 8),
          Text(issue.description, style: const TextStyle(fontSize: 15, color: Color(0xFF1A1A2E), height: 1.5)),
        ],
      ],
    );
  }

  Color _statusColor(String s) {
    switch (s) {
      case 'open': return const Color(0xFF3B82F6);
      case 'in_progress': return const Color(0xFFF97316);
      case 'resolved': return const Color(0xFF34D399);
      default: return const Color(0xFF9CA3AF);
    }
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          SizedBox(width: 90, child: Text(label, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary, fontWeight: FontWeight.w500))),
          Expanded(child: Text(value, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Color(0xFF1A1A2E)))),
        ],
      ),
    );
  }
}
