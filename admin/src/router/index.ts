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
        {
          path: 'maintenance',
          name: 'maintenance',
          component: () => import('../views/maintenance/MaintenanceView.vue'),
        },
        {
          path: 'leases',
          name: 'leases',
          component: () => import('../views/leases/LeasesView.vue'),
        },
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
