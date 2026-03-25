import 'package:flutter/material.dart';

class IconMapper {
  IconMapper._();

  static IconData fromType(String iconType) {
    switch (iconType) {
      case 'wifi':
        return Icons.wifi_rounded;
      case 'alarm':
        return Icons.security_rounded;
      case 'garbage':
        return Icons.delete_outline_rounded;
      case 'parking':
        return Icons.local_parking_rounded;
      case 'electricity':
        return Icons.bolt_rounded;
      case 'water':
        return Icons.water_drop_outlined;
      case 'rules':
        return Icons.gavel_rounded;
      default:
        return Icons.info_outline_rounded;
    }
  }

  static bool isSensitive(String iconType) {
    return iconType == 'wifi' || iconType == 'alarm';
  }
}
