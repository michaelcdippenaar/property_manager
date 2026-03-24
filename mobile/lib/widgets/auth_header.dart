import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import 'klikk_logo.dart';

class AuthHeader extends StatelessWidget {
  const AuthHeader({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: AppColors.primaryNavy,
      padding: const EdgeInsets.only(top: 60, bottom: 40),
      child: const Center(
        child: KlikkLogo(
          fontSize: 36,
          textColor: Colors.white,
        ),
      ),
    );
  }
}
