import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../services/maintenance_chat_socket.dart';
import '../../services/maintenance_service.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_radius.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/state_views.dart';
import '../../widgets/status_badge.dart';

class IssueDetailScreen extends StatefulWidget {
  const IssueDetailScreen({super.key, required this.issueId});
  final int issueId;
  @override
  State<IssueDetailScreen> createState() => _IssueDetailScreenState();
}

class _IssueDetailScreenState extends State<IssueDetailScreen> {
  MaintenanceIssue? _issue;
  bool _loading = true;
  String? _error;

  // Chat state
  List<MaintenanceActivity> _activities = [];
  bool _chatLoading = false;
  final _chatController = TextEditingController();
  final _scrollController = ScrollController();

  // WebSocket
  late final MaintenanceChatSocket _socket;
  StreamSubscription? _socketSub;
  final Set<int> _seenActivityIds = {};

  @override
  void initState() {
    super.initState();
    _socket = MaintenanceChatSocket(issueId: widget.issueId);
    _load();
  }

  @override
  void dispose() {
    _socketSub?.cancel();
    _socket.dispose();
    _chatController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final issue = await maintenanceService.getIssue(widget.issueId);
      if (mounted) setState(() { _issue = issue; _loading = false; });
      _connectChat();
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _loading = false; });
    }
  }

  bool _wsConnected = false;

  Future<void> _connectChat() async {
    setState(() => _chatLoading = true);

    // Always load via REST first so chat is visible immediately
    await _loadChatRest();

    // Then try WebSocket for real-time updates
    _socketSub = _socket.events.listen(
      (event) {
        if (!mounted) return;
        if (event.isHistory) {
          _wsConnected = true;
          setState(() {
            _activities = event.history!;
            _seenActivityIds.clear();
            for (final a in _activities) {
              _seenActivityIds.add(a.id);
            }
          });
          _scrollToBottom();
        } else {
          final activity = event.activity!;
          if (_seenActivityIds.add(activity.id)) {
            setState(() => _activities.add(activity));
            _scrollToBottom();
          }
        }
      },
      onError: (_) {},
    );
    _socket.connect();
  }

  Future<void> _loadChatRest() async {
    try {
      final activities = await maintenanceService.getActivities(widget.issueId);
      if (mounted) {
        setState(() {
          _activities = activities;
          _seenActivityIds.clear();
          for (final a in _activities) {
            _seenActivityIds.add(a.id);
          }
          _chatLoading = false;
        });
        _scrollToBottom();
      }
    } catch (_) {
      if (mounted) setState(() => _chatLoading = false);
    }
  }

  Future<void> _sendMessage() async {
    final text = _chatController.text.trim();
    if (text.isEmpty) return;

    _chatController.clear();

    // Try WebSocket first, fall back to REST
    if (_wsConnected) {
      _socket.sendMessage(text);
    } else {
      try {
        final activity = await maintenanceService.postActivity(widget.issueId, text);
        if (mounted && _seenActivityIds.add(activity.id)) {
          setState(() => _activities.add(activity));
          _scrollToBottom();
        }
      } catch (e) {
        if (mounted) {
          _chatController.text = text;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to send: $e'), backgroundColor: AppColors.danger500),
          );
        }
      }
    }
  }

  Future<void> _pickAndSendFile() async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery, imageQuality: 80);
    if (picked == null) return;

    setState(() => _chatLoading = true);
    try {
      await maintenanceService.postActivityWithFile(
        widget.issueId,
        picked.path,
        message: _chatController.text.trim(),
      );
      _chatController.clear();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to upload: $e'), backgroundColor: AppColors.danger500),
        );
      }
    } finally {
      if (mounted) setState(() => _chatLoading = false);
    }
  }

  void _showAttachOptions() {
    showModalBottomSheet(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt_rounded),
              title: const Text('Take Photo'),
              onTap: () async {
                Navigator.pop(ctx);
                final picker = ImagePicker();
                final picked = await picker.pickImage(source: ImageSource.camera, imageQuality: 80);
                if (picked != null) {
                  setState(() => _chatLoading = true);
                  try {
                    await maintenanceService.postActivityWithFile(widget.issueId, picked.path);
                  } catch (_) {}
                  if (mounted) setState(() => _chatLoading = false);
                }
              },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_rounded),
              title: const Text('Choose from Gallery'),
              onTap: () {
                Navigator.pop(ctx);
                _pickAndSendFile();
              },
            ),
          ],
        ),
      ),
    );
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffoldBackground,
      appBar: AppBar(
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
        title: Text(_issue?.ticketRef.isNotEmpty == true
            ? _issue!.ticketRef
            : 'Repair Request'),
        leading: IconButton(
            icon: const Icon(Icons.arrow_back_rounded),
            onPressed: () => context.pop()),
      ),
      body: _loading
          ? const LoadingView()
          : _error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : _buildBody(),
    );
  }

  Widget _buildBody() {
    final issue = _issue!;

    return Column(
      children: [
        // Scrollable content: metadata + chat
        Expanded(
          child: ListView(
            controller: _scrollController,
            padding: AppSpacing.listPadding,
            children: [
              // Status + Priority badges
              Row(
                children: [
                  StatusBadge.status(issue.status),
                  const SizedBox(width: AppSpacing.sm),
                  StatusBadge.priority(issue.priority),
                ],
              ),
              const SizedBox(height: AppSpacing.xl),

              // Title
              Text(issue.title,
                  style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary)),
              const SizedBox(height: AppSpacing.xl),

              // Metadata card
              Container(
                padding: const EdgeInsets.all(AppSpacing.lg),
                decoration: BoxDecoration(
                  color: AppColors.cardBackground,
                  borderRadius: BorderRadius.circular(AppRadius.card),
                  border: Border.all(color: AppColors.border),
                ),
                child: Column(
                  children: [
                    _DetailRow(label: 'Category', value: issue.category),
                    _DetailRow(label: 'Priority', value: issue.priority),
                    if (issue.ticketRef.isNotEmpty)
                      _DetailRow(label: 'Reference', value: issue.ticketRef),
                    _DetailRow(
                      label: 'Logged',
                      value: issue.createdAt.isNotEmpty
                          ? issue.createdAt.substring(0, 10)
                          : '\u2014',
                      showDivider: false,
                    ),
                  ],
                ),
              ),

              // Description card
              if (issue.description.isNotEmpty) ...[
                const SizedBox(height: AppSpacing.lg),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  decoration: BoxDecoration(
                    color: AppColors.cardBackground,
                    borderRadius: BorderRadius.circular(AppRadius.card),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Description',
                          style: AppTextStyles.cardLabel
                              .copyWith(fontWeight: FontWeight.w600)),
                      const SizedBox(height: AppSpacing.sm),
                      Text(issue.description, style: AppTextStyles.body),
                    ],
                  ),
                ),
              ],

              // Chat / Activity section
              const SizedBox(height: AppSpacing.xxl),
              const Text('Activity', style: AppTextStyles.sectionTitle),
              const SizedBox(height: AppSpacing.md),

              if (_chatLoading)
                const Padding(
                  padding: EdgeInsets.all(AppSpacing.xxl),
                  child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
                )
              else if (_activities.isEmpty)
                Container(
                  padding: const EdgeInsets.all(AppSpacing.xxl),
                  alignment: Alignment.center,
                  child: const Text('No activity yet. Send a message below.',
                      style: AppTextStyles.bodySecondary),
                )
              else
                ..._activities.map(_buildActivityBubble),
            ],
          ),
        ),

        // Chat input bar
        Container(
          decoration: const BoxDecoration(
            color: AppColors.cardBackground,
            border: Border(top: BorderSide(color: AppColors.border)),
          ),
          padding: EdgeInsets.only(
            left: AppSpacing.lg,
            right: AppSpacing.sm,
            top: AppSpacing.sm,
            bottom: MediaQuery.of(context).padding.bottom + AppSpacing.sm,
          ),
          child: Row(
            children: [
              IconButton(
                onPressed: _showAttachOptions,
                icon: const Icon(Icons.attach_file_rounded),
                color: AppColors.gray400,
                iconSize: 22,
              ),
              Expanded(
                child: TextField(
                  controller: _chatController,
                  textCapitalization: TextCapitalization.sentences,
                  maxLines: 3,
                  minLines: 1,
                  decoration: InputDecoration(
                    hintText: 'Type a message\u2026 Use @agent for AI help',
                    hintStyle: AppTextStyles.bodySecondary.copyWith(fontSize: 13),
                    border: InputBorder.none,
                    contentPadding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
                  ),
                  style: AppTextStyles.body.copyWith(fontSize: 14),
                  onSubmitted: (_) => _sendMessage(),
                ),
              ),
              const SizedBox(width: AppSpacing.xs),
              IconButton(
                onPressed: _sendMessage,
                icon: const Icon(Icons.send_rounded),
                color: AppColors.primaryNavy,
                iconSize: 22,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildActivityBubble(MaintenanceActivity a) {
    final isAi = a.isAi;
    final isSystem = a.activityType == 'status_change' ||
        a.activityType == 'supplier_assigned' ||
        a.activityType == 'system';

    // System events: centered small text
    if (isSystem && !isAi) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
        child: Center(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.xs),
            decoration: BoxDecoration(
              color: AppColors.gray100,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              a.message,
              style: AppTextStyles.cardLabel.copyWith(fontSize: 11),
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );
    }

    // Chat bubbles
    final currentUser = context.read<AuthProvider>().user;
    final isMine = !isAi && a.createdByName != null && currentUser != null
        && a.createdByName == currentUser.fullName;
    final authorName = isAi ? 'AI Assistant' : (a.createdByName ?? 'Unknown');
    final time = _formatTime(a.createdAt);

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: Column(
        crossAxisAlignment: isMine ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          // Author + time
          Padding(
            padding: const EdgeInsets.only(bottom: 2),
            child: Text(
              '$authorName  $time',
              style: AppTextStyles.cardLabel.copyWith(fontSize: 10),
            ),
          ),
          // Bubble
          Container(
            constraints: BoxConstraints(
              maxWidth: MediaQuery.of(context).size.width * 0.78,
            ),
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.md,
              vertical: AppSpacing.sm + 2,
            ),
            decoration: BoxDecoration(
              color: isMine
                  ? Colors.white
                  : AppColors.info50,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: isMine ? AppColors.border : AppColors.info100,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                if (a.hasFile && a.isImage)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Image.network(
                      a.file!,
                      width: double.infinity,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const Icon(Icons.broken_image, size: 48),
                    ),
                  ),
                if (a.hasFile && !a.isImage)
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.insert_drive_file, size: 16, color: AppColors.gray400),
                      const SizedBox(width: 4),
                      Flexible(
                        child: Text(
                          Uri.parse(a.file!).pathSegments.last,
                          style: AppTextStyles.cardLabel.copyWith(fontSize: 12, color: AppColors.primaryNavy),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                if (a.message.isNotEmpty) ...[
                  if (a.hasFile) const SizedBox(height: 6),
                  Text(
                    a.message,
                    style: AppTextStyles.body.copyWith(fontSize: 13.5),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _formatTime(String iso) {
    if (iso.isEmpty) return '';
    try {
      final d = DateTime.parse(iso).toLocal();
      final h = d.hour.toString().padLeft(2, '0');
      final m = d.minute.toString().padLeft(2, '0');
      final months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      return '$h:$m  ${d.day} ${months[d.month - 1]}';
    } catch (_) {
      return '';
    }
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.label,
    required this.value,
    this.showDivider = true,
  });
  final String label;
  final String value;
  final bool showDivider;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
          child: Row(
            children: [
              SizedBox(
                  width: 90,
                  child: Text(label, style: AppTextStyles.cardLabel)),
              Expanded(child: Text(value, style: AppTextStyles.cardValue)),
            ],
          ),
        ),
        if (showDivider) const Divider(height: 1, color: AppColors.divider),
      ],
    );
  }
}
