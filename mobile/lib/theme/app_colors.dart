import 'package:flutter/material.dart';

class AppColors {
  AppColors._();

  // ── Brand ──
  static const Color primaryNavy = Color(0xFF2B2D6E);
  static const Color navyDark = Color(0xFF23255A);
  static const Color navyLight = Color(0xFF3B3E8F);
  static const Color accentPink = Color(0xFFFF3D7F);
  static const Color accentPinkLight = Color(0xFFFF6B9D);

  // ── Surfaces ──
  static const Color splashBackground = Color(0xFFF0EFF8);
  static const Color scaffoldBackground = Color(0xFFF5F5F8);
  static const Color cardBackground = Colors.white;

  // ── Text ──
  static const Color textPrimary = Color(0xFF111111);
  static const Color textSecondary = Color(0xFF6B7280);
  static const Color textTertiary = Color(0xFF9CA3AF);
  static const Color textOnPrimary = Colors.white;

  // ── Borders & Dividers ──
  static const Color inputBorder = Color(0xFFD1D5DB);
  static const Color inputBorderActive = Color(0xFF2B2D6E);
  static const Color border = Color(0xFFE5E7EB);
  static const Color divider = Color(0xFFE5E7EB);

  // ── Semantic: Success ──
  static const Color success50 = Color(0xFFECFDF5);
  static const Color success100 = Color(0xFFD1FAE5);
  static const Color success500 = Color(0xFF10B981);
  static const Color success600 = Color(0xFF059669);
  static const Color success700 = Color(0xFF047857);

  // ── Semantic: Warning ──
  static const Color warning50 = Color(0xFFFFFBEB);
  static const Color warning100 = Color(0xFFFEF3C7);
  static const Color warning500 = Color(0xFFF59E0B);
  static const Color warning600 = Color(0xFFD97706);
  static const Color warning700 = Color(0xFFB45309);

  // ── Semantic: Danger ──
  static const Color danger50 = Color(0xFFFEF2F2);
  static const Color danger100 = Color(0xFFFEE2E2);
  static const Color danger500 = Color(0xFFEF4444);
  static const Color danger600 = Color(0xFFDC2626);
  static const Color danger700 = Color(0xFFB91C1C);

  // ── Semantic: Info ──
  static const Color info50 = Color(0xFFEFF6FF);
  static const Color info100 = Color(0xFFDBEAFE);
  static const Color info500 = Color(0xFF3B82F6);
  static const Color info600 = Color(0xFF2563EB);
  static const Color info700 = Color(0xFF1D4ED8);

  // ── Gray Scale ──
  static const Color gray50 = Color(0xFFF9FAFB);
  static const Color gray100 = Color(0xFFF3F4F6);
  static const Color gray200 = Color(0xFFE5E7EB);
  static const Color gray300 = Color(0xFFD1D5DB);
  static const Color gray400 = Color(0xFF9CA3AF);
  static const Color gray500 = Color(0xFF6B7280);
  static const Color gray600 = Color(0xFF4B5563);
  static const Color gray700 = Color(0xFF374151);

  // ── Status colors (aligned with admin badge pattern) ──
  static Color statusColor(String status) {
    switch (status) {
      case 'open':
        return danger500;
      case 'in_progress':
        return warning600;
      case 'resolved':
        return success500;
      case 'closed':
        return gray600;
      default:
        return gray500;
    }
  }

  static Color statusBadgeBg(String status) {
    switch (status) {
      case 'open':
        return danger50;
      case 'in_progress':
        return warning50;
      case 'resolved':
        return success50;
      case 'closed':
        return gray100;
      default:
        return gray100;
    }
  }

  static Color statusBadgeText(String status) {
    switch (status) {
      case 'open':
        return danger700;
      case 'in_progress':
        return warning700;
      case 'resolved':
        return success700;
      case 'closed':
        return gray600;
      default:
        return gray600;
    }
  }

  // ── Priority colors (aligned with admin badge pattern) ──
  static Color priorityColor(String priority) {
    switch (priority) {
      case 'urgent':
        return danger500;
      case 'high':
        return warning500;
      case 'medium':
        return info500;
      case 'low':
        return success500;
      default:
        return gray500;
    }
  }

  static Color priorityBadgeBg(String priority) {
    switch (priority) {
      case 'urgent':
        return danger50;
      case 'high':
        return warning50;
      case 'medium':
        return info50;
      case 'low':
        return success50;
      default:
        return gray100;
    }
  }

  static Color priorityBadgeText(String priority) {
    switch (priority) {
      case 'urgent':
        return danger700;
      case 'high':
        return warning700;
      case 'medium':
        return info700;
      case 'low':
        return success700;
      default:
        return gray600;
    }
  }
}
