import { boot } from 'quasar/wrappers'
import { useAuthStore } from '../stores/auth'

export default boot(({ router }) => {
  router.beforeEach(async (to) => {
    const auth = useAuthStore()

    if (to.meta.public) return true
    if (!auth.isAuthenticated) return '/login'

    if (!auth.user) {
      try {
        await auth.fetchMe()
      } catch {
        auth.logout()
        return '/login'
      }
    }

    // Only allow tenant users
    if (auth.user?.role !== 'tenant') {
      await auth.logout()
      return '/login'
    }

    return true
  })
})
