import 'dart:io';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../services/api_client.dart' show apiClient, ApiException;
import '../../theme/app_colors.dart';
import '../../theme/app_radius.dart';
import '../../theme/app_text_styles.dart';

class _Message {
  _Message({
    required this.role,
    required this.content,
    required this.id,
    this.type,
    this.attachmentUrl,
    this.attachmentKind,
    this.localPath,
    this.severity,
    this.userMessage,
    this.skillsUsed,
  });

  final int id;
  final String role;
  final String content;
  final String? type;
  final String? attachmentUrl;
  final String? attachmentKind;
  final String? localPath;
  bool resolved = false;
  String? resolvedText;
  final String? severity;
  final String? userMessage;
  final Map<String, dynamic>? skillsUsed;

  factory _Message.fromJson(Map<String, dynamic> j) {
    final rawKind = j['attachment_kind'] as String?;
    final kindTrim = (rawKind ?? '').trim();
    return _Message(
      id: j['id'] as int? ?? 0,
      role: j['role'] as String? ?? 'assistant',
      content: j['content'] as String? ?? '',
      attachmentUrl: j['attachment_url'] as String?,
      attachmentKind: kindTrim.isEmpty ? null : kindTrim,
    );
  }

  factory _Message.skills({
    required int id,
    required String content,
    required Map<String, dynamic> skillsUsed,
  }) {
    return _Message(
      id: id,
      role: 'assistant',
      type: 'skills',
      content: content,
      skillsUsed: skillsUsed,
    );
  }

  factory _Message.confirm({
    required int id,
    required String content,
    required String userMessage,
    String? severity,
  }) {
    return _Message(
      id: id,
      role: 'assistant',
      type: 'confirm',
      content: content,
      severity: severity,
      userMessage: userMessage,
    );
  }
}

String? _kindFromMimeOrPath(XFile f) {
  final m = (f.mimeType ?? '').toLowerCase();
  if (m.startsWith('video/')) return 'video';
  if (m.startsWith('image/')) return 'image';
  final p = f.path.toLowerCase();
  for (final e in ['.mp4', '.mov', '.m4v', '.webm', '.3gp']) {
    if (p.endsWith(e)) return 'video';
  }
  return 'image';
}

class ChatDetailScreen extends StatefulWidget {
  const ChatDetailScreen({super.key, required this.conversationId});
  final int conversationId;
  @override
  State<ChatDetailScreen> createState() => _ChatDetailScreenState();
}

class _ChatDetailScreenState extends State<ChatDetailScreen> {
  final _ctrl = TextEditingController();
  final _scroll = ScrollController();
  List<_Message> _messages = [];
  bool _loading = true;
  bool _sending = false;
  String _title = 'AI Assistant';
  bool _showMaintenanceReportCta = false;
  bool _openingMaintenanceDraft = false;
  XFile? _pendingAttachment;
  int? _maintenanceRequestId;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await apiClient
          .get('/tenant-portal/conversations/${widget.conversationId}/');
      final msgs = data['messages'] as List? ?? [];
      if (mounted) {
        setState(() {
          _title = data['title'] as String? ?? 'AI Assistant';
          _showMaintenanceReportCta =
              data['maintenance_report_suggested'] == true;
          _maintenanceRequestId = data['maintenance_request_id'] as int?;
          _messages = msgs
              .map((e) => _Message.fromJson(e as Map<String, dynamic>))
              .toList();
          _loading = false;
        });
      }
      _scrollToBottom();
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        final msg = e is ApiException ? e.message : 'Could not load this chat';
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(msg)));
      }
    }
  }

  Future<void> _pickImage(ImageSource source) async {
    final x = await ImagePicker()
        .pickImage(source: source, maxWidth: 2048, imageQuality: 85);
    if (x != null && mounted) setState(() => _pendingAttachment = x);
  }

  Future<void> _pickVideo(ImageSource source) async {
    final x = await ImagePicker().pickVideo(source: source);
    if (x != null && mounted) setState(() => _pendingAttachment = x);
  }

  void _showAttachmentOptions() {
    showModalBottomSheet<void>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Photo from library'),
              onTap: () {
                Navigator.pop(ctx);
                _pickImage(ImageSource.gallery);
              },
            ),
            ListTile(
              leading: const Icon(Icons.camera_alt_outlined),
              title: const Text('Take photo'),
              onTap: () {
                Navigator.pop(ctx);
                _pickImage(ImageSource.camera);
              },
            ),
            ListTile(
              leading: const Icon(Icons.video_library_outlined),
              title: const Text('Video from library'),
              onTap: () {
                Navigator.pop(ctx);
                _pickVideo(ImageSource.gallery);
              },
            ),
            ListTile(
              leading: const Icon(Icons.videocam_outlined),
              title: const Text('Record video'),
              onTap: () {
                Navigator.pop(ctx);
                _pickVideo(ImageSource.camera);
              },
            ),
          ],
        ),
      ),
    );
  }

  static const _maxMessageLength = 5000;

  int _transientMessageId() => -DateTime.now().microsecondsSinceEpoch;

  bool get _hasPendingConfirm =>
      _messages.any((m) => m.type == 'confirm' && !m.resolved);

  bool get _showReportButton =>
      _showMaintenanceReportCta &&
      _maintenanceRequestId == null &&
      !_hasPendingConfirm;

  String _priorityFromSeverity(String? severity) {
    switch ((severity ?? '').toLowerCase()) {
      case 'critical':
        return 'urgent';
      case 'high':
        return 'high';
      case 'low':
        return 'low';
      case 'medium':
      default:
        return 'medium';
    }
  }

  String _truncateTitle(String text) {
    final clean = text.trim();
    if (clean.isEmpty) return 'Maintenance report';
    return clean.length <= 120 ? clean : clean.substring(0, 120);
  }

  Future<void> _send() async {
    final text = _ctrl.text.trim();
    final pending = _pendingAttachment;
    if ((text.isEmpty && pending == null) || _sending) return;
    if (text.length > _maxMessageLength) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Message is too long (max 5 000 characters)')),
      );
      return;
    }

    final kind = pending != null ? _kindFromMimeOrPath(pending) : null;
    final placeholder = pending != null
        ? (kind == 'video' ? '(Video attached)' : '(Photo attached)')
        : null;
    final displayContent = text.isNotEmpty ? text : (placeholder ?? '');

    _ctrl.clear();
    setState(() => _pendingAttachment = null);

    final optimistic = _Message(
      id: -DateTime.now().millisecondsSinceEpoch,
      role: 'user',
      content: displayContent,
      localPath: pending?.path,
      attachmentKind: kind,
    );
    setState(() {
      _messages.add(optimistic);
      _sending = true;
    });
    _scrollToBottom();
    try {
      final Map<String, dynamic> data;
      if (pending != null) {
        data = await apiClient.postMultipart(
          '/tenant-portal/conversations/${widget.conversationId}/messages/',
          content: text.isNotEmpty ? text : null,
          filePath: pending.path,
        );
      } else {
        data = await apiClient.post(
          '/tenant-portal/conversations/${widget.conversationId}/messages/',
          body: {'content': text},
        );
      }
      final userMsg = data['user_message'] != null
          ? _Message.fromJson(data['user_message'] as Map<String, dynamic>)
          : null;
      final aiMsg = data['ai_message'] != null
          ? _Message.fromJson(data['ai_message'] as Map<String, dynamic>)
          : null;
      if (mounted) {
        setState(() {
          _messages.removeWhere((m) => m.id == optimistic.id);
          if (userMsg != null) _messages.add(userMsg);
          if (aiMsg != null) _messages.add(aiMsg);
          _sending = false;
          _maintenanceRequestId = data['maintenance_request_id'] as int?;
          final conv = data['conversation'];
          if (conv is Map &&
              conv['title'] is String &&
              (conv['title'] as String).isNotEmpty) {
            _title = conv['title'] as String;
          }
          if (data['maintenance_report_suggested'] == true) {
            _showMaintenanceReportCta = true;
          }
          final skillsUsed = data['skills_used'];
          if (skillsUsed is Map<String, dynamic>) {
            final preview = skillsUsed['preview'];
            if (skillsUsed['used'] == true &&
                preview is List &&
                preview.isNotEmpty) {
              final total = skillsUsed['count'] is int
                  ? skillsUsed['count'] as int
                  : preview.length;
              _messages.add(
                _Message.skills(
                  id: _transientMessageId(),
                  content:
                      'The tenant chat injected $total maintenance skill${total == 1 ? '' : 's'} into the AI context.',
                  skillsUsed: skillsUsed,
                ),
              );
            }
          }
          final isMaintenance = data['interaction_type'] == 'maintenance' ||
              data['maintenance_report_suggested'] == true;
          final ticketMissing = data['maintenance_request'] == null &&
              data['maintenance_request_id'] == null;
          if (isMaintenance && ticketMissing) {
            final severity = data['severity'] as String?;
            final severityLabel = severity != null && severity.isNotEmpty
                ? ' ($severity priority)'
                : '';
            _messages.add(
              _Message.confirm(
                id: _transientMessageId(),
                content:
                    'Should I log this as a maintenance ticket?$severityLabel',
                severity: severity,
                userMessage: text,
              ),
            );
          }
        });
      }
      final ticket = data['maintenance_request'];
      if (mounted && ticket is Map) {
        final id = ticket['id'];
        final pri = ticket['priority'] as String? ?? '';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              id != null
                  ? 'Maintenance ticket #$id logged${pri.isNotEmpty ? ' ($pri priority)' : ''}.'
                  : 'A maintenance ticket was logged for the property team.',
            ),
          ),
        );
      }
      _scrollToBottom();
    } catch (e) {
      if (mounted) {
        setState(() {
          _messages.removeWhere((m) => m.id == optimistic.id);
          _sending = false;
        });
        final msg = e is ApiException ? e.message : 'Could not send message';
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(msg)));
      }
    }
  }

  Future<void> _confirmTicket(_Message message, bool accept) async {
    setState(() {
      message.resolved = true;
      if (!accept) {
        message.resolvedText = 'No ticket created.';
      }
    });
    if (!accept) return;

    final initialChatHistory = _messages
        .where((entry) =>
            entry.type == null &&
            (entry.role == 'user' || entry.role == 'assistant'))
        .map(
          (entry) => {
            'role': entry.role,
            'content': entry.content,
          },
        )
        .toList();

    try {
      final data = await apiClient.post(
        '/maintenance/',
        body: {
          'title': _truncateTitle(message.userMessage ?? ''),
          'description': message.userMessage ?? '',
          'priority': _priorityFromSeverity(message.severity),
          'category': 'other',
          'initial_chat_history': initialChatHistory,
          'conversation_id': widget.conversationId,
        },
      );
      if (!mounted) return;
      setState(() {
        _maintenanceRequestId = data['id'] as int?;
        message.resolvedText = 'Ticket #${data['id']} created.';
        _messages.add(
          _Message(
            id: _transientMessageId(),
            role: 'assistant',
            content:
                'Ticket #${data['id']} has been logged. You can find it in the Issues section.',
          ),
        );
      });
      _scrollToBottom();
    } catch (e) {
      if (!mounted) return;
      final err = e is ApiException ? e.message : 'Could not create ticket';
      setState(() {
        message.resolvedText = 'Failed: $err';
        _messages.add(
          _Message(
            id: _transientMessageId(),
            role: 'assistant',
            content: 'Could not create ticket: $err',
          ),
        );
      });
      _scrollToBottom();
    }
  }

  Future<void> _openReportFromChat() async {
    if (_sending || _openingMaintenanceDraft) return;
    setState(() => _openingMaintenanceDraft = true);
    try {
      final data = await apiClient.post(
        '/tenant-portal/conversations/${widget.conversationId}/maintenance-draft/',
        body: {},
      );
      if (!mounted) return;
      setState(() => _openingMaintenanceDraft = false);
      context.push('/issues/report', extra: data);
    } catch (e) {
      if (!mounted) return;
      setState(() => _openingMaintenanceDraft = false);
      final msg =
          e is ApiException ? e.message : 'Could not prepare report from chat';
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  bool _pendingIsVideo(XFile f) => _kindFromMimeOrPath(f) == 'video';

  @override
  Widget build(BuildContext context) {
    final pending = _pendingAttachment;
    return Scaffold(
      backgroundColor: AppColors.scaffoldBackground,
      appBar: AppBar(
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
        title: Text(_title, overflow: TextOverflow.ellipsis),
        leading: IconButton(
            icon: const Icon(Icons.arrow_back_rounded),
            onPressed: () => context.pop()),
      ),
      body: Column(
        children: [
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _messages.isEmpty
                    ? const Center(
                        child: Text(
                          'Start the conversation below',
                          style: AppTextStyles.emptySubtitle,
                        ),
                      )
                    : ListView.builder(
                        controller: _scroll,
                        padding: const EdgeInsets.all(16),
                        itemCount: _messages.length + (_sending ? 1 : 0),
                        itemBuilder: (ctx, i) {
                          if (i == _messages.length) {
                            return const _TypingIndicator();
                          }
                          final message = _messages[i];
                          if (message.type == 'confirm') {
                            return _ConfirmCard(
                              message: message,
                              onAccept: () => _confirmTicket(message, true),
                              onDecline: () => _confirmTicket(message, false),
                            );
                          }
                          if (message.type == 'skills') {
                            return _SkillsCard(message: message);
                          }
                          return _Bubble(message: message);
                        },
                      ),
          ),
          Container(
            color: Colors.white,
            padding: EdgeInsets.only(
              left: 16,
              right: 12,
              top: 10,
              bottom: MediaQuery.of(context).padding.bottom + 10,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (pending != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Row(
                      children: [
                        ClipRRect(
                          borderRadius: BorderRadius.circular(AppRadius.small),
                          child: _pendingIsVideo(pending)
                              ? Container(
                                  width: 56,
                                  height: 56,
                                  color: AppColors.border,
                                  child: const Icon(Icons.videocam,
                                      color: AppColors.textSecondary),
                                )
                              : Image.file(
                                  File(pending.path),
                                  width: 56,
                                  height: 56,
                                  fit: BoxFit.cover,
                                ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            _pendingIsVideo(pending)
                                ? 'Video ready to send'
                                : 'Photo ready to send',
                            style: const TextStyle(
                                fontSize: 13, color: AppColors.textSecondary),
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close_rounded),
                          onPressed: () =>
                              setState(() => _pendingAttachment = null),
                        ),
                      ],
                    ),
                  ),
                Row(
                  children: [
                    IconButton(
                      onPressed: _sending ? null : _showAttachmentOptions,
                      icon: const Icon(Icons.attach_file_rounded),
                      color: AppColors.primaryNavy,
                    ),
                    Expanded(
                      child: TextField(
                        controller: _ctrl,
                        decoration: InputDecoration(
                          hintText: 'Type a message…',
                          hintStyle:
                              const TextStyle(color: AppColors.textSecondary),
                          filled: true,
                          fillColor: AppColors.scaffoldBackground,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(AppRadius.pill),
                            borderSide: BorderSide.none,
                          ),
                          contentPadding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 10),
                        ),
                        textInputAction: TextInputAction.send,
                        onSubmitted: (_) => _send(),
                        maxLines: null,
                      ),
                    ),
                    const SizedBox(width: 8),
                    GestureDetector(
                      onTap: _send,
                      child: Container(
                        width: 42,
                        height: 42,
                        decoration: const BoxDecoration(
                          color: AppColors.primaryNavy,
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.send_rounded,
                            color: Colors.white, size: 18),
                      ),
                    ),
                  ],
                ),
                if (_showReportButton) ...[
                  const Divider(
                      height: 20, thickness: 1, color: AppColors.border),
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: _sending || _openingMaintenanceDraft
                          ? null
                          : _openReportFromChat,
                      icon: _openingMaintenanceDraft
                          ? const SizedBox(
                              width: 22,
                              height: 22,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: AppColors.primaryNavy),
                            )
                          : const Icon(Icons.build_circle_outlined, size: 22),
                      label: Text(_openingMaintenanceDraft
                          ? 'Preparing form from chat…'
                          : 'Report maintenance issue'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppColors.primaryNavy,
                        side: const BorderSide(color: AppColors.border),
                        padding: const EdgeInsets.symmetric(
                            vertical: 12, horizontal: 14),
                        shape: RoundedRectangleBorder(
                            borderRadius:
                                BorderRadius.circular(AppRadius.medium)),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.message});
  final _Message message;

  static bool _hidePlaceholderCaption(_Message m) {
    final hasVisual = m.localPath != null ||
        (m.attachmentUrl != null && m.attachmentUrl!.isNotEmpty);
    if (!hasVisual) return false;
    final c = m.content.trim();
    return c == '(Photo attached)' || c == '(Video attached)';
  }

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == 'user';
    final kind = message.attachmentKind ?? '';
    final hideCaption = _hidePlaceholderCaption(message);

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        constraints:
            BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.76),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          gradient: isUser
              ? const LinearGradient(
                  colors: [AppColors.navyDark, AppColors.navyLight],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : null,
          color: isUser ? null : Colors.white,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isUser ? 16 : 4),
            bottomRight: Radius.circular(isUser ? 4 : 16),
          ),
          boxShadow: isUser
              ? null
              : [
                  BoxShadow(
                      color: Colors.black.withValues(alpha: 0.06),
                      blurRadius: 6,
                      offset: const Offset(0, 1))
                ],
          border: isUser ? null : Border.all(color: AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (message.localPath != null) ...[
              ClipRRect(
                borderRadius: BorderRadius.circular(AppRadius.medium),
                child: kind == 'video'
                    ? Container(
                        width: double.infinity,
                        constraints: const BoxConstraints(maxHeight: 160),
                        color: isUser ? Colors.white24 : AppColors.border,
                        child: Icon(
                          Icons.videocam,
                          size: 48,
                          color:
                              isUser ? Colors.white70 : AppColors.textSecondary,
                        ),
                      )
                    : SizedBox(
                        width: double.infinity,
                        height: 200,
                        child: Image.file(
                          File(message.localPath!),
                          fit: BoxFit.cover,
                        ),
                      ),
              ),
              if (!hideCaption) const SizedBox(height: 8),
            ] else if (message.attachmentUrl != null &&
                message.attachmentUrl!.isNotEmpty) ...[
              ClipRRect(
                borderRadius: BorderRadius.circular(AppRadius.medium),
                child: kind == 'video'
                    ? Material(
                        color:
                            isUser ? Colors.white24 : const Color(0xFFF3F4F6),
                        child: InkWell(
                          onTap: () async {
                            final u = Uri.tryParse(message.attachmentUrl!);
                            if (u == null ||
                                (u.scheme != 'https' && u.scheme != 'http')) {
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                      content: Text('Invalid video URL')),
                                );
                              }
                              return;
                            }
                            if (!await launchUrl(u,
                                    mode: LaunchMode.externalApplication) &&
                                context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                    content: Text('Could not open video')),
                              );
                            }
                          },
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                                vertical: 20, horizontal: 12),
                            child: Row(
                              children: [
                                Icon(
                                  Icons.play_circle_outline_rounded,
                                  color: isUser
                                      ? Colors.white
                                      : AppColors.primaryNavy,
                                  size: 36,
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(
                                    'Open video',
                                    style: TextStyle(
                                      color: isUser
                                          ? Colors.white
                                          : AppColors.textPrimary,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      )
                    : SizedBox(
                        width: double.infinity,
                        height: 200,
                        child: Image.network(
                          message.attachmentUrl!,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) => Padding(
                            padding: const EdgeInsets.all(12),
                            child: Text(
                              'Could not load image',
                              style: TextStyle(
                                  color: isUser
                                      ? Colors.white70
                                      : AppColors.textSecondary),
                            ),
                          ),
                        ),
                      ),
              ),
              if (!hideCaption) const SizedBox(height: 8),
            ],
            if (!hideCaption && message.content.isNotEmpty)
              Text(
                message.content,
                style: TextStyle(
                  color: isUser ? Colors.white : AppColors.textPrimary,
                  fontSize: 14,
                  height: 1.45,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _ConfirmCard extends StatelessWidget {
  const _ConfirmCard({
    required this.message,
    required this.onAccept,
    required this.onDecline,
  });

  final _Message message;
  final VoidCallback onAccept;
  final VoidCallback onDecline;

  @override
  Widget build(BuildContext context) {
    final created = (message.resolvedText ?? '').startsWith('Ticket #');
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        constraints:
            BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.86),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.warning50,
          borderRadius: BorderRadius.circular(AppRadius.xl),
          border: Border.all(color: AppColors.warning100),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.warning_amber_rounded,
                    size: 15, color: AppColors.warning700),
                const SizedBox(width: 6),
                Text(
                  'MAINTENANCE IDENTIFIED',
                  style: AppTextStyles.sectionLabel
                      .copyWith(color: AppColors.warning700),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(message.content, style: AppTextStyles.body),
            const SizedBox(height: 10),
            if (!message.resolved)
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  FilledButton(
                    onPressed: onAccept,
                    style: FilledButton.styleFrom(
                      backgroundColor: AppColors.primaryNavy,
                      foregroundColor: Colors.white,
                    ),
                    child: const Text('Yes, log ticket'),
                  ),
                  OutlinedButton(
                    onPressed: onDecline,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.textSecondary,
                      side: const BorderSide(color: AppColors.gray300),
                    ),
                    child: const Text('No, skip'),
                  ),
                ],
              )
            else
              Row(
                children: [
                  if (created) ...[
                    const Icon(Icons.check_circle_rounded,
                        size: 15, color: AppColors.success600),
                    const SizedBox(width: 6),
                  ],
                  Expanded(
                    child: Text(
                      message.resolvedText ?? '',
                      style: AppTextStyles.cardSubtitle
                          .copyWith(fontStyle: FontStyle.italic),
                    ),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _SkillsCard extends StatelessWidget {
  const _SkillsCard({required this.message});

  final _Message message;

  @override
  Widget build(BuildContext context) {
    final preview =
        (message.skillsUsed?['preview'] as List?)?.cast<String>() ?? const [];
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        constraints:
            BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.9),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.info50,
          borderRadius: BorderRadius.circular(AppRadius.xl),
          border: Border.all(color: AppColors.info100),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.menu_book_rounded,
                    size: 15, color: AppColors.info700),
                const SizedBox(width: 6),
                Text(
                  'SKILLS USED IN CHAT',
                  style: AppTextStyles.sectionLabel
                      .copyWith(color: AppColors.info700),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(message.content, style: AppTextStyles.body),
            if (preview.isNotEmpty) ...[
              const SizedBox(height: 10),
              for (final line in preview) ...[
                Container(
                  width: double.infinity,
                  margin: const EdgeInsets.only(bottom: 6),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.8),
                    borderRadius: BorderRadius.circular(AppRadius.small),
                    border: Border.all(color: AppColors.info100),
                  ),
                  child: SelectableText(
                    line,
                    style: const TextStyle(
                      fontSize: 12,
                      height: 1.4,
                      color: AppColors.gray700,
                      fontFamily: 'monospace',
                    ),
                  ),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }
}

class _TypingIndicator extends StatelessWidget {
  const _TypingIndicator();
  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(16),
            topRight: Radius.circular(16),
            bottomRight: Radius.circular(16),
            bottomLeft: Radius.circular(4),
          ),
          border: Border.all(color: AppColors.border),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _Dot(delay: 0),
            SizedBox(width: 4),
            _Dot(delay: 150),
            SizedBox(width: 4),
            _Dot(delay: 300),
          ],
        ),
      ),
    );
  }
}

class _Dot extends StatefulWidget {
  const _Dot({required this.delay});
  final int delay;
  @override
  State<_Dot> createState() => _DotState();
}

class _DotState extends State<_Dot> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 600));
    _anim = Tween<double>(begin: 0.4, end: 1.0).animate(
      CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut),
    );
    Future.delayed(Duration(milliseconds: widget.delay), () {
      if (mounted) _ctrl.repeat(reverse: true);
    });
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _anim,
      child: Container(
        width: 7,
        height: 7,
        decoration: const BoxDecoration(
            color: AppColors.textSecondary, shape: BoxShape.circle),
      ),
    );
  }
}
