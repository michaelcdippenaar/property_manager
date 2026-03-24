import 'package:flutter/material.dart';
import 'package:pin_code_fields/pin_code_fields.dart';
import '../theme/app_colors.dart';

class OtpInputRow extends StatelessWidget {
  final ValueChanged<String> onCompleted;
  final ValueChanged<String>? onChanged;

  const OtpInputRow({
    super.key,
    required this.onCompleted,
    this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return PinCodeTextField(
      appContext: context,
      length: 6,
      onCompleted: onCompleted,
      onChanged: onChanged ?? (_) {},
      keyboardType: TextInputType.number,
      animationType: AnimationType.fade,
      pinTheme: PinTheme(
        shape: PinCodeFieldShape.box,
        borderRadius: BorderRadius.circular(8),
        fieldHeight: 52,
        fieldWidth: 44,
        activeFillColor: Colors.white,
        inactiveFillColor: Colors.white,
        selectedFillColor: Colors.white,
        activeColor: AppColors.primaryNavy,
        inactiveColor: AppColors.inputBorder,
        selectedColor: AppColors.primaryNavy,
      ),
      enableActiveFill: true,
      textStyle: const TextStyle(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        color: AppColors.primaryNavy,
      ),
    );
  }
}
