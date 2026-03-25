import 'package:flutter/material.dart';
import 'app_colors.dart';

/// Centralised text styles to eliminate inline TextStyle duplication.
class AppTextStyles {
  AppTextStyles._();

  // --- Screen headers (white on navy) ---
  static const TextStyle headerTitle = TextStyle(
    color: Colors.white,
    fontSize: 20,
    fontWeight: FontWeight.w700,
  );

  static const TextStyle headerSubtitle = TextStyle(
    color: Colors.white60,
    fontSize: 14,
  );

  // --- Section titles ---
  static const TextStyle sectionTitle = TextStyle(
    fontSize: 16,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
  );

  static const TextStyle sectionLabel = TextStyle(
    fontSize: 11,
    fontWeight: FontWeight.w700,
    color: AppColors.textSecondary,
    letterSpacing: 1,
  );

  // --- Card / list tile ---
  static const TextStyle cardTitle = TextStyle(
    fontWeight: FontWeight.w600,
    fontSize: 15,
    color: AppColors.textPrimary,
  );

  static const TextStyle cardSubtitle = TextStyle(
    fontSize: 13,
    color: AppColors.textSecondary,
  );

  static const TextStyle cardLabel = TextStyle(
    fontSize: 12,
    color: AppColors.textSecondary,
    fontWeight: FontWeight.w500,
  );

  static const TextStyle cardValue = TextStyle(
    fontSize: 14,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
  );

  // --- Badges ---
  static const TextStyle badgeText = TextStyle(
    fontSize: 11,
    fontWeight: FontWeight.w600,
  );

  // --- Body ---
  static const TextStyle body = TextStyle(
    fontSize: 14,
    color: AppColors.textPrimary,
    height: 1.45,
  );

  static const TextStyle bodySecondary = TextStyle(
    fontSize: 14,
    color: AppColors.textSecondary,
  );

  // --- Empty / error states ---
  static const TextStyle emptyTitle = TextStyle(
    fontSize: 17,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
  );

  static const TextStyle emptySubtitle = TextStyle(
    fontSize: 14,
    color: AppColors.textSecondary,
  );
}
