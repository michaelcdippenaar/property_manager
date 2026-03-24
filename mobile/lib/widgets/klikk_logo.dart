import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

class KlikkLogo extends StatelessWidget {
  final double fontSize;
  final Color textColor;

  const KlikkLogo({
    super.key,
    this.fontSize = 36,
    this.textColor = AppColors.primaryNavy,
  });

  @override
  Widget build(BuildContext context) {
    return RichText(
      text: TextSpan(
        children: [
          TextSpan(
            text: 'Klikk',
            style: TextStyle(
              fontSize: fontSize,
              fontWeight: FontWeight.w700,
              color: textColor,
              letterSpacing: -0.5,
            ),
          ),
          TextSpan(
            text: '.',
            style: TextStyle(
              fontSize: fontSize,
              fontWeight: FontWeight.w700,
              color: AppColors.accentPink,
            ),
          ),
        ],
      ),
    );
  }
}
