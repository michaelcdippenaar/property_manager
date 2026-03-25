import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:go_router/go_router.dart';

class _Stage {
  const _Stage({required this.icon, required this.color, required this.title, required this.subtitle, required this.step});
  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
  final int step;
}

const _stages = [
  _Stage(icon: Icons.search_rounded, color: Color(0xFF60A5FA), step: 1, title: 'Find Your Home', subtitle: 'Browse available properties and book a viewing — all from your phone.'),
  _Stage(icon: Icons.assignment_turned_in_rounded, color: Color(0xFFA78BFA), step: 2, title: 'Apply Online', subtitle: 'Submit your application and credit check without printing a single page.'),
  _Stage(icon: Icons.draw_rounded, color: Color(0xFFEC4899), step: 3, title: 'Sign Your Lease', subtitle: 'Review every clause and sign digitally. Your lease is stored safely forever.'),
  _Stage(icon: Icons.vpn_key_rounded, color: Color(0xFF34D399), step: 4, title: 'Keys & Move In', subtitle: 'Your agent walks you through the ingoing inspection. Everything is on record.'),
  _Stage(icon: Icons.auto_awesome_rounded, color: Color(0xFFFBBF24), step: 5, title: '24/7 AI Support', subtitle: 'Log repairs, ask about your WiFi code, or report an emergency — AI is always on.'),
  _Stage(icon: Icons.event_available_rounded, color: Color(0xFF38BDF8), step: 6, title: 'Renewal Reminders', subtitle: 'Get notified before your lease expires. Renew, renegotiate, or serve notice in minutes.'),
  _Stage(icon: Icons.inventory_2_rounded, color: Color(0xFFF97316), step: 7, title: 'Clean Exit', subtitle: 'Outgoing inspection, deposit reconciliation, and final settlement. Transparent and fair.'),
];

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});
  @override State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> with TickerProviderStateMixin {
  final _pageController = PageController();
  int _current = 0;
  Timer? _timer;

  late AnimationController _iconCtrl;
  late AnimationController _textCtrl;
  late Animation<double> _iconScale;
  late Animation<double> _iconOpacity;
  late Animation<Offset> _textSlide;
  late Animation<double> _textOpacity;

  @override
  void initState() {
    super.initState();
    _iconCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 700));
    _textCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 500));
    _iconScale = Tween<double>(begin: 0.4, end: 1.0).animate(CurvedAnimation(parent: _iconCtrl, curve: Curves.elasticOut));
    _iconOpacity = Tween<double>(begin: 0.0, end: 1.0).animate(CurvedAnimation(parent: _iconCtrl, curve: const Interval(0.0, 0.4, curve: Curves.easeIn)));
    _textSlide = Tween<Offset>(begin: const Offset(0, 0.3), end: Offset.zero).animate(CurvedAnimation(parent: _textCtrl, curve: Curves.easeOut));
    _textOpacity = Tween<double>(begin: 0.0, end: 1.0).animate(CurvedAnimation(parent: _textCtrl, curve: const Interval(0.0, 0.7, curve: Curves.easeIn)));
    _play();
    _schedule();
  }

  void _play() {
    _iconCtrl.forward(from: 0);
    Future.delayed(const Duration(milliseconds: 120), () { if (mounted) _textCtrl.forward(from: 0); });
  }

  void _schedule() {
    _timer?.cancel();
    if (_current < _stages.length - 1) {
      _timer = Timer(const Duration(seconds: 4), () {
        if (!mounted) return;
        _pageController.nextPage(duration: const Duration(milliseconds: 400), curve: Curves.easeInOut);
      });
    }
  }

  void _onPageChanged(int p) {
    setState(() => _current = p);
    _play();
    _schedule();
  }

  Future<void> _finish() async {
    _timer?.cancel();
    const storage = FlutterSecureStorage();
    await storage.write(key: 'onboarding_seen', value: 'true');
    if (mounted) context.go('/login');
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pageController.dispose();
    _iconCtrl.dispose();
    _textCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final stage = _stages[_current];
    final isLast = _current == _stages.length - 1;

    return Scaffold(
      backgroundColor: const Color(0xFF07111F),
      body: Stack(
        children: [
          // Radial glow
          Positioned.fill(
            child: AnimatedBuilder(
              animation: _iconCtrl,
              builder: (_, __) => CustomPaint(
                painter: _GlowPainter(color: stage.color.withOpacity(0.2), scale: _iconCtrl.value),
              ),
            ),
          ),
          SafeArea(
            child: Column(
              children: [
                Align(
                  alignment: Alignment.topRight,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(0, 12, 20, 0),
                    child: TextButton(
                      onPressed: _finish,
                      child: const Text('Skip', style: TextStyle(color: Colors.white54, fontSize: 14, fontWeight: FontWeight.w500)),
                    ),
                  ),
                ),
                const Spacer(flex: 2),
                // Icon
                AnimatedBuilder(
                  animation: _iconCtrl,
                  builder: (_, __) => Opacity(
                    opacity: _iconOpacity.value,
                    child: Transform.scale(
                      scale: _iconScale.value,
                      child: Container(
                        width: 130, height: 130,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: const Color(0xFF0D1E30),
                          border: Border.all(color: stage.color.withOpacity(0.25), width: 1.5),
                          boxShadow: [BoxShadow(color: stage.color.withOpacity(0.2), blurRadius: 40, spreadRadius: 8)],
                        ),
                        child: Icon(stage.icon, color: stage.color, size: 56),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 48),
                // Step badge + text
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 36),
                  child: Column(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                        decoration: BoxDecoration(
                          color: stage.color.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: stage.color.withOpacity(0.3)),
                        ),
                        child: Text(
                          '${stage.step.toString().padLeft(2, '0')} / ${_stages.length.toString().padLeft(2, '0')}',
                          style: TextStyle(color: stage.color, fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 1.5),
                        ),
                      ),
                      const SizedBox(height: 16),
                      SlideTransition(
                        position: _textSlide,
                        child: FadeTransition(
                          opacity: _textOpacity,
                          child: Text(stage.title, textAlign: TextAlign.center,
                            style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w700, height: 1.2)),
                        ),
                      ),
                      const SizedBox(height: 12),
                      FadeTransition(
                        opacity: _textOpacity,
                        child: Text(stage.subtitle, textAlign: TextAlign.center,
                          style: const TextStyle(color: Colors.white60, fontSize: 15, height: 1.6)),
                      ),
                    ],
                  ),
                ),
                const Spacer(flex: 3),
                // Dots
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: List.generate(_stages.length, (i) {
                    final active = i == _current;
                    return AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      curve: Curves.easeInOut,
                      margin: const EdgeInsets.symmetric(horizontal: 4),
                      width: active ? 24 : 7, height: 7,
                      decoration: BoxDecoration(
                        color: active ? stage.color : Colors.white24,
                        borderRadius: BorderRadius.circular(4),
                      ),
                    );
                  }),
                ),
                const SizedBox(height: 32),
                // CTA
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 36),
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 300),
                    child: SizedBox(
                      key: ValueKey(isLast),
                      width: double.infinity, height: 54,
                      child: ElevatedButton(
                        onPressed: isLast ? _finish : () => _pageController.nextPage(duration: const Duration(milliseconds: 400), curve: Curves.easeInOut),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: stage.color,
                          foregroundColor: Colors.white,
                          elevation: 0,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
                        ),
                        child: Text(isLast ? 'Get Started' : 'Next', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 40),
              ],
            ),
          ),
          // Swipeable overlay
          PageView.builder(
            controller: _pageController,
            onPageChanged: _onPageChanged,
            itemCount: _stages.length,
            itemBuilder: (_, __) => const SizedBox.expand(),
          ),
        ],
      ),
    );
  }
}

class _GlowPainter extends CustomPainter {
  const _GlowPainter({required this.color, required this.scale});
  final Color color;
  final double scale;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height * 0.38);
    final radius = size.width * 0.7 * scale;
    final paint = Paint()
      ..shader = RadialGradient(colors: [color, Colors.transparent]).createShader(
          Rect.fromCircle(center: center, radius: radius));
    canvas.drawCircle(center, radius, paint);
  }

  @override
  bool shouldRepaint(_GlowPainter old) => old.color != color || old.scale != scale;
}
