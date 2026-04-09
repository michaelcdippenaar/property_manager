<template>
  <div class="h-dvh flex flex-col items-center justify-center bg-navy">
    <!-- Logo mark -->
    <div class="mb-8 flex flex-col items-center gap-4">
      <div class="w-20 h-20 rounded-3xl bg-white/10 flex items-center justify-center">
        <span class="text-white text-4xl font-bold tracking-tight">K</span>
      </div>
      <div class="text-center">
        <h1 class="text-white text-2xl font-bold tracking-tight">Klikk</h1>
        <p class="text-white/50 text-sm mt-1">Tenant Portal</p>
      </div>
    </div>

    <!-- Spinner -->
    <Loader2 :size="24" class="text-white/40 animate-spin" />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { Loader2 } from 'lucide-vue-next'

const router = useRouter()
const auth = useAuthStore()

onMounted(async () => {
  if (!auth.isAuthenticated) {
    router.replace({ name: 'login' })
    return
  }

  try {
    await auth.fetchMe()
    router.replace({ name: 'home' })
  } catch {
    auth.logout()
    router.replace({ name: 'login' })
  }
})
</script>
