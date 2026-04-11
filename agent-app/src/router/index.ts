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
        path: '/',
        component: () => import('../layouts/MainLayout.vue'),
        meta: { requiresAuth: true },
        children: [
          {
            path: '',
            redirect: '/dashboard',
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
            path: 'settings',
            name: 'settings',
            component: () => import('../pages/SettingsPage.vue'),
            meta: { title: 'Settings', showFab: false },
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
