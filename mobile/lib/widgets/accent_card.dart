import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_radius.dart';
import '../theme/app_spacing.dart';

/// White card with 12px radius, gray-200 border, and optional left accent
/// border colored by priority (matching admin `border-l-4` pattern).
class AccentCard extends StatelessWidget {
  const AccentCard({
    super.key,
    this.accentColor,
    this.onTap,
    required this.child,
  });

  /// Left border accent color. Pass `AppColors.priorityColor(priority)`.
  final Color? accentColor;
  final VoidCallback? onTap;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.cardBackground,
      borderRadius: BorderRadius.circular(AppRadius.card),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.card),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(color: AppColors.border),
          ),
          child: Row(
            children: [
              if (accentColor != null)
                Container(
                  width: 4,
                  constraints: const BoxConstraints(minHeight: 72),
                  decoration: BoxDecoration(
                    color: accentColor,
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(AppRadius.card),
                      bottomLeft: Radius.circular(AppRadius.card),
                    ),
                  ),
                ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  child: child,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
