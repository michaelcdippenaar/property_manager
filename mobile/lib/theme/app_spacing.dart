import 'package:flutter/material.dart';

/// Standardised spacing tokens used across the app.
class AppSpacing {
  AppSpacing._();

  // Base increments
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 20;
  static const double xxl = 24;
  static const double xxxl = 32;

  // Screen-level horizontal padding (consistent across all shell tabs).
  static const double screenH = 20;

  // List-item vertical gap.
  static const double listGap = 10;

  // Section title bottom padding.
  static const double sectionGap = 12;

  // Convenience EdgeInsets
  static const EdgeInsets screenPadding = EdgeInsets.symmetric(horizontal: screenH);
  static const EdgeInsets listPadding = EdgeInsets.symmetric(horizontal: screenH, vertical: lg);
  static const EdgeInsets cardPadding = EdgeInsets.all(lg);
}
