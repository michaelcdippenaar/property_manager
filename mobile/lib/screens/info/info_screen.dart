import 'package:flutter/material.dart';
import '../../services/info_service.dart';
import '../../theme/app_colors.dart';

class InfoScreen extends StatefulWidget {
  const InfoScreen({super.key});
  @override State<InfoScreen> createState() => _InfoScreenState();
}

class _InfoScreenState extends State<InfoScreen> {
  List<UnitInfoItem> _items = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final items = await infoService.listUnitInfo();
      if (mounted) setState(() { _items = items; _loading = false; });
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
          Container(
            color: AppColors.primaryNavy,
            padding: EdgeInsets.fromLTRB(20, MediaQuery.of(context).padding.top + 20, 20, 20),
            child: const Row(
              children: [
                Text('Property Info', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w700)),
              ],
            ),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _load,
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(child: Text(_error!, style: const TextStyle(color: AppColors.textSecondary)))
                      : _items.isEmpty
                          ? const Center(child: Text('No info available yet.', style: TextStyle(color: AppColors.textSecondary)))
                          : ListView.separated(
                              padding: const EdgeInsets.all(16),
                              itemCount: _items.length,
                              separatorBuilder: (_, __) => const SizedBox(height: 10),
                              itemBuilder: (ctx, i) => _InfoTile(item: _items[i]),
                            ),
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoTile extends StatelessWidget {
  const _InfoTile({required this.item});
  final UnitInfoItem item;

  IconData get _icon {
    switch (item.iconType) {
      case 'wifi': return Icons.wifi_rounded;
      case 'alarm': return Icons.security_rounded;
      case 'garbage': return Icons.delete_outline_rounded;
      case 'parking': return Icons.local_parking_rounded;
      case 'electricity': return Icons.bolt_rounded;
      case 'water': return Icons.water_drop_outlined;
      case 'rules': return Icons.gavel_rounded;
      default: return Icons.info_outline_rounded;
    }
  }

  Color get _color {
    switch (item.iconType) {
      case 'wifi': return const Color(0xFF3B82F6);
      case 'alarm': return const Color(0xFFEF4444);
      case 'electricity': return const Color(0xFFFBBF24);
      case 'water': return const Color(0xFF38BDF8);
      default: return AppColors.primaryNavy;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 44, height: 44,
              decoration: BoxDecoration(color: _color.withOpacity(0.1), borderRadius: BorderRadius.circular(12)),
              child: Icon(_icon, color: _color, size: 22),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(item.label, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary, fontWeight: FontWeight.w500)),
                  const SizedBox(height: 2),
                  Text(item.value, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: Color(0xFF1A1A2E))),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
