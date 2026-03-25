import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_radius.dart';
import '../theme/app_text_styles.dart';

/// Unified coloured badge for status / priority labels.
///
/// Uses the admin 50/700 color pattern: light tinted background with dark text.
class StatusBadge extends StatelessWidget {
  const StatusBadge({
    super.key,
    required this.label,
    required this.backgroundColor,
    required this.textColor,
  });

  /// Badge for a maintenance issue status (open, in_progress, resolved, closed).
  factory StatusBadge.status(String status) {
    return StatusBadge(
      label: status.replaceAll('_', ' '),
      backgroundColor: AppColors.statusBadgeBg(status),
      textColor: AppColors.statusBadgeText(status),
    );
  }

  /// Badge for a maintenance issue priority (urgent, high, medium, low).
  factory StatusBadge.priority(String priority) {
    return StatusBadge(
      label: priority,
      backgroundColor: AppColors.priorityBadgeBg(priority),
      textColor: AppColors.priorityBadgeText(priority),
    );
  }

  final String label;
  final Color backgroundColor;
  final Color textColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(AppRadius.pill),
      ),
      child: Text(
        label,
        style: AppTextStyles.badgeText.copyWith(
          color: textColor,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }
}
