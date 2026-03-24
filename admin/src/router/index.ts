import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/auth/LoginView.vue'),
      meta: { public: true },
    },

    // ── Agent / Admin layout ──
    {
      path: '/',
      component: () => import('../components/AppLayout.vue'),
      meta: { requiresAuth: true, roles: ['agent', 'admin'] },
      children: [
        { path: '', name: 'dashboard', component: () => import('../views/dashboard/DashboardView.vue') },
        { path: 'properties', name: 'properties', component: () => import('../views/properties/PropertiesView.vue') },
        { path: 'tenants', name: 'tenants', component: () => import('../views/tenants/TenantsView.vue') },
        { path: 'maintenance', name: 'maintenance', component: () => import('../views/maintenance/RequestsView.vue') },
        {
          path: 'suppliers',
          component: () => import('../views/suppliers/SuppliersLayout.vue'),
          children: [
            { path: '', name: 'suppliers', component: () => import('../views/suppliers/DirectoryView.vue') },
            { path: 'dispatch', name: 'dispatch', component: () => import('../views/suppliers/DispatchView.vue') },
          ],
        },
        { path: 'leases', name: 'leases', component: () => import('../views/leases/LeasesView.vue') },
      ],
    },

    // ── Supplier layout ──
    {
      path: '/jobs',
      component: () => import('../components/SupplierLayout.vue'),
      meta: { requiresAuth: true, roles: ['supplier'] },
      children: [
        { path: '', name: 'supplier-jobs', component: () => import('../views/supplier/JobsListView.vue') },
        { path: ':id', name: 'supplier-job-detail', component: () => import('../views/supplier/JobsListView.vue') },
      ],
    },
    {
      path: '/calendar',
      component: () => import('../components/SupplierLayout.vue'),
      meta: { requiresAuth: true, roles: ['supplier'] },
      children: [
        { path: '', name: 'supplier-calendar', component: () => import('../views/supplier/CalendarView.vue') },
      ],
    },
    {
      path: '/profile',
      component: () => import('../components/SupplierLayout.vue'),
      meta: { requiresAuth: true, roles: ['supplier'] },
      children: [
        { path: '', name: 'supplier-profile', component: () => import('../views/supplier/SupplierProfileView.vue') },
      ],
    },

    // ── Owner layout ──
    {
      path: '/owner',
      component: () => import('../components/OwnerLayout.vue'),
      meta: { requiresAuth: true, roles: ['owner'] },
      children: [
        { path: '', name: 'owner-dashboard', component: () => import('../views/owner/OwnerDashboard.vue') },
        { path: 'properties', name: 'owner-properties', component: () => import('../views/owner/OwnerPropertiesView.vue') },
      ],
    },

    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  // Public routes
  if (to.meta.public) {
    if (auth.isAuthenticated) {
      // Fetch user data if we don't have it yet
      if (!auth.user) {
        try { await auth.fetchMe() } catch { auth.logout(); return { name: 'login' } }
      }
      return { path: auth.homeRoute }
    }
    return
  }

  // Not authenticated
  if (!auth.isAuthenticated) {
    return { name: 'login' }
  }

  // Fetch user if needed
  if (!auth.user) {
    try { await auth.fetchMe() } catch { auth.logout(); return { name: 'login' } }
  }

  // Role-based access
  const allowedRoles = to.meta.roles as string[] | undefined
  if (allowedRoles && !allowedRoles.includes(auth.user?.role ?? '')) {
    return { path: auth.homeRoute }
  }
})

export default router
