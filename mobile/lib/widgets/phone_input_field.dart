import 'package:flutter/material.dart';
import 'package:country_code_picker/country_code_picker.dart';
import '../theme/app_colors.dart';

class PhoneInputField extends StatelessWidget {
  final TextEditingController controller;
  final ValueChanged<CountryCode>? onCountryChanged;

  const PhoneInputField({
    super.key,
    required this.controller,
    this.onCountryChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          decoration: BoxDecoration(
            border: Border.all(color: AppColors.inputBorder),
            borderRadius: BorderRadius.circular(8),
          ),
          child: CountryCodePicker(
            onChanged: onCountryChanged,
            initialSelection: 'ZA',
            showCountryOnly: false,
            showOnlyCountryWhenClosed: false,
            alignLeft: false,
            textStyle: const TextStyle(
              fontSize: 14,
              color: AppColors.textPrimary,
            ),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: TextFormField(
            controller: controller,
            keyboardType: TextInputType.phone,
            decoration: const InputDecoration(
              labelText: 'Mobile number',
            ),
          ),
        ),
      ],
    );
  }
}
