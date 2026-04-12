import { route } from 'quasar/wrappers'
import { createRouter, createWebHashHistory } from 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    requiresAuth?: boolean
    title?: string
    showBackBtn?: boolean
    depth?: number
  }
}

export default route(function () {
  const Router = createRouter({
    scrollBehavior: () => ({ left: 0, top: 0 }),
    history: createWebHashHistory(),
    routes: [
      // ── Public ─────────────────────────────────────────────
      {
        path: '/login',
        name: 'login',
        component: () => import('../pages/LoginPage.vue'),
        meta: { public: true, depth: 0 },
      },

      // ── Authenticated shell (tab bar) ──────────────────────
      {
        path: '/',
        component: () => import('../layouts/MainLayout.vue'),
        children: [
          {
            path: '',
            redirect: '/dashboard',
          },
          {
            path: 'dashboard',
            name: 'dashboard',
            component: () => import('../pages/HomePage.vue'),
            meta: { title: 'Home', depth: 1 },
          },
          {
            path: 'repairs',
            name: 'repairs',
            component: () => import('../pages/RepairsPage.vue'),
            meta: { title: 'Repairs', depth: 1 },
          },
          {
            path: 'settings',
            name: 'settings',
            component: () => import('../pages/SettingsPage.vue'),
            meta: { title: 'Settings', depth: 1 },
          },
        ],
      },

      // ── Full-screen pages (no tab bar) ─────────────────────
      {
        path: '/repairs/chat/:convId',
        name: 'triage-chat',
        component: () => import('../pages/TriageChatPage.vue'),
        meta: { title: 'New Request', showBackBtn: true, depth: 2 },
      },
      {
        path: '/repairs/ticket/:id',
        name: 'ticket-chat',
        component: () => import('../pages/TicketChatPage.vue'),
        meta: { title: 'Repair Chat', showBackBtn: true, depth: 2 },
      },
      {
        path: '/lease',
        name: 'lease',
        component: () => import('../pages/LeasePage.vue'),
        meta: { title: 'My Lease', showBackBtn: true, depth: 2 },
      },
      {
        path: '/signing',
        name: 'signing',
        component: () => import('../pages/LeaseSigningPage.vue'),
        meta: { title: 'Lease & Signing', showBackBtn: true, depth: 2 },
      },

      // ── Catch-all ──────────────────────────────────────────
      {
        path: '/:catchAll(.*)*',
        redirect: '/dashboard',
      },
    ],
  })

  return Router
})
