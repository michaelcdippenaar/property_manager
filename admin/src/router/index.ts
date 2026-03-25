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
    {
      path: '/sign/:token',
      name: 'public-sign',
      component: () => import('../views/signing/PublicSignView.vue'),
      meta: { public: true, allowWhenAuthenticated: true },
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
        { path: 'maintenance', redirect: '/maintenance/issues' },
        {
          path: 'maintenance/issues',
          name: 'maintenance-issues',
          component: () => import('../views/maintenance/RequestsView.vue'),
        },
        {
          path: 'maintenance/suppliers',
          name: 'maintenance-suppliers',
          component: () => import('../views/maintenance/SuppliersView.vue'),
        },
        {
          path: 'suppliers',
          component: () => import('../views/suppliers/SuppliersLayout.vue'),
          children: [
            { path: '', name: 'suppliers', component: () => import('../views/suppliers/DirectoryView.vue') },
            { path: 'dispatch', name: 'dispatch', component: () => import('../views/suppliers/DispatchView.vue') },
          ],
        },
        { path: 'leases', name: 'leases', component: () => import('../views/leases/LeasesView.vue') },
        { path: 'leases/templates', name: 'lease-templates', component: () => import('../views/leases/LeaseTemplatesView.vue') },
        { path: 'leases/calendar', name: 'lease-calendar', component: () => import('../views/leases/LeaseCalendarView.vue') },
        {
          path: 'leases/templates/:id/edit',
          name: 'lease-template-edit',
          component: () => import('../views/leases/TemplateEditorView.vue'),
        },
        {
          path: 'leases/build',
          name: 'lease-builder',
          component: () => import('../views/leases/LeaseBuilderView.vue'),
        },
        {
          path: 'leases/submit',
          name: 'lease-submit',
          component: () => import('../views/leases/SubmitLeaseView.vue'),
        },
        {
          path: 'property-info',
          component: () => import('../views/properties/PropertyInfoSection.vue'),
          children: [
            { path: 'agent', name: 'property-info-agent', component: () => import('../views/properties/PropertyAgentView.vue') },
            { path: 'skills', name: 'property-info-skills', component: () => import('../views/maintenance/SkillLibraryView.vue') },
            { path: 'unit-info', name: 'property-info-unit-info', component: () => import('../views/properties/UnitTenantInfoView.vue') },
            { path: '', redirect: { name: 'property-info-agent' } },
          ],
        },
        { path: 'property-agent', redirect: '/property-info/agent' },
        { path: 'unit-tenant-info', redirect: '/property-info/unit-info' },
        { path: 'skills', redirect: '/property-info/skills' },
      ],
    },

    // ── Supplier layout ──
    {
      path: '/jobs',
      component: () => import('../components/SupplierLayout.vue'),
      meta: { requiresAuth: true, roles: ['supplier'] },
      children: [
        { path: '', name: 'supplier-jobs', component: () => import('../views/supplier/JobsListView.vue') },
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

  // Public routes (e.g. login, passwordless /sign/:token)
  if (to.meta.public) {
    const allowWhenAuthed = to.meta.allowWhenAuthenticated === true
    if (auth.isAuthenticated && !allowWhenAuthed) {
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
