import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../services/maintenance_service.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_radius.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';

class ReportIssueScreen extends StatefulWidget {
  const ReportIssueScreen({super.key, this.initialDraft});
  final Map<String, dynamic>? initialDraft;
  @override State<ReportIssueScreen> createState() => _ReportIssueScreenState();
}

class _ReportIssueScreenState extends State<ReportIssueScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  String _category = 'other';
  String _priority = 'medium';
  bool _submitting = false;
  String? _error;

  static const _categories = ['plumbing', 'electrical', 'roof', 'appliance', 'security', 'pest', 'garden', 'other'];
  static const _priorities = ['low', 'medium', 'high', 'urgent'];

  @override
  void initState() {
    super.initState();
    final d = widget.initialDraft;
    if (d != null) {
      final t = d['title'];
      if (t is String && t.trim().isNotEmpty) _titleCtrl.text = t.trim();
      final desc = d['description'];
      if (desc is String && desc.trim().isNotEmpty) _descCtrl.text = desc.trim();
      final p = d['priority'];
      if (p is String && _priorities.contains(p)) _priority = p;
      final c = d['category'];
      if (c is String && _categories.contains(c)) _category = c;
    }
  }

  @override
  void dispose() { _titleCtrl.dispose(); _descCtrl.dispose(); super.dispose(); }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _submitting = true; _error = null; });
    try {
      await maintenanceService.createIssue(
        title: _titleCtrl.text.trim(),
        description: _descCtrl.text.trim(),
        category: _category,
        priority: _priority,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Repair request submitted ✓'), backgroundColor: AppColors.success500));
        context.pop();
      }
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _submitting = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffoldBackground,
      appBar: AppBar(
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
        title: const Text('Report a Repair'),
        leading: IconButton(icon: const Icon(Icons.close_rounded), onPressed: () => context.pop()),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: AppSpacing.listPadding,
          children: [
            _field('What needs fixing?', _titleCtrl, hint: 'e.g. Tap leaking in bathroom'),
            const SizedBox(height: AppSpacing.lg),
            _field('Describe the problem', _descCtrl, hint: 'More detail helps the team respond faster…', maxLines: 4),
            const SizedBox(height: AppSpacing.lg),
            _label('Category'),
            const SizedBox(height: 6),
            _dropdown(_categories, _category, (v) => setState(() => _category = v!)),
            const SizedBox(height: AppSpacing.lg),
            _label('Priority'),
            const SizedBox(height: 6),
            _dropdown(_priorities, _priority, (v) => setState(() => _priority = v!)),
            if (_error != null) ...[
              const SizedBox(height: AppSpacing.lg),
              Text(_error!, style: const TextStyle(color: AppColors.danger500)),
            ],
            const SizedBox(height: AppSpacing.xxxl),
            FilledButton(
              onPressed: _submitting ? null : _submit,
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.accentPink,
                minimumSize: const Size.fromHeight(52),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.pill)),
              ),
              child: _submitting
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : const Text('Submit Request', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _field(String label, TextEditingController ctrl, {String? hint, int maxLines = 1}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _label(label),
        const SizedBox(height: 6),
        TextFormField(
          controller: ctrl,
          maxLines: maxLines,
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: AppTextStyles.bodySecondary,
            filled: true, fillColor: Colors.white,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(AppRadius.medium), borderSide: const BorderSide(color: AppColors.inputBorder)),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(AppRadius.medium), borderSide: const BorderSide(color: AppColors.inputBorder)),
            focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(AppRadius.medium), borderSide: const BorderSide(color: AppColors.primaryNavy, width: 1.5)),
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          ),
          validator: (v) => v == null || v.trim().isEmpty ? 'Required' : null,
        ),
      ],
    );
  }

  Widget _label(String text) => Text(text, style: AppTextStyles.cardLabel.copyWith(fontWeight: FontWeight.w600));

  Widget _dropdown(List<String> items, String value, void Function(String?) onChanged) {
    return DropdownButtonFormField<String>(
      initialValue: value,
      onChanged: onChanged,
      decoration: InputDecoration(
        filled: true, fillColor: Colors.white,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(AppRadius.medium), borderSide: const BorderSide(color: AppColors.inputBorder)),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(AppRadius.medium), borderSide: const BorderSide(color: AppColors.inputBorder)),
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      ),
      items: items.map((s) => DropdownMenuItem(
        value: s,
        child: Row(
          children: [
            if (items == _priorities)
              Container(
                width: 8, height: 8,
                margin: const EdgeInsets.only(right: 8),
                decoration: BoxDecoration(
                  color: AppColors.priorityColor(s),
                  shape: BoxShape.circle,
                ),
              ),
            Text(s, style: AppTextStyles.body),
          ],
        ),
      )).toList(),
    );
  }
}
