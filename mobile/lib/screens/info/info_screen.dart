import 'package:flutter/material.dart';
import '../../services/info_service.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_radius.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import '../../utils/icon_mapper.dart';
import '../../widgets/app_header.dart';
import '../../widgets/state_views.dart';

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
      backgroundColor: AppColors.scaffoldBackground,
      body: Column(
        children: [
          const AppHeader(title: 'Property Info'),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _load,
              child: _loading
                  ? const LoadingView()
                  : _error != null
                      ? ErrorView(message: _error!, onRetry: _load)
                      : _items.isEmpty
                          ? const EmptyView(
                              icon: Icons.info_outline_rounded,
                              title: 'No info available yet',
                            )
                          : ListView.separated(
                              padding: AppSpacing.listPadding,
                              itemCount: _items.length,
                              separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.listGap),
                              itemBuilder: (ctx, i) => _InfoTile(item: _items[i]),
                            ),
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoTile extends StatefulWidget {
  const _InfoTile({required this.item});
  final UnitInfoItem item;
  @override
  State<_InfoTile> createState() => _InfoTileState();
}

class _InfoTileState extends State<_InfoTile> {
  bool _revealed = false;

  UnitInfoItem get item => widget.item;

  Color _iconColor(String iconType) {
    switch (iconType) {
      case 'wifi': return AppColors.info500;
      case 'alarm': return AppColors.danger500;
      case 'electricity': return AppColors.warning500;
      case 'water': return AppColors.info500;
      default: return AppColors.primaryNavy;
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _iconColor(item.iconType);
    final sensitive = IconMapper.isSensitive(item.iconType);
    final displayValue = sensitive && !_revealed ? '\u2022' * 8 : item.value;
    return Material(
      color: Colors.white,
      borderRadius: AppRadius.cardBorder,
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        borderRadius: AppRadius.cardBorder,
        onTap: sensitive ? () => setState(() => _revealed = !_revealed) : null,
        child: Container(
          padding: AppSpacing.cardPadding,
          decoration: BoxDecoration(
            borderRadius: AppRadius.cardBorder,
            border: Border.all(color: AppColors.border),
          ),
          child: Row(
            children: [
              Container(
                width: 44, height: 44,
                decoration: BoxDecoration(color: color.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(AppRadius.medium)),
                child: Icon(IconMapper.fromType(item.iconType), color: color, size: 22),
              ),
              const SizedBox(width: AppSpacing.lg),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(item.label, style: AppTextStyles.cardLabel),
                    const SizedBox(height: 2),
                    Text(displayValue, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
                  ],
                ),
              ),
              if (sensitive)
                Icon(
                  _revealed ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                  color: AppColors.textSecondary,
                  size: 20,
                ),
            ],
          ),
        ),
      ),
    );
  }
}
