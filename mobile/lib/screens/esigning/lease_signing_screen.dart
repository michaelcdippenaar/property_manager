import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../providers/auth_provider.dart';
import '../../services/esigning_service.dart';
import '../../services/lease_service.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_radius.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/accent_card.dart';
import '../../widgets/state_views.dart';

class LeaseSigningScreen extends StatefulWidget {
  const LeaseSigningScreen({super.key});

  @override
  State<LeaseSigningScreen> createState() => _LeaseSigningScreenState();
}

class _LeaseSigningScreenState extends State<LeaseSigningScreen> {
  TenantLease? _lease;
  List<ESigningSubmission> _submissions = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final leases = await leaseService.listLeases();
      TenantLease? pick;
      for (final l in leases) {
        if (l.status.toLowerCase() == 'active') {
          pick = l;
          break;
        }
      }
      pick ??= leases.isNotEmpty ? leases.first : null;

      if (pick == null) {
        if (mounted) {
          setState(() {
            _lease = null;
            _submissions = [];
            _loading = false;
          });
        }
        return;
      }

      final subs = await esigningService.listForLease(pick.id);
      if (mounted) {
        setState(() {
          _lease = pick;
          _submissions = subs;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  Future<void> _openSigning(ESigningSubmission sub, ESigningSigner signer) async {
    if (signer.embedSrc.isEmpty) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Signing link not ready yet. Try again shortly.')),
      );
      return;
    }
    final changed = await context.push<bool>(
      '/signing/web',
      extra: <String, dynamic>{
        'embedUrl': signer.embedSrc,
        'submissionId': sub.id,
      },
    );
    if (changed == true && mounted) await _load();
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final userEmail = auth.user?.email ?? '';

    return Scaffold(
      backgroundColor: AppColors.scaffoldBackground,
      appBar: AppBar(
        title: const Text('Lease signing'),
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _buildBody(context, userEmail),
      ),
    );
  }

  Widget _buildBody(BuildContext context, String userEmail) {
    if (_loading) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: const [
          SizedBox(height: 120),
          LoadingView(),
        ],
      );
    }

    if (_error != null) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: AppSpacing.screenPadding,
        children: [
          const SizedBox(height: 48),
          Text(_error!, style: const TextStyle(color: Colors.red)),
          TextButton(onPressed: _load, child: const Text('Retry')),
        ],
      );
    }

    if (_lease == null) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: AppSpacing.screenPadding,
        children: const [
          SizedBox(height: 64),
          Text(
            'No lease found on your account yet.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.textSecondary, fontSize: 15),
          ),
        ],
      );
    }

    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: AppSpacing.screenPadding,
      children: [
        Text(
          _lease!.unitLabel.isNotEmpty ? _lease!.unitLabel : 'Your lease',
          style: AppTextStyles.sectionTitle,
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          'Status: ${_lease!.status}',
          style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
        ),
        const SizedBox(height: AppSpacing.xl),
        if (_submissions.isEmpty)
          Container(
            padding: AppSpacing.cardPadding,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(AppRadius.card),
              border: Border.all(color: AppColors.border),
            ),
            child: const Text(
              'No signing requests yet. Your property manager will send the lease when it is ready.',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 14),
            ),
          )
        else
          ..._submissions.map((sub) => _SubmissionCard(
                submission: sub,
                userEmail: userEmail,
                onSign: (s) => _openSigning(sub, s),
              )),
        const SizedBox(height: 80),
      ],
    );
  }
}

class _SubmissionCard extends StatelessWidget {
  const _SubmissionCard({
    required this.submission,
    required this.userEmail,
    required this.onSign,
  });

  final ESigningSubmission submission;
  final String userEmail;
  final void Function(ESigningSigner signer) onSign;

  @override
  Widget build(BuildContext context) {
    final signer = actionableSignerForUser(
      userEmail: userEmail,
      submission: submission,
    );
    final canOpen = signer != null &&
        signer.embedSrc.isNotEmpty &&
        submission.status != 'completed' &&
        submission.status != 'declined';

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: AccentCard(
        accentColor: AppColors.primaryNavy,
        onTap: canOpen ? () => onSign(signer) : null,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    submission.leaseLabel,
                    style: AppTextStyles.cardTitle,
                  ),
                ),
                _StatusChip(status: submission.status),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              'Mode: ${submission.signingMode}',
              style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
            ),
            const SizedBox(height: AppSpacing.md),
            ...submission.signers.map(
              (s) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  children: [
                    Icon(
                      _iconForSigner(s.status),
                      size: 16,
                      color: AppColors.textSecondary,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${s.name.isNotEmpty ? s.name : s.email} · ${s.role}',
                        style: const TextStyle(fontSize: 13),
                      ),
                    ),
                    Text(
                      s.status,
                      style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                    ),
                  ],
                ),
              ),
            ),
            if (canOpen) ...[
              const SizedBox(height: AppSpacing.md),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: () => onSign(signer),
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.primaryNavy,
                  ),
                  child: const Text('Open signing'),
                ),
              ),
            ] else if (submission.status != 'completed' &&
                userEmail.isNotEmpty &&
                signer == null) ...[
              const SizedBox(height: AppSpacing.sm),
              const Text(
                'Waiting for another signer, or your account email does not match a signer on this document.',
                style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
              ),
            ],
            if (submission.status == 'completed' && submission.signedPdfUrl.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: AppSpacing.sm),
                child: Text(
                  'Signed document is available from your property manager.',
                  style: TextStyle(fontSize: 12, color: Colors.green.shade800),
                ),
              ),
          ],
        ),
      ),
    );
  }

  IconData _iconForSigner(String status) {
    final s = status.toLowerCase();
    if (s == 'completed' || s == 'signed') return Icons.check_circle_outline;
    if (s == 'declined') return Icons.cancel_outlined;
    if (s == 'opened') return Icons.visibility_outlined;
    return Icons.mail_outline;
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final s = status.toLowerCase();
    Color bg;
    Color fg;
    switch (s) {
      case 'completed':
        bg = Colors.green.shade50;
        fg = Colors.green.shade800;
        break;
      case 'declined':
        bg = Colors.red.shade50;
        fg = Colors.red.shade800;
        break;
      case 'in_progress':
        bg = Colors.blue.shade50;
        fg = Colors.blue.shade800;
        break;
      default:
        bg = Colors.grey.shade100;
        fg = Colors.grey.shade800;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        status,
        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: fg),
      ),
    );
  }
}
