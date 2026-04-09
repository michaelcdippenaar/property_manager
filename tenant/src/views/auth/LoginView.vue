<template>
  <div class="h-dvh flex flex-col bg-surface overflow-y-auto">
    <!-- Header -->
    <div class="bg-navy px-6 pt-16 pb-10 flex flex-col items-center" style="padding-top: calc(4rem + env(safe-area-inset-top))">
      <div class="w-16 h-16 rounded-2xl bg-white/10 flex items-center justify-center mb-4">
        <span class="text-white text-3xl font-bold">K</span>
      </div>
      <h1 class="text-white text-2xl font-bold">Welcome back</h1>
      <p class="text-white/60 text-sm mt-1">Sign in to your tenant account</p>
    </div>

    <!-- Form -->
    <div class="flex-1 px-5 pt-8 pb-8">
      <div class="list-section">
        <div class="list-row">
          <span class="text-sm text-gray-500 w-20 flex-shrink-0">Email</span>
          <input
            v-model="email"
            type="email"
            placeholder="your@email.com"
            autocomplete="email"
            class="flex-1 text-sm text-gray-900 outline-none bg-transparent"
            @keyup.enter="focusPassword"
          />
        </div>
        <div class="list-row">
          <span class="text-sm text-gray-500 w-20 flex-shrink-0">Password</span>
          <input
            ref="passwordRef"
            v-model="password"
            type="password"
            placeholder="••••••••"
            autocomplete="current-password"
            class="flex-1 text-sm text-gray-900 outline-none bg-transparent"
            @keyup.enter="handleLogin"
          />
        </div>
      </div>

      <!-- Error -->
      <p v-if="errorMsg" class="text-danger-600 text-sm text-center mb-4 px-2">{{ errorMsg }}</p>

      <!-- Sign in button -->
      <button
        class="w-full py-4 bg-navy text-white font-semibold rounded-2xl text-base ripple touchable active:scale-[0.98]"
        :disabled="loading"
        @click="handleLogin"
      >
        <span v-if="!loading">Sign In</span>
        <Loader2 v-else :size="20" class="animate-spin mx-auto" />
      </button>
    </div>

    <!-- Footer -->
    <div class="pb-10 text-center safe-bottom">
      <p class="text-xs text-gray-400">Klikk Tenant Portal &copy; {{ new Date().getFullYear() }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { Loader2 } from 'lucide-vue-next'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')
const passwordRef = ref<HTMLInputElement | null>(null)

function focusPassword() {
  passwordRef.value?.focus()
}

async function handleLogin() {
  if (!email.value || !password.value) {
    errorMsg.value = 'Please enter your email and password.'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    await auth.login(email.value.trim(), password.value)
    router.replace({ name: 'home' })
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.detail || 'Invalid email or password.'
  } finally {
    loading.value = false
  }
}
</script>
