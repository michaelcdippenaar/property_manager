import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // ── Auth (depth 0) ──────────────────────────────────────────────
    {
      path: '/',
      name: 'splash',
      component: () => import('../views/auth/SplashView.vue'),
      meta: { public: true, depth: 0 },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/auth/LoginView.vue'),
      meta: { public: true, depth: 0 },
    },
    {
      path: '/2fa/challenge',
      name: '2fa-challenge',
      component: () => import('../views/auth/TwoFAChallengeView.vue'),
      meta: { public: true, depth: 0 },
    },
    {
      path: '/2fa/enroll',
      name: '2fa-enroll',
      component: () => import('../views/auth/TwoFAEnrollView.vue'),
      meta: { public: true, depth: 0 },
    },

    // ── Welcome / onboarding screen (full-screen, depth 1) ─────────
    {
      path: '/welcome',
      name: 'welcome',
      component: () => import('../views/home/WelcomeView.vue'),
      meta: { requiresAuth: true, depth: 1 },
    },

    // ── Main shell (depth 1) ────────────────────────────────────────
    {
      path: '/home',
      component: () => import('../views/shell/AppShell.vue'),
      meta: { requiresAuth: true, depth: 1 },
      children: [
        { path: '', redirect: '/home/dashboard' },
        {
          path: 'dashboard',
          name: 'home',
          component: () => import('../views/home/HomeView.vue'),
          meta: { requiresAuth: true, depth: 1 },
        },
        {
          path: 'issues',
          name: 'issues',
          component: () => import('../views/issues/IssuesView.vue'),
          meta: { requiresAuth: true, depth: 1 },
        },
        {
          path: 'lease',
          name: 'lease',
          component: () => import('../views/leases/LeaseView.vue'),
          meta: { requiresAuth: true, depth: 1 },
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('../views/settings/SettingsView.vue'),
          meta: { requiresAuth: true, depth: 1 },
        },
      ],
    },

    // ── Full-screen views (depth 2) ─────────────────────────────────
    {
      path: '/issues/report',
      name: 'report-issue',
      component: () => import('../views/issues/ReportIssueView.vue'),
      meta: { requiresAuth: true, depth: 2 },
    },
    {
      path: '/issues/:id',
      name: 'issue-detail',
      component: () => import('../views/issues/IssueDetailView.vue'),
      meta: { requiresAuth: true, depth: 2 },
    },
    {
      path: '/chat',
      name: 'chat-list',
      component: () => import('../views/chat/ChatListView.vue'),
      meta: { requiresAuth: true, depth: 2 },
    },
    {
      path: '/chat/:id',
      name: 'chat-detail',
      component: () => import('../views/chat/ChatDetailView.vue'),
      meta: { requiresAuth: true, depth: 2 },
    },
    {
      path: '/signing',
      name: 'signing',
      component: () => import('../views/esigning/LeaseSigningView.vue'),
      meta: { requiresAuth: true, depth: 2 },
    },

    // Catch-all
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (to.meta.public) return

  if (!auth.isAuthenticated) {
    return { name: 'login' }
  }

  if (!auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      auth.logout()
      return { name: 'login' }
    }
  }

  // Redirect tenant to welcome screen if they haven't dismissed it yet.
  // Uses server-side seen_welcome_at (durable across tabs and browser restarts).
  if (to.name === 'home' && auth.user?.role === 'tenant' && !auth.user?.seen_welcome_at) {
    return { name: 'welcome' }
  }
})

export default router
