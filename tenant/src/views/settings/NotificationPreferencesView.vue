<template>
  <div class="flex flex-col h-full overflow-hidden bg-surface" name="NotificationPreferencesView">
    <AppHeader title="Notifications" :show-back="true" @back="router.back()" />

    <div class="scroll-page page-with-tab-bar px-4 pt-4 pb-8 space-y-4">

      <!-- Loading -->
      <div v-if="loading" class="flex justify-center py-12">
        <div class="w-8 h-8 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
      </div>

      <template v-else>

        <!-- POPIA disclosure -->
        <div class="list-section p-4 flex items-start gap-3">
          <div class="w-10 h-10 rounded-full bg-navy/10 flex items-center justify-center flex-shrink-0 mt-0.5">
            <Bell :size="18" class="text-navy" />
          </div>
          <div>
            <p class="text-sm font-semibold text-gray-900">Push notification preferences</p>
            <p class="text-xs text-gray-500 mt-1 leading-relaxed">
              Choose which categories of push notification you want to receive. You can
              change these at any time (POPIA s18 — purpose notification).
            </p>
          </div>
        </div>

        <!-- Category toggles -->
        <div>
          <p class="list-section-header px-1 pt-0 pb-1">Categories</p>
          <div class="list-section divide-y divide-gray-100">
            <div
              v-for="pref in prefs"
              :key="pref.category"
              class="flex items-center gap-3 px-4 py-3"
            >
              <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0" :class="categoryIconBg(pref.category)">
                <component :is="categoryIcon(pref.category)" :size="16" :class="categoryIconColor(pref.category)" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-900">{{ categoryLabel(pref.category) }}</p>
                <p class="text-xs text-gray-500">{{ categoryDescription(pref.category) }}</p>
              </div>
              <!-- Toggle -->
              <button
                :aria-label="`Toggle ${categoryLabel(pref.category)}`"
                :aria-checked="pref.enabled"
                role="switch"
                :disabled="saving"
                class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-navy disabled:opacity-50"
                :class="pref.enabled ? 'bg-navy' : 'bg-gray-200'"
                @click="togglePref(pref)"
              >
                <span
                  class="inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform"
                  :class="pref.enabled ? 'translate-x-6' : 'translate-x-1'"
                />
              </button>
            </div>
          </div>
        </div>

      </template>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Bell, FileText, Briefcase, CreditCard, Wrench, MessageCircle } from 'lucide-vue-next'
import AppHeader from '../../components/AppHeader.vue'
import api from '../../api'
import { useToast } from '../../composables/useToast'

const router = useRouter()
const toast  = useToast()

interface PushPref {
  category: string
  enabled: boolean
}

const loading = ref(true)
const saving  = ref(false)
const prefs   = ref<PushPref[]>([])

const CATEGORY_META: Record<string, {
  label: string
  description: string
  icon: unknown
  bg: string
  color: string
}> = {
  lease: {
    label:       'Lease updates',
    description: 'Signing reminders, lease status changes',
    icon:        FileText,
    bg:          'bg-accent/10',
    color:       'text-accent',
  },
  mandate: {
    label:       'Mandate updates',
    description: 'New mandates and mandate status changes',
    icon:        Briefcase,
    bg:          'bg-navy/10',
    color:       'text-navy',
  },
  rent: {
    label:       'Rent & payments',
    description: 'Payment confirmations, overdue reminders',
    icon:        CreditCard,
    bg:          'bg-green-100',
    color:       'text-green-600',
  },
  maintenance: {
    label:       'Maintenance updates',
    description: 'New requests and status updates',
    icon:        Wrench,
    bg:          'bg-amber-100',
    color:       'text-amber-600',
  },
  chat: {
    label:       'Chat messages',
    description: 'New messages from your property manager',
    icon:        MessageCircle,
    bg:          'bg-blue-100',
    color:       'text-blue-600',
  },
}

function categoryLabel(cat: string): string      { return CATEGORY_META[cat]?.label ?? cat }
function categoryDescription(cat: string): string { return CATEGORY_META[cat]?.description ?? '' }
function categoryIcon(cat: string): unknown       { return CATEGORY_META[cat]?.icon ?? Bell }
function categoryIconBg(cat: string): string      { return CATEGORY_META[cat]?.bg ?? 'bg-gray-100' }
function categoryIconColor(cat: string): string   { return CATEGORY_META[cat]?.color ?? 'text-gray-500' }

async function loadPreferences(): Promise<void> {
  loading.value = true
  try {
    const { data } = await api.get<PushPref[]>('/auth/push-preferences/')
    prefs.value = data
  } catch {
    toast.error('Failed to load notification preferences')
  } finally {
    loading.value = false
  }
}

async function togglePref(pref: PushPref): Promise<void> {
  if (saving.value) return
  const newVal = !pref.enabled
  pref.enabled = newVal   // optimistic
  saving.value = true
  try {
    await api.post('/auth/push-preferences/', { category: pref.category, enabled: newVal })
    toast.success(`${categoryLabel(pref.category)} ${newVal ? 'enabled' : 'disabled'}`)
  } catch {
    pref.enabled = !newVal  // revert
    toast.error('Failed to save preference')
  } finally {
    saving.value = false
  }
}

onMounted(loadPreferences)
</script>
