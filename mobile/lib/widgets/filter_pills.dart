import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_radius.dart';
import '../theme/app_spacing.dart';

/// A single filter option for [FilterPills].
class FilterOption {
  const FilterOption({required this.label, required this.value});
  final String label;
  final String value;
}

/// Horizontal scrollable pill row matching admin FilterPills component.
///
/// Inactive: white bg, gray-200 border, gray-600 text, pill shape.
/// Active: navy bg, white text.
class FilterPills extends StatelessWidget {
  const FilterPills({
    super.key,
    required this.options,
    required this.selectedValue,
    required this.onChanged,
  });

  final List<FilterOption> options;
  final String selectedValue;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 36,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.screenH),
        itemCount: options.length,
        separatorBuilder: (_, __) => const SizedBox(width: AppSpacing.sm),
        itemBuilder: (context, index) {
          final option = options[index];
          final isActive = option.value == selectedValue;
          return GestureDetector(
            onTap: () => onChanged(option.value),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
              decoration: BoxDecoration(
                color: isActive ? AppColors.primaryNavy : AppColors.cardBackground,
                borderRadius: BorderRadius.circular(AppRadius.pill),
                border: Border.all(
                  color: isActive ? AppColors.primaryNavy : AppColors.gray200,
                ),
              ),
              child: Text(
                option.label,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  color: isActive ? Colors.white : AppColors.gray600,
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
