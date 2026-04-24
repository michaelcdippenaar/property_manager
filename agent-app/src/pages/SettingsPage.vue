<template>
  <q-page class="q-pa-md">

    <!-- Profile card -->
    <div class="section-header">
      Profile
    </div>
    <q-card flat class="settings-card q-mb-md">
      <q-list>
        <q-item>
          <q-item-section avatar>
            <q-avatar color="primary" text-color="white" size="48px">
              <span class="text-weight-bold avatar-initials">
                {{ userInitials }}
              </span>
            </q-avatar>
          </q-item-section>
          <q-item-section>
            <q-item-label class="text-weight-semibold">{{ auth.user?.full_name || '—' }}</q-item-label>
            <q-item-label caption>{{ auth.user?.email }}</q-item-label>
            <q-item-label caption>
              <q-badge :color="roleColor" :label="auth.user?.role" class="text-capitalize q-mt-xs" />
            </q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <!-- Agency card -->
    <template v-if="auth.agency">
      <div class="section-header">
        Agency
      </div>
      <q-card flat class="settings-card q-mb-md">
        <q-list>
          <q-item>
            <q-item-section avatar>
              <q-avatar v-if="auth.agency.logo" size="40px">
                <img :src="auth.agency.logo" :alt="auth.agency.name" />
              </q-avatar>
              <q-avatar v-else color="grey-2" text-color="grey-6" size="40px">
                <q-icon name="business" />
              </q-avatar>
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-weight-semibold">{{ auth.agency.name }}</q-item-label>
              <q-item-label caption v-if="auth.agency.phone">{{ auth.agency.phone }}</q-item-label>
              <q-item-label caption v-if="auth.agency.email">{{ auth.agency.email }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>
    </template>

    <!-- App settings -->
    <div class="section-header">
      App
    </div>
    <q-card flat class="settings-card q-mb-md">
      <q-list separator>
        <q-item>
          <q-item-section avatar>
            <q-icon name="phone_iphone" color="grey-5" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Platform</q-item-label>
            <q-item-label caption>{{ platform }}</q-item-label>
          </q-item-section>
        </q-item>
        <q-item>
          <q-item-section avatar>
            <q-icon name="info_outline" color="grey-5" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Version</q-item-label>
            <q-item-label caption>Klikk Agent 1.0.0</q-item-label>
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

    <!-- Notifications -->
    <div class="section-header">
      Notifications
    </div>
    <q-card flat class="settings-card q-mb-md">
      <q-list>
        <q-item clickable v-ripple @click="router.push('/settings/notifications')">
          <q-item-section avatar>
            <q-icon name="notifications" color="grey-5" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Push notification preferences</q-item-label>
            <q-item-label caption>Manage which categories you receive</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-icon name="chevron_right" color="grey-4" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <!-- Sign out -->
    <div class="section-header">
      Account
    </div>
    <q-card flat class="settings-card q-mb-md">
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
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from '../stores/auth'
import { usePlatform } from '../composables/usePlatform'

const auth   = useAuthStore()
const router = useRouter()
const $q     = useQuasar()
const { isIos, isAndroid } = usePlatform()

const userInitials = computed(() => {
  const name = auth.user?.full_name || ''
  return name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase() || '?'
})

const roleColor = computed(() => ({
  admin: 'secondary',
  agent: 'primary',
}[auth.user?.role ?? ''] ?? 'grey-5'))

const platform = computed(() => {
  if (isIos.value) return 'iOS'
  if (isAndroid.value) return 'Android'
  return 'Web'
})

const apiBase = computed(() => process.env.API_URL || 'http://localhost:8000/api/v1')
const currentYear = new Date().getFullYear()

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
      $q.notify({ type: 'negative', message: 'Sign out failed. Please try again.', icon: 'error' })
    }
  })
}
</script>

<style scoped lang="scss">
.settings-card {
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-card-border);
  background: var(--klikk-card-bg);
  box-shadow: var(--klikk-shadow-soft);
  overflow: hidden;
}

.avatar-initials {
  font-size: 18px;
  line-height: 1;
}
</style>
