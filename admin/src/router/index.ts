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
      path: '/',
      component: () => import('../components/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('../views/dashboard/DashboardView.vue'),
        },
        {
          path: 'properties',
          name: 'properties',
          component: () => import('../views/properties/PropertiesView.vue'),
        },
        {
          path: 'tenants',
          name: 'tenants',
          component: () => import('../views/tenants/TenantsView.vue'),
        },
        { path: 'maintenance', redirect: '/maintenance/issues' },
        {
          path: 'maintenance/issues',
          name: 'maintenance-issues',
          component: () => import('../views/maintenance/MaintenanceView.vue'),
        },
        {
          path: 'maintenance/suppliers',
          name: 'maintenance-suppliers',
          component: () => import('../views/maintenance/SuppliersView.vue'),
        },
        {
          path: 'maintenance/ai-questions',
          name: 'maintenance-ai-questions',
          component: () => import('../views/maintenance/AIQuestionsView.vue'),
        },
        {
          path: 'maintenance/ai-sandbox',
          name: 'maintenance-ai-sandbox',
          component: () => import('../views/maintenance/AISandboxView.vue'),
        },
        {
          path: 'leases',
          name: 'leases',
          component: () => import('../views/leases/LeasesView.vue'),
        },
        {
          path: 'leases/calendar',
          name: 'leases-calendar',
          component: () => import('../views/leases/LeaseCalendarView.vue'),
        },
        {
          path: 'property-info',
          component: () => import('../views/properties/PropertyInfoSection.vue'),
          children: [
            {
              path: 'agent',
              name: 'property-info-agent',
              component: () => import('../views/properties/PropertyAgentView.vue'),
            },
            {
              path: 'skills',
              name: 'property-info-skills',
              component: () => import('../views/maintenance/SkillLibraryView.vue'),
            },
            {
              path: 'unit-info',
              name: 'property-info-unit-info',
              component: () => import('../views/properties/UnitTenantInfoView.vue'),
            },
            { path: '', redirect: { name: 'property-info-agent' } },
          ],
        },
        { path: 'property-agent', redirect: '/property-info/agent' },
        { path: 'unit-tenant-info', redirect: '/property-info/unit-info' },
        { path: 'skills', redirect: '/property-info/skills' },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login' }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'dashboard' }
  }
})

export default router
