import 'package:go_router/go_router.dart';
import '../screens/auth/splash_screen.dart';
import '../screens/auth/onboarding_screen.dart';
import '../screens/auth/login_email_screen.dart';
import '../screens/auth/login_mobile_screen.dart';
import '../screens/auth/otp_screen.dart';
import '../screens/auth/signup_screen.dart';
import '../screens/shell/app_shell.dart';
import '../screens/issues/issue_detail_screen.dart';
import '../screens/issues/report_issue_screen.dart';
import '../screens/chat/chat_list_screen.dart';
import '../screens/chat/chat_detail_screen.dart';
import '../screens/esigning/docuseal_webview_screen.dart';
import '../screens/esigning/lease_signing_screen.dart';

final appRouter = GoRouter(
  initialLocation: '/',
  redirect: (context, state) {
    if (state.matchedLocation == '/dashboard') return '/home';
    return null;
  },
  routes: [
    GoRoute(path: '/', builder: (ctx, st) => const SplashScreen()),
    GoRoute(path: '/onboarding', builder: (ctx, st) => const OnboardingScreen()),
    GoRoute(path: '/login', builder: (ctx, st) => const LoginEmailScreen()),
    GoRoute(path: '/login/mobile', builder: (ctx, st) => const LoginMobileScreen()),
    GoRoute(path: '/login/otp', builder: (ctx, st) => OtpScreen(mode: OtpMode.login, phone: st.extra as String? ?? '')),
    GoRoute(path: '/signup', builder: (ctx, st) => const SignupScreen()),
    GoRoute(path: '/signup/otp', builder: (ctx, st) => OtpScreen(mode: OtpMode.signup, phone: st.extra as String? ?? '')),
    GoRoute(path: '/home', builder: (ctx, st) => const AppShell()),
    GoRoute(
      path: '/issues/report',
      builder: (ctx, st) {
        final x = st.extra;
        return ReportIssueScreen(
          initialDraft: x is Map<String, dynamic> ? x : null,
        );
      },
    ),
    GoRoute(
      path: '/issues/:id',
      builder: (ctx, st) {
        final id = int.tryParse(st.pathParameters['id'] ?? '');
        if (id == null) return const SplashScreen();
        return IssueDetailScreen(issueId: id);
      },
    ),
    GoRoute(
      path: '/chat',
      builder: (ctx, st) => const ChatListScreen(),
    ),
    GoRoute(
      path: '/chat/:id',
      builder: (ctx, st) {
        final id = int.tryParse(st.pathParameters['id'] ?? '') ?? 0;
        return ChatDetailScreen(conversationId: id);
      },
    ),
    GoRoute(
      path: '/signing',
      builder: (ctx, st) => const LeaseSigningScreen(),
    ),
    GoRoute(
      path: '/signing/web',
      builder: (ctx, st) {
        final extra = st.extra;
        if (extra is! Map) {
          return const LeaseSigningScreen();
        }
        final url = extra['embedUrl'] as String?;
        final sid = extra['submissionId'] as int?;
        if (url == null || sid == null) {
          return const LeaseSigningScreen();
        }
        return DocusealWebViewScreen(embedUrl: url, submissionId: sid);
      },
    ),
  ],
);
