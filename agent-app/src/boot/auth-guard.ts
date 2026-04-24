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

    if (!auth.canAccessAgentApp) {
      await auth.logout()
      return '/login'
    }

    // Optional 2FA setup pending (owner role, DEC-018): redirect to enroll view unless already there
    if (auth.suggestTwoFASetup && to.name !== '2fa-enroll') {
      return { name: '2fa-enroll', query: { optional: '1' } }
    }

    return true
  })
})
