<template>
  <q-page class="page-container">

    <!-- Profile card -->
    <div class="section-header">
      Profile
    </div>
    <q-card flat class="section-card q-mb-md">
      <q-list>
        <q-item>
          <q-item-section avatar>
            <q-avatar color="primary" text-color="white" :size="AVATAR_PROFILE">
              <span class="text-weight-bold avatar-initials">
                {{ userInitials }}
              </span>
            </q-avatar>
          </q-item-section>
          <q-item-section>
            <q-item-label class="text-weight-semibold">{{ auth.user?.full_name || '—' }}</q-item-label>
            <q-item-label caption>{{ auth.user?.email }}</q-item-label>
            <q-item-label caption>
              <q-badge color="primary" :label="auth.user?.role" class="text-capitalize q-mt-xs" />
            </q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <!-- Quick links -->
    <div class="section-header">
      Account
    </div>
    <q-card flat class="section-card q-mb-md">
      <q-list separator>
        <q-item clickable v-ripple @click="$router.push('/signing')">
          <q-item-section avatar>
            <q-icon name="draw" color="secondary" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Lease &amp; Signing</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-icon name="chevron_right" color="grey-4" />
          </q-item-section>
        </q-item>
        <q-item clickable v-ripple @click="$router.push('/lease')">
          <q-item-section avatar>
            <q-icon name="description" color="primary" />
          </q-item-section>
          <q-item-section>
            <q-item-label>My Lease</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-icon name="chevron_right" color="grey-4" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <!-- App info -->
    <div class="section-header">
      App
    </div>
    <q-card flat class="section-card q-mb-md">
      <q-list separator>
        <q-item>
          <q-item-section avatar>
            <q-icon name="phone_iphone" color="grey-5" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Platform</q-item-label>
            <q-item-label caption>{{ platformLabel }}</q-item-label>
          </q-item-section>
        </q-item>
        <q-item>
          <q-item-section avatar>
            <q-icon name="info_outline" color="grey-5" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Version</q-item-label>
            <q-item-label caption>Klikk Tenant 1.0.0</q-item-label>
          </q-item-section>
        </q-item>
        <q-item>
          <q-item-section avatar>
            <q-icon name="api" color="grey-5" />
          </q-item-section>
          <q-item-section>
            <q-item-label>API</q-item-label>
            <q-item-label caption>{{ apiBase }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <!-- Sign out -->
    <div class="section-header">
      Account
    </div>
    <q-card flat class="section-card q-mb-md">
      <q-list>
        <q-item clickable v-ripple @click="confirmLogout">
          <q-item-section avatar>
            <q-icon name="logout" color="negative" />
          </q-item-section>
          <q-item-section>
            <q-item-label class="text-negative text-weight-medium">Sign Out</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-icon name="chevron_right" color="grey-4" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <!-- Legal footer -->
    <div class="text-caption text-grey-4 text-center q-mt-lg q-pb-md">
      Klikk Property Management · South Africa<br />
      POPIA compliant · {{ currentYear }}
    </div>

  </q-page>
</template>

<script setup lang="ts">
defineOptions({ name: 'SettingsPage' })

import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from '../stores/auth'
import { usePlatform } from '../composables/usePlatform'
import { AVATAR_PROFILE } from '../utils/designTokens'

const auth   = useAuthStore()
const router = useRouter()
const $q     = useQuasar()
const { isIos, isAndroid } = usePlatform()

// ── Computed in component ─────────────────────────────────────────────────────
const userInitials = computed(() => {
  const name = auth.user?.full_name || ''
  return name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || '?'
})

const platformLabel = computed(() => {
  if (isIos.value) return 'iOS'
  if (isAndroid.value) return 'Android'
  return 'Web'
})

const apiBase = computed(() => process.env.API_URL || 'http://localhost:8000/api/v1')

const currentYear = computed(() => new Date().getFullYear())

function confirmLogout() {
  $q.dialog({
    title:   'Sign Out',
    message: 'Are you sure you want to sign out?',
    cancel:  true,
    ok:      { label: 'Sign Out', color: 'negative', flat: true },
  }).onOk(async () => {
    try {
      await auth.logout()
      void router.replace('/login')
    } catch {
      $q.notify({ type: 'negative', message: 'Failed to sign out. Please try again.', icon: 'error' })
    }
  })
}
</script>

<style scoped lang="scss">
.avatar-initials {
  font-size: 18px;
  line-height: 1;
}
</style>
