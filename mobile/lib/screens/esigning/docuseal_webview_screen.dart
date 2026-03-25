import 'dart:async';

import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../../services/esigning_service.dart';
import '../../theme/app_colors.dart';

/// Loads DocuSeal [embedUrl] (per-signer URL from the API) and polls submission status.
class DocusealWebViewScreen extends StatefulWidget {
  const DocusealWebViewScreen({
    super.key,
    required this.embedUrl,
    required this.submissionId,
  });

  final String embedUrl;
  final int submissionId;

  @override
  State<DocusealWebViewScreen> createState() => _DocusealWebViewScreenState();
}

class _DocusealWebViewScreenState extends State<DocusealWebViewScreen> {
  late final WebViewController _controller;
  Timer? _poll;
  var _pageLoading = true;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) => setState(() => _pageLoading = true),
          onPageFinished: (_) => setState(() => _pageLoading = false),
        ),
      )
      ..loadRequest(Uri.parse(widget.embedUrl));

    _poll = Timer.periodic(const Duration(seconds: 10), (_) => _checkStatus());
  }

  Future<void> _checkStatus() async {
    try {
      final s = await esigningService.getSubmission(widget.submissionId);
      if (!mounted) return;
      if (s.status == 'completed' || s.status == 'declined') {
        Navigator.of(context).pop(true);
      }
    } catch (_) {
      // Keep WebView usable even if polling fails briefly.
    }
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('Sign document'),
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: Colors.white,
      ),
      body: Stack(
        children: [
          WebViewWidget(controller: _controller),
          if (_pageLoading)
            const LinearProgressIndicator(minHeight: 2),
        ],
      ),
    );
  }
}
