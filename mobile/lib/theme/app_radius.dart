import 'package:flutter/material.dart';

class AppRadius {
  AppRadius._();

  static const double small = 8;
  static const double medium = 12;
  static const double card = 12;
  static const double large = 12;
  static const double xl = 16;
  static const double pill = 28;

  static BorderRadius get smallBorder => BorderRadius.circular(small);
  static BorderRadius get mediumBorder => BorderRadius.circular(medium);
  static BorderRadius get cardBorder => BorderRadius.circular(card);
  static BorderRadius get largeBorder => BorderRadius.circular(large);
  static BorderRadius get xlBorder => BorderRadius.circular(xl);
  static BorderRadius get pillBorder => BorderRadius.circular(pill);
}
