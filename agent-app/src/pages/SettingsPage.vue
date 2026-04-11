<template>
  <q-page class="q-pa-md">

    <!-- Profile card -->
    <div class="text-caption text-grey-6 text-uppercase q-mb-xs q-ml-xs letter-spacing-wide">
      Profile
    </div>
    <q-card flat class="settings-card q-mb-md">
      <q-list>
        <q-item>
          <q-item-section avatar>
            <q-avatar color="primary" text-color="white" size="48px">
              <span class="text-weight-bold" style="font-size:18px">
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
      <div class="text-caption text-grey-6 text-uppercase q-mb-xs q-ml-xs letter-spacing-wide">
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
    <div class="text-caption text-grey-6 text-uppercase q-mb-xs q-ml-xs letter-spacing-wide">
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

    <!-- Sign out -->
    <div class="text-caption text-grey-6 text-uppercase q-mb-xs q-ml-xs letter-spacing-wide">
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
      POPIA compliant · {{ new Date().getFullYear() }}
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

function confirmLogout() {
  $q.dialog({
    title:   'Sign Out',
    message: 'Are you sure you want to sign out?',
    cancel:  true,
    ok:      { label: 'Sign Out', color: 'negative', flat: true },
  }).onOk(async () => {
    await auth.logout()
    void router.replace('/login')
  })
}
</script>

<style scoped lang="scss">
.settings-card {
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.letter-spacing-wide {
  letter-spacing: 0.05em;
}
</style>
