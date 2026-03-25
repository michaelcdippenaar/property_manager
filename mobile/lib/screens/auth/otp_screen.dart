import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../theme/app_colors.dart';
import '../../widgets/auth_header.dart';
import '../../widgets/auth_card.dart';
import '../../widgets/primary_button.dart';
import '../../widgets/otp_input_row.dart';

enum OtpMode { login, signup }

class OtpScreen extends StatefulWidget {
  final OtpMode mode;
  final String phone;

  const OtpScreen({
    super.key,
    required this.mode,
    required this.phone,
  });

  @override
  State<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends State<OtpScreen> {
  String _otp = '';
  bool _isLoading = false;

  Future<void> _verify() async {
    if (_otp.length < 6) return;
    setState(() => _isLoading = true);
    // TODO: call POST /api/v1/auth/otp/verify/
    await Future.delayed(const Duration(seconds: 1));
    setState(() => _isLoading = false);
    if (mounted) context.go('/home');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.primaryNavy,
      body: Column(
        children: [
          const AuthHeader(),
          AuthCard(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Enter OTP',
                    style: TextStyle(
                      fontSize: 26,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'We sent a 6-digit code to ${widget.phone}',
                    style: const TextStyle(
                      fontSize: 14,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 32),
                  OtpInputRow(
                    onCompleted: (val) => setState(() => _otp = val),
                    onChanged: (val) => setState(() => _otp = val),
                  ),
                  const SizedBox(height: 24),
                  PrimaryButton(
                    label: 'Verify',
                    onPressed: _otp.length == 6 ? _verify : null,
                    isLoading: _isLoading,
                  ),
                  const SizedBox(height: 16),
                  Center(
                    child: TextButton(
                      onPressed: () {},
                      child: const Text(
                        'Resend OTP',
                        style: TextStyle(color: AppColors.primaryNavy),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
