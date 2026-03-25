import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../services/api_client.dart' show apiClient, ApiException;
import '../../theme/app_colors.dart';

class _Conversation {
  _Conversation({required this.id, required this.title, required this.lastMessage, required this.updatedAt});
  final int id;
  final String title;
  final String lastMessage;
  final String updatedAt;

  factory _Conversation.fromJson(Map<String, dynamic> j) => _Conversation(
    id: (j['id'] as num?)?.toInt() ?? 0,
    title: j['title'] as String? ?? 'Conversation',
    lastMessage: j['last_message'] as String? ?? '',
    updatedAt: j['updated_at'] as String? ?? '',
  );
}

class ChatListScreen extends StatefulWidget {
  const ChatListScreen({super.key});
  @override State<ChatListScreen> createState() => _ChatListScreenState();
}

class _ChatListScreenState extends State<ChatListScreen> {
  List<_Conversation> _convos = [];
  bool _loading = true;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await apiClient.getList('/tenant-portal/conversations/');
      if (!mounted) return;
      final list = data is List ? data : <dynamic>[];
      setState(() {
        _convos = list
            .map((e) => _Conversation.fromJson(e as Map<String, dynamic>))
            .where((c) => c.id > 0)
            .toList();
        _loading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        final msg = e is ApiException ? e.message : 'Could not load conversations';
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
      }
    }
  }

  int _parseConversationId(dynamic raw) {
    if (raw is int) return raw;
    if (raw is num) return raw.toInt();
    return int.tryParse('$raw') ?? 0;
  }

  Future<void> _openChat(int id) async {
    if (id <= 0) return;
    await context.push('/chat/$id');
    if (mounted) await _load();
  }

  Future<void> _newChat() async {
    try {
      final data = await apiClient.post('/tenant-portal/conversations/', body: {});
      final id = _parseConversationId(data['id']);
      if (id <= 0) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not create conversation — invalid response.')),
        );
        return;
      }
      if (!mounted) return;
      await context.push('/chat/$id');
      if (mounted) await _load();
    } catch (e) {
      if (!mounted) return;
      final msg = e is ApiException ? e.message : 'Could not start a chat';
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F6FA),
      body: Column(
        children: [
          Container(
            color: AppColors.primaryNavy,
            padding: EdgeInsets.fromLTRB(20, MediaQuery.of(context).padding.top + 20, 20, 20),
            child: const Row(
              children: [
                Icon(Icons.auto_awesome_rounded, color: Colors.white70, size: 18),
                SizedBox(width: 10),
                Text('AI Assistant', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w700)),
              ],
            ),
          ),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : RefreshIndicator(
                    onRefresh: _load,
                    child: _convos.isEmpty
                        ? ListView(
                            physics: const AlwaysScrollableScrollPhysics(),
                            children: const [
                              SizedBox(height: 80),
                              Icon(Icons.chat_bubble_outline_rounded, size: 56, color: AppColors.textSecondary),
                              SizedBox(height: 16),
                              Center(
                                child: Text('No conversations yet', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600)),
                              ),
                              SizedBox(height: 8),
                              Center(
                                child: Text('Tap + to chat with the AI assistant', style: TextStyle(color: AppColors.textSecondary)),
                              ),
                            ],
                          )
                        : ListView.separated(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.all(16),
                        itemCount: _convos.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (ctx, i) {
                          final c = _convos[i];
                          return Material(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(14),
                            child: InkWell(
                              borderRadius: BorderRadius.circular(14),
                              onTap: () => _openChat(c.id),
                              child: Padding(
                                padding: const EdgeInsets.all(16),
                                child: Row(
                                  children: [
                                    const CircleAvatar(
                                      radius: 22,
                                      backgroundColor: Color(0xFFEEF2FF),
                                      child: Icon(Icons.auto_awesome_rounded, color: AppColors.primaryNavy, size: 20),
                                    ),
                                    const SizedBox(width: 14),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(c.title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                                          if (c.lastMessage.isNotEmpty)
                                            Text(c.lastMessage, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
                                        ],
                                      ),
                                    ),
                                    const Icon(Icons.chevron_right, color: AppColors.textSecondary),
                                  ],
                                ),
                              ),
                            ),
                          );
                        },
                      ),
                  ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _newChat,
        backgroundColor: AppColors.primaryNavy,
        child: const Icon(Icons.add_rounded, color: Colors.white),
      ),
    );
  }
}
