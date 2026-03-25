import 'package:go_router/go_router.dart';
import '../screens/auth/splash_screen.dart';
import '../screens/auth/login_email_screen.dart';
import '../screens/auth/login_mobile_screen.dart';
import '../screens/auth/otp_screen.dart';
import '../screens/auth/signup_screen.dart';
import '../screens/home/dashboard_screen.dart';
import '../screens/home/issues_screen.dart';

final appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(
      path: '/',
      builder: (context, state) => const SplashScreen(),
    ),
    GoRoute(
      path: '/login',
      builder: (context, state) => const LoginEmailScreen(),
    ),
    GoRoute(
      path: '/login/mobile',
      builder: (context, state) => const LoginMobileScreen(),
    ),
    GoRoute(
      path: '/login/otp',
      builder: (context, state) => OtpScreen(
        mode: OtpMode.login,
        phone: state.extra as String? ?? '',
      ),
    ),
    GoRoute(
      path: '/signup',
      builder: (context, state) => const SignupScreen(),
    ),
    GoRoute(
      path: '/signup/otp',
      builder: (context, state) => OtpScreen(
        mode: OtpMode.signup,
        phone: state.extra as String? ?? '',
      ),
    ),
    GoRoute(
      path: '/dashboard',
      builder: (context, state) => const DashboardScreen(),
    ),
    GoRoute(
      path: '/issues',
      builder: (context, state) => const IssuesScreen(),
    ),
  ],
);
