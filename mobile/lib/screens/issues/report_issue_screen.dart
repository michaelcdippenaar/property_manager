import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../services/maintenance_service.dart';
import '../../theme/app_colors.dart';

class ReportIssueScreen extends StatefulWidget {
  const ReportIssueScreen({super.key});
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
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Repair request submitted ✓'), backgroundColor: Color(0xFF34D399)));
        context.pop();
      }
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _submitting = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F6FA),
      appBar: AppBar(
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
        title: const Text('Report a Repair'),
        leading: IconButton(icon: const Icon(Icons.close_rounded), onPressed: () => context.pop()),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            _field('What needs fixing?', _titleCtrl, hint: 'e.g. Tap leaking in bathroom'),
            const SizedBox(height: 16),
            _field('Describe the problem', _descCtrl, hint: 'More detail helps the team respond faster…', maxLines: 4),
            const SizedBox(height: 16),
            _label('Category'),
            const SizedBox(height: 6),
            _dropdown(_categories, _category, (v) => setState(() => _category = v!)),
            const SizedBox(height: 16),
            _label('Priority'),
            const SizedBox(height: 6),
            _dropdown(_priorities, _priority, (v) => setState(() => _priority = v!)),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(_error!, style: const TextStyle(color: Colors.red)),
            ],
            const SizedBox(height: 32),
            FilledButton(
              onPressed: _submitting ? null : _submit,
              style: FilledButton.styleFrom(backgroundColor: AppColors.accentPink, minimumSize: const Size.fromHeight(52)),
              child: _submitting ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : const Text('Submit Request', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
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
            hintStyle: const TextStyle(color: AppColors.textSecondary, fontSize: 14),
            filled: true, fillColor: Colors.white,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.inputBorder)),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.inputBorder)),
            focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.primaryNavy, width: 1.5)),
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          ),
          validator: (v) => v == null || v.trim().isEmpty ? 'Required' : null,
        ),
      ],
    );
  }

  Widget _label(String text) => Text(text, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.textSecondary));

  Widget _dropdown(List<String> items, String value, void Function(String?) onChanged) {
    return DropdownButtonFormField<String>(
      value: value,
      onChanged: onChanged,
      decoration: InputDecoration(
        filled: true, fillColor: Colors.white,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.inputBorder)),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppColors.inputBorder)),
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      ),
      items: items.map((s) => DropdownMenuItem(value: s, child: Text(s, style: const TextStyle(fontSize: 14)))).toList(),
    );
  }
}
