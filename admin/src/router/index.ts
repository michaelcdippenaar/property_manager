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
      path: '/register',
      name: 'register',
      component: () => import('../views/auth/RegisterView.vue'),
      meta: { public: true },
    },
    {
      path: '/forgot-password',
      name: 'forgot-password',
      component: () => import('../views/auth/ForgotPasswordView.vue'),
      meta: { public: true },
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: () => import('../views/auth/ResetPasswordView.vue'),
      meta: { public: true },
    },
    {
      path: '/accept-invite',
      name: 'accept-invite',
      component: () => import('../views/auth/AcceptInviteView.vue'),
      meta: { public: true, allowWhenAuthenticated: true },
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
      meta: { requiresAuth: true, roles: ['agent', 'admin', 'agency_admin', 'estate_agent', 'managing_agent', 'accountant', 'viewer'] },
      children: [
        { path: '', name: 'dashboard', component: () => import('../views/dashboard/DashboardView.vue'), meta: { title: 'Dashboard' } },
        { path: 'agency', name: 'agency-dashboard', component: () => import('../views/dashboard/AgencyDashboardView.vue'), meta: { title: 'Agency Dashboard' } },
        { path: 'agent', name: 'agent-dashboard', component: () => import('../views/dashboard/AgentDashboardView.vue'), meta: { title: 'Agent Dashboard' } },
        { path: 'properties', name: 'properties', component: () => import('../views/properties/PropertiesView.vue'), meta: { title: 'Properties' } },
        { path: 'properties/:id', name: 'property-detail', component: () => import('../views/properties/PropertyDetailView.vue'), meta: { title: 'Property' } },
        { path: 'landlords', name: 'landlords', component: () => import('../views/properties/LandlordsView.vue'), meta: { title: 'Owners' } },
        { path: 'landlords/:id', name: 'landlord-detail', component: () => import('../views/properties/LandlordDetailView.vue'), meta: { title: 'Owner' } },
        { path: 'tenants', name: 'tenants', component: () => import('../views/tenants/TenantsView.vue'), meta: { title: 'Tenants' } },
        { path: 'tenants/:id', name: 'tenant-detail', component: () => import('../views/tenants/TenantDetailView.vue'), meta: { title: 'Tenant' } },
        { path: 'maintenance', redirect: '/maintenance/issues' },
        {
          path: 'maintenance/issues',
          name: 'maintenance-issues',
          component: () => import('../views/maintenance/RequestsView.vue'),
          meta: { title: 'Maintenance Issues' },
        },
        {
          path: 'maintenance/issues/:id',
          name: 'maintenance-detail',
          component: () => import('../views/maintenance/MaintenanceDetailView.vue'),
          meta: { title: 'Maintenance Issue' },
        },
        {
          path: 'maintenance/suppliers',
          name: 'maintenance-suppliers',
          component: () => import('../views/maintenance/SuppliersView.vue'),
          meta: { title: 'Maintenance Suppliers' },
        },
        {
          path: 'maintenance/questions',
          name: 'maintenance-questions',
          component: () => import('../views/maintenance/QuestionsView.vue'),
          meta: { title: 'Maintenance Questions' },
        },
        {
          path: 'suppliers',
          component: () => import('../views/suppliers/SuppliersLayout.vue'),
          children: [
            { path: '', name: 'suppliers', component: () => import('../views/suppliers/DirectoryView.vue'), meta: { title: 'Suppliers' } },
            { path: 'dispatch', name: 'dispatch', component: () => import('../views/suppliers/DispatchView.vue'), meta: { title: 'Dispatch' } },
          ],
        },
        { path: 'leases/overview', name: 'lease-overview', component: () => import('../views/leases/LeaseOverviewView.vue'), meta: { title: 'Lease Overview' } },
        { path: 'leases', name: 'leases', component: () => import('../views/leases/LeasesView.vue'), meta: { title: 'Leases' } },
        { path: 'leases/templates', name: 'lease-templates', component: () => import('../views/leases/LeaseTemplatesView.vue'), meta: { title: 'Lease Templates' } },
        { path: 'leases/status', redirect: '/leases' },
        { path: 'leases/calendar', name: 'lease-calendar', component: () => import('../views/leases/LeaseCalendarView.vue'), meta: { title: 'Lease Calendar' } },
        {
          path: 'leases/templates/:id/edit',
          name: 'lease-template-edit',
          component: () => import('../views/leases/TiptapEditorView.vue'),
          meta: { title: 'Edit Template' },
        },
        {
          path: 'leases/build',
          name: 'lease-builder',
          component: () => import('../views/leases/LeaseBuilderView.vue'),
          meta: { title: 'Build Lease' },
        },
        { path: 'leases/submit', redirect: '/leases' },
        {
          path: 'property-info',
          component: () => import('../views/properties/PropertyInfoSection.vue'),
          children: [
            { path: 'agent', name: 'property-info-agent', component: () => import('../views/properties/PropertyAgentView.vue'), meta: { title: 'Agent Context' } },
            { path: 'skills', name: 'property-info-skills', component: () => import('../views/maintenance/SkillLibraryView.vue'), meta: { title: 'Skill Library' } },
            { path: 'unit-info', name: 'property-info-unit-info', component: () => import('../views/properties/UnitTenantInfoView.vue'), meta: { title: 'Property Info' } },
            { path: 'monitor', name: 'property-info-monitor', component: () => import('../views/setup/AgentMonitorView.vue'), meta: { title: 'Agent Monitor' } },
            { path: '', redirect: { name: 'property-info-agent' } },
          ],
        },
        { path: 'property-agent', redirect: '/property-info/agent' },
        { path: 'unit-tenant-info', redirect: '/property-info/unit-info' },
        { path: 'skills', redirect: '/property-info/skills' },
        // Admin
        { path: 'admin/users', name: 'admin-users', component: () => import('../views/admin/UsersView.vue'), meta: { title: 'Users' } },
        { path: 'admin/agency', name: 'admin-agency', component: () => import('../views/admin/AgencySettingsView.vue'), meta: { title: 'Agency Settings' } },
        // Profile
        { path: 'profile', name: 'profile', component: () => import('../views/auth/ProfileView.vue'), meta: { title: 'Profile' } },
        // Testing Portal
        { path: 'testing', name: 'TestingDashboard', component: () => import('../views/testing/TestingDashboard.vue'), meta: { title: 'Testing Portal' } },
        { path: 'testing/module/:module', name: 'TestingModule', component: () => import('../views/testing/TestingModuleView.vue'), meta: { title: 'Test Module' } },
        { path: 'testing/issues', name: 'TestingIssues', component: () => import('../views/testing/TestingIssuesView.vue'), meta: { title: 'Test Issues' } },
        { path: 'testing/runs', name: 'TestingRuns', component: () => import('../views/testing/TestingRunsView.vue'), meta: { title: 'Test Runs' } },
        { path: 'testing/selfcheck', name: 'TestingSelfCheck', component: () => import('../views/testing/TestingSelfCheckView.vue'), meta: { title: 'Self Check' } },
        { path: 'admin/devops', name: 'admin-devops', component: () => import('../views/admin/DevOpsView.vue'), meta: { title: 'DevOps' } },
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
        { path: 'leases', name: 'owner-lease-builder', component: () => import('../views/leases/LeaseBuilderView.vue') },
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

  // Redirect `/` to role-specific dashboard
  if (to.path === '/' && to.name === 'dashboard' && auth.homeRoute !== '/') {
    return { path: auth.homeRoute, replace: true }
  }
})

router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  document.title = title ? `${title} · Klikk` : 'Klikk'
})

export default router
