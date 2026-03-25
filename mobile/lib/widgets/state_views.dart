import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_radius.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text_styles.dart';

/// Standardised loading view.
///
/// Default shows skeleton shimmer cards; use [LoadingView.spinner] for inline
/// button / small-area loading states.
class LoadingView extends StatelessWidget {
  const LoadingView({super.key}) : _useSpinner = false;

  const LoadingView.spinner({super.key}) : _useSpinner = true;

  final bool _useSpinner;

  @override
  Widget build(BuildContext context) {
    if (_useSpinner) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.only(top: 80),
          child: CircularProgressIndicator(),
        ),
      );
    }
    return const SkeletonListView();
  }
}

/// Consistent error state with icon, message, and retry button.
class ErrorView extends StatelessWidget {
  const ErrorView({
    super.key,
    required this.message,
    this.onRetry,
  });

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xxxl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_outlined,
                size: 48, color: AppColors.textSecondary),
            const SizedBox(height: AppSpacing.lg),
            Text(
              message,
              textAlign: TextAlign.center,
              style: AppTextStyles.bodySecondary,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: AppSpacing.xl),
              FilledButton(
                onPressed: onRetry,
                style: FilledButton.styleFrom(
                    backgroundColor: AppColors.primaryNavy),
                child: const Text('Retry'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Consistent empty state with icon, title, and optional subtitle.
class EmptyView extends StatelessWidget {
  const EmptyView({
    super.key,
    required this.icon,
    required this.title,
    this.subtitle,
    this.iconColor,
  });

  final IconData icon;
  final String title;
  final String? subtitle;
  final Color? iconColor;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 56, color: iconColor ?? AppColors.textSecondary),
          const SizedBox(height: AppSpacing.lg),
          Text(title, style: AppTextStyles.emptyTitle),
          if (subtitle != null) ...[
            const SizedBox(height: AppSpacing.sm),
            Text(subtitle!, style: AppTextStyles.emptySubtitle),
          ],
        ],
      ),
    );
  }
}

// ── Skeleton shimmer components (matching admin animate-pulse pattern) ──

/// A single skeleton card with animated pulse, mimicking a list item layout.
class SkeletonCard extends StatefulWidget {
  const SkeletonCard({super.key});

  @override
  State<SkeletonCard> createState() => _SkeletonCardState();
}

class _SkeletonCardState extends State<SkeletonCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
    _opacity = Tween<double>(begin: 0.3, end: 0.7).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _opacity,
      builder: (context, child) {
        return Container(
          padding: const EdgeInsets.all(AppSpacing.lg),
          decoration: BoxDecoration(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(AppRadius.card),
            border: Border.all(color: AppColors.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  _bar(width: 120, height: 14),
                  const Spacer(),
                  _bar(width: 60, height: 20, radius: AppRadius.pill),
                ],
              ),
              const SizedBox(height: 12),
              _bar(width: double.infinity, height: 12),
              const SizedBox(height: 8),
              _bar(width: 200, height: 12),
            ],
          ),
        );
      },
    );
  }

  Widget _bar({
    required double width,
    required double height,
    double radius = 4,
  }) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: AppColors.gray200.withValues(alpha: _opacity.value),
        borderRadius: BorderRadius.circular(radius),
      ),
    );
  }
}

/// Renders a list of [SkeletonCard]s as a loading placeholder.
class SkeletonListView extends StatelessWidget {
  const SkeletonListView({super.key, this.count = 5});

  final int count;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: AppSpacing.listPadding,
      physics: const NeverScrollableScrollPhysics(),
      shrinkWrap: true,
      itemCount: count,
      separatorBuilder: (_, __) => const SizedBox(height: AppSpacing.listGap),
      itemBuilder: (_, __) => const SkeletonCard(),
    );
  }
}
