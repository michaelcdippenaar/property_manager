<!--
  ChoosePortalView — portal chooser shown to sys admins on login.

  Sys admins (role === 'admin') can jump between the main Admin Console
  and the Agent Operations Portal. Styling mirrors RegisterView step 1
  (two-card selector + Continue button).

  Non-admin roles should never land here — route guard sends them to
  auth.homeRoute instead.
-->
<template>
  <div class="min-h-screen bg-lavender flex items-center justify-center px-4">
    <div class="w-full max-w-md">

      <!-- Logo -->
      <div class="text-center mb-8">
        <span class="text-3xl font-bold text-navy">Klikk<span class="text-pink-brand">.</span></span>
        <p class="text-gray-500 text-sm mt-1">Welcome back{{ firstName ? `, ${firstName}` : '' }}</p>
      </div>

      <div class="card p-8">

        <p class="text-sm font-medium text-gray-700 text-center mb-4">Where would you like to go?</p>

        <div class="grid grid-cols-2 gap-3">
          <button
            type="button"
            class="flex flex-col items-center gap-2 p-5 rounded-xl border-2 transition-all text-center"
            :class="choice === 'admin'
              ? 'border-navy bg-navy/5 text-navy'
              : 'border-gray-200 hover:border-gray-300 text-gray-600'"
            @click="choice = 'admin'"
          >
            <ShieldCheck :size="28" />
            <span class="text-sm font-semibold">Admin Console</span>
            <span class="text-micro text-gray-400 leading-tight">Users · agencies · DevOps · system settings</span>
          </button>

          <button
            type="button"
            class="flex flex-col items-center gap-2 p-5 rounded-xl border-2 transition-all text-center"
            :class="choice === 'agent'
              ? 'border-navy bg-navy/5 text-navy'
              : 'border-gray-200 hover:border-gray-300 text-gray-600'"
            @click="choice = 'agent'"
          >
            <Briefcase :size="28" />
            <span class="text-sm font-semibold">Agent Portal</span>
            <span class="text-micro text-gray-400 leading-tight">Properties · leases · maintenance · inspections</span>
          </button>
        </div>

        <button
          type="button"
          class="btn-primary w-full justify-center py-2.5 mt-5"
          :disabled="!choice"
          @click="goNext"
        >
          Continue
          <ArrowRight :size="15" />
        </button>

        <button
          type="button"
          class="w-full justify-center py-2 mt-2 text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1"
          @click="handleLogout"
        >
          <LogOut :size="13" />
          Sign out instead
        </button>
      </div>

      <p class="text-center text-xs text-gray-400 mt-4">
        Signed in as <span class="font-medium text-gray-600">{{ auth.user?.email }}</span>
      </p>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { ShieldCheck, Briefcase, ArrowRight, LogOut } from 'lucide-vue-next'

const router = useRouter()
const auth = useAuthStore()

const choice = ref<'admin' | 'agent' | ''>('')

const firstName = computed(() => {
  const full = auth.user?.full_name?.trim() ?? ''
  return full ? full.split(/\s+/)[0] : ''
})

onMounted(async () => {
  // Hydrate user if needed so the greeting + email render.
  if (auth.isAuthenticated && !auth.user) {
    try { await auth.fetchMe() } catch { /* ignore — the guard will catch it */ }
  }
  // Non-admins should never see this page — bounce to their home.
  if (auth.user && auth.user.role !== 'admin') {
    router.replace(auth.homeRoute)
  }
})

function goNext() {
  if (choice.value === 'admin') {
    router.push('/')
  } else if (choice.value === 'agent') {
    router.push('/agent')
  }
}

async function handleLogout() {
  await auth.logout()
  router.replace('/login')
}
</script>
