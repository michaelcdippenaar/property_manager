import { route } from 'quasar/wrappers'
import {
  createMemoryHistory,
  createRouter,
  createWebHashHistory,
  createWebHistory,
} from 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    requiresAuth?: boolean
    title?: string
    showBackBtn?: boolean
    showFab?: boolean
  }
}

export default route(function (/* { store, ssrContext } */) {
  const createHistory = process.env.SERVER
    ? createMemoryHistory
    : process.env.VUE_ROUTER_MODE === 'history'
      ? createWebHistory
      : createWebHashHistory

  const router = createRouter({
    scrollBehavior: () => ({ left: 0, top: 0 }),
    history: createHistory(process.env.VUE_ROUTER_BASE),
    routes: [
      {
        path: '/login',
        name: 'login',
        component: () => import('../pages/LoginPage.vue'),
        meta: { public: true, title: 'Sign In' },
      },
      {
        path: '/2fa/challenge',
        name: '2fa-challenge',
        component: () => import('../pages/TwoFAChallengePage.vue'),
        meta: { public: true, title: '2FA Verification' },
      },
      {
        path: '/2fa/enroll',
        name: '2fa-enroll',
        component: () => import('../pages/TwoFAEnrollPage.vue'),
        meta: { public: true, title: 'Set Up 2FA' },
      },
      {
        path: '/',
        component: () => import('../layouts/MainLayout.vue'),
        meta: { requiresAuth: true },
        children: [
          {
            path: '',
            redirect: '/today',
          },
          {
            path: 'today',
            name: 'today',
            component: () => import('../pages/TodayPage.vue'),
            meta: { title: 'Today', showFab: false },
          },
          {
            path: 'pipeline',
            name: 'pipeline',
            component: () => import('../pages/PipelinePage.vue'),
            meta: { title: 'Pipeline', showFab: true },
          },
          {
            path: 'people',
            name: 'people',
            component: () => import('../pages/PeoplePage.vue'),
            meta: { title: 'People', showFab: false },
          },
          {
            path: 'inbox',
            name: 'inbox',
            component: () => import('../pages/InboxPage.vue'),
            meta: { title: 'Inbox', showFab: false },
          },
          {
            path: 'dashboard',
            name: 'dashboard',
            component: () => import('../pages/DashboardPage.vue'),
            meta: { title: 'Dashboard', showFab: false },
          },
          {
            path: 'properties',
            name: 'properties',
            component: () => import('../pages/PropertiesPage.vue'),
            meta: { title: 'Properties', showFab: false },
          },
          {
            path: 'properties/:id',
            name: 'property-detail',
            component: () => import('../pages/PropertyDetailPage.vue'),
            props: true,
            meta: { title: 'Property', showBackBtn: true, showFab: true },
          },
          {
            path: 'properties/:propertyId/leases/new',
            name: 'create-direct-lease',
            component: () => import('../pages/CreateDirectLeasePage.vue'),
            props: (route) => ({ propertyId: Number(route.params.propertyId) }),
            meta: { title: 'Create Lease', showBackBtn: true, showFab: false },
          },
          {
            path: 'viewings',
            name: 'viewings',
            component: () => import('../pages/ViewingsPage.vue'),
            meta: { title: 'Viewings', showFab: true },
          },
          {
            path: 'leases',
            name: 'leases',
            component: () => import('../pages/LeasesPage.vue'),
            meta: { title: 'Leases', showFab: false },
          },
          {
            path: 'calendar',
            name: 'calendar',
            component: () => import('../pages/ViewingCalendarPage.vue'),
            meta: { title: 'Calendar', showFab: true },
          },
          {
            path: 'maintenance',
            name: 'maintenance',
            component: () => import('../pages/MaintenancePage.vue'),
            meta: { title: 'Maintenance', showFab: false },
          },
          {
            path: 'settings',
            name: 'settings',
            component: () => import('../pages/SettingsPage.vue'),
            meta: { title: 'Settings', showFab: false },
          },
          {
            path: 'settings/notifications',
            name: 'notification-preferences',
            component: () => import('../pages/NotificationPreferencesPage.vue'),
            meta: { title: 'Notifications', showBackBtn: true, showFab: false },
          },
          {
            path: 'viewings/new',
            name: 'book-viewing',
            component: () => import('../pages/BookViewingPage.vue'),
            props: (route) => ({
              prePropertyId: route.query.property ? Number(route.query.property) : undefined,
              preUnitId:     route.query.unit     ? Number(route.query.unit)     : undefined,
            }),
            meta: { title: 'Book Viewing', showBackBtn: true, showFab: false },
          },
          {
            path: 'viewings/:id',
            name: 'viewing-detail',
            component: () => import('../pages/ViewingDetailPage.vue'),
            props: (route) => ({ id: Number(route.params.id) }),
            meta: { title: 'Viewing', showBackBtn: true, showFab: false },
          },
          {
            path: 'viewings/:id/lease',
            name: 'create-lease',
            component: () => import('../pages/CreateLeasePage.vue'),
            props: (route) => ({ viewingId: Number(route.params.id) }),
            meta: { title: 'Create Lease', showBackBtn: true, showFab: false },
          },
        ],
      },
      // Catch-all
      {
        path: '/:catchAll(.*)*',
        redirect: '/',
      },
    ],
  })

  return router
})
