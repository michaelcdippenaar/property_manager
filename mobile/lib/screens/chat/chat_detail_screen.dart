import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../services/api_client.dart';
import '../../theme/app_colors.dart';

class _Message {
  _Message({required this.role, required this.content, required this.id});
  final int id;
  final String role;
  final String content;

  factory _Message.fromJson(Map<String, dynamic> j) => _Message(
    id: j['id'] as int? ?? 0,
    role: j['role'] as String? ?? 'assistant',
    content: j['content'] as String? ?? '',
  );
}

class ChatDetailScreen extends StatefulWidget {
  const ChatDetailScreen({super.key, required this.conversationId});
  final int conversationId;
  @override State<ChatDetailScreen> createState() => _ChatDetailScreenState();
}

class _ChatDetailScreenState extends State<ChatDetailScreen> {
  final _ctrl = TextEditingController();
  final _scroll = ScrollController();
  List<_Message> _messages = [];
  bool _loading = true;
  bool _sending = false;
  String _title = 'AI Assistant';

  @override
  void initState() { super.initState(); _load(); }

  @override
  void dispose() { _ctrl.dispose(); _scroll.dispose(); super.dispose(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await apiClient.get('/tenant-portal/conversations/${widget.conversationId}/');
      final msgs = data['messages'] as List? ?? [];
      if (mounted) setState(() {
        _title = data['title'] as String? ?? 'AI Assistant';
        _messages = msgs.map((e) => _Message.fromJson(e as Map<String, dynamic>)).toList();
        _loading = false;
      });
      _scrollToBottom();
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _send() async {
    final text = _ctrl.text.trim();
    if (text.isEmpty || _sending) return;
    _ctrl.clear();
    final optimistic = _Message(id: -DateTime.now().millisecondsSinceEpoch, role: 'user', content: text);
    setState(() { _messages.add(optimistic); _sending = true; });
    _scrollToBottom();
    try {
      final data = await apiClient.post(
        '/tenant-portal/conversations/${widget.conversationId}/messages/',
        body: {'content': text},
      );
      final userMsg = data['user_message'] != null ? _Message.fromJson(data['user_message'] as Map<String, dynamic>) : null;
      final aiMsg = data['ai_message'] != null ? _Message.fromJson(data['ai_message'] as Map<String, dynamic>) : null;
      if (mounted) setState(() {
        _messages.removeWhere((m) => m.id == optimistic.id);
        if (userMsg != null) _messages.add(userMsg);
        if (aiMsg != null) _messages.add(aiMsg);
        _sending = false;
      });
      _scrollToBottom();
    } catch (_) {
      if (mounted) setState(() { _messages.removeWhere((m) => m.id == optimistic.id); _sending = false; });
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) _scroll.animateTo(_scroll.position.maxScrollExtent, duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F6FA),
      appBar: AppBar(
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
        title: Text(_title, overflow: TextOverflow.ellipsis),
        leading: IconButton(icon: const Icon(Icons.arrow_back_rounded), onPressed: () => context.pop()),
      ),
      body: Column(
        children: [
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _messages.isEmpty
                    ? const Center(child: Text('Start the conversation below', style: TextStyle(color: AppColors.textSecondary)))
                    : ListView.builder(
                        controller: _scroll,
                        padding: const EdgeInsets.all(16),
                        itemCount: _messages.length + (_sending ? 1 : 0),
                        itemBuilder: (ctx, i) {
                          if (i == _messages.length) return const _TypingIndicator();
                          return _Bubble(message: _messages[i]);
                        },
                      ),
          ),
          // Composer
          Container(
            color: Colors.white,
            padding: EdgeInsets.only(left: 16, right: 12, top: 10, bottom: MediaQuery.of(context).padding.bottom + 10),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _ctrl,
                    decoration: InputDecoration(
                      hintText: 'Type a message…',
                      hintStyle: const TextStyle(color: AppColors.textSecondary),
                      filled: true, fillColor: const Color(0xFFF5F6FA),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(22), borderSide: BorderSide.none),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
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
                    width: 42, height: 42,
                    decoration: const BoxDecoration(color: AppColors.primaryNavy, shape: BoxShape.circle),
                    child: const Icon(Icons.send_rounded, color: Colors.white, size: 18),
                  ),
                ),
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

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == 'user';
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.76),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          gradient: isUser ? const LinearGradient(colors: [Color(0xFF0F2744), Color(0xFF1B3F6B)], begin: Alignment.topLeft, end: Alignment.bottomRight) : null,
          color: isUser ? null : Colors.white,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isUser ? 16 : 4),
            bottomRight: Radius.circular(isUser ? 4 : 16),
          ),
          boxShadow: isUser ? null : [BoxShadow(color: Colors.black.withOpacity(0.06), blurRadius: 6, offset: const Offset(0, 1))],
          border: isUser ? null : Border.all(color: const Color(0xFFE5E7EB)),
        ),
        child: Text(message.content, style: TextStyle(color: isUser ? Colors.white : const Color(0xFF1A1A2E), fontSize: 14, height: 1.45)),
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
          borderRadius: const BorderRadius.only(topLeft: Radius.circular(16), topRight: Radius.circular(16), bottomRight: Radius.circular(16), bottomLeft: Radius.circular(4)),
          border: Border.all(color: const Color(0xFFE5E7EB)),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _Dot(delay: 0), SizedBox(width: 4), _Dot(delay: 150), SizedBox(width: 4), _Dot(delay: 300),
          ],
        ),
      ),
    );
  }
}

class _Dot extends StatefulWidget {
  const _Dot({required this.delay});
  final int delay;
  @override State<_Dot> createState() => _DotState();
}

class _DotState extends State<_Dot> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 600));
    _anim = Tween<double>(begin: 0.4, end: 1.0).animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut));
    Future.delayed(Duration(milliseconds: widget.delay), () {
      if (mounted) _ctrl.repeat(reverse: true);
    });
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _anim,
      child: Container(width: 7, height: 7, decoration: const BoxDecoration(color: AppColors.textSecondary, shape: BoxShape.circle)),
    );
  }
}
