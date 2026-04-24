<template>
  <q-page class="q-pa-md">

    <!-- Loading -->
    <div v-if="loading" class="row justify-center q-py-xl">
      <q-spinner-dots color="primary" size="40px" />
    </div>

    <template v-else>

      <!-- POPIA disclosure -->
      <div class="section-header">
        Push Notifications
      </div>
      <q-card flat class="settings-card q-mb-md">
        <q-card-section class="q-pb-xs">
          <div class="text-caption text-grey-6 leading-relaxed">
            Control which push notifications you receive. Your preferences are stored
            securely and can be changed at any time (POPIA s18 — purpose notification).
          </div>
        </q-card-section>
      </q-card>

      <!-- Category toggles -->
      <div class="section-header">
        Categories
      </div>
      <q-card flat class="settings-card q-mb-md">
        <q-list separator>
          <q-item
            v-for="pref in prefs"
            :key="pref.category"
          >
            <q-item-section avatar>
              <q-icon :name="categoryIcon(pref.category)" color="grey-5" />
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-weight-medium">{{ categoryLabel(pref.category) }}</q-item-label>
              <q-item-label caption>{{ categoryDescription(pref.category) }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-toggle
                v-model="pref.enabled"
                color="primary"
                :disable="saving"
                @update:model-value="(val) => savePreference(pref.category, val)"
              />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

    </template>

  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { api } from '../boot/axios'

interface PushPref {
  category: string
  enabled: boolean
}

const $q     = useQuasar()
const loading = ref(true)
const saving  = ref(false)
const prefs   = ref<PushPref[]>([])

const CATEGORY_LABELS: Record<string, string> = {
  lease:       'Lease updates',
  mandate:     'Mandate updates',
  rent:        'Rent & payments',
  maintenance: 'Maintenance updates',
  chat:        'Chat messages',
}

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  lease:       'Signing reminders, lease status changes',
  mandate:     'New mandates, mandate status changes',
  rent:        'Payments received, rent overdue alerts',
  maintenance: 'New requests, status updates',
  chat:        'New messages from tenants and owners',
}

const CATEGORY_ICONS: Record<string, string> = {
  lease:       'description',
  mandate:     'handshake',
  rent:        'payments',
  maintenance: 'build',
  chat:        'chat_bubble',
}

function categoryLabel(cat: string): string {
  return CATEGORY_LABELS[cat] ?? cat
}

function categoryDescription(cat: string): string {
  return CATEGORY_DESCRIPTIONS[cat] ?? ''
}

function categoryIcon(cat: string): string {
  return CATEGORY_ICONS[cat] ?? 'notifications'
}

async function loadPreferences(): Promise<void> {
  loading.value = true
  try {
    const { data } = await api.get<PushPref[]>('/auth/push-preferences/')
    prefs.value = data
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to load notification preferences', icon: 'error' })
  } finally {
    loading.value = false
  }
}

async function savePreference(category: string, enabled: boolean): Promise<void> {
  saving.value = true
  try {
    await api.post('/auth/push-preferences/', { category, enabled })
    $q.notify({ type: 'positive', message: `${categoryLabel(category)} ${enabled ? 'enabled' : 'disabled'}`, icon: 'check' })
  } catch {
    // Revert the toggle on failure
    const pref = prefs.value.find(p => p.category === category)
    if (pref) pref.enabled = !enabled
    $q.notify({ type: 'negative', message: 'Failed to save preference', icon: 'error' })
  } finally {
    saving.value = false
  }
}

onMounted(loadPreferences)
</script>

<style scoped lang="scss">
.settings-card {
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-card-border);
  background: var(--klikk-card-bg);
  box-shadow: var(--klikk-shadow-soft);
  overflow: hidden;
}
</style>
