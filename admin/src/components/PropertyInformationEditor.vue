<template>
  <div class="card overflow-hidden">
    <!-- Card header -->
    <div class="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <Cpu :size="14" class="text-navy" />
        <span class="text-xs font-semibold uppercase tracking-wide text-navy">Property Information</span>
      </div>
      <div class="flex items-center gap-2">
        <span v-if="syncingBadge" class="text-xs text-success-600 inline-flex items-center gap-1">
          <CheckCircle2 :size="14" /> Synced to AI
        </span>
        <button
          v-if="dirty"
          class="btn-primary btn-sm"
          :disabled="saving"
          @click="save"
        >
          <Save :size="14" /> {{ saving ? 'Saving...' : 'Save' }}
        </button>
      </div>
    </div>

    <div class="px-5 py-4 space-y-4">
      <p class="text-xs text-gray-500">
        This is what the maintenance AI agent will know about your property. Add anything a tenant might ask what is the wifi password.
      </p>

      <!-- Empty-state with suggestion chips -->
      <div v-if="localItems.length === 0" class="space-y-3">
        <p class="text-sm text-gray-500">No notes yet. Start with a common one:</p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="s in suggestions"
            :key="s.label"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-gray-200 bg-white text-xs text-gray-600 hover:border-navy hover:text-navy transition-colors"
            @click="addFromSuggestion(s)"
          >
            <component :is="s.icon" :size="14" /> {{ s.label }}
          </button>
        </div>
        <button class="btn-ghost btn-sm" @click="addBlank()">
          <Plus :size="14" /> Or add a blank entry
        </button>
      </div>

      <!-- Grouped items -->
      <div v-else class="space-y-5">
        <div
          v-for="group in groupedItems"
          :key="group.category"
          class="space-y-3"
        >
          <div class="flex items-center gap-2 text-xs font-medium text-gray-400 uppercase tracking-wide">
            <component :is="categoryIcon(group.category)" :size="14" class="text-gray-400" />
            {{ categoryLabel(group.category) }}
            <span class="text-gray-200">·</span>
            <span class="text-gray-300 normal-case tracking-normal">{{ group.items.length }}</span>
          </div>

          <div
            v-for="item in group.items"
            :key="item.id"
            :ref="el => registerRowRef(item.id, el)"
            class="rounded-lg border border-gray-100 bg-gray-50/50 p-4 space-y-3"
          >
            <div class="flex gap-3">
              <input
                v-model="item.label"
                type="text"
                maxlength="120"
                placeholder="e.g. WiFi password, Bin day, Alarm code"
                class="input flex-1 text-sm"
              />
              <select
                v-model="item.category"
                class="input w-auto text-sm"
              >
                <option v-for="cat in categoryOptions" :key="cat" :value="cat">
                  {{ categoryLabel(cat) }}
                </option>
              </select>
              <button
                v-if="confirmingRemoveId !== item.id"
                class="p-2 text-gray-400 hover:text-danger-600 hover:bg-danger-50 rounded-lg transition-colors"
                aria-label="Remove entry"
                @click="confirmingRemoveId = item.id"
              >
                <Trash2 :size="14" />
              </button>
              <button
                v-else
                class="btn-danger btn-sm"
                @click="removeItem(item.id)"
              >
                Remove
              </button>
            </div>
            <textarea
              v-model="item.body"
              maxlength="4000"
              rows="2"
              placeholder="Value or instructions — tenants will see this phrased back by the AI."
              class="input text-sm resize-y min-h-14"
              @input="autogrow($event)"
            />
          </div>
        </div>

        <button class="btn-ghost btn-sm" @click="addBlank()">
          <Plus :size="14" /> Add entry
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import {
  Info, Plus, Trash2, Save, CheckCircle2, Cpu,
  Wifi, Shield, Key, BookOpen, Phone, Trash,
} from 'lucide-vue-next'
import type { Property, PropertyInformationItem, InformationCategory } from '../types/property'
import { usePropertiesStore } from '../stores/properties'
import { useToast } from '../composables/useToast'
import { extractApiError } from '../utils/api-errors'

const props = defineProps<{ property: Property }>()
const emit = defineEmits<{ (e: 'saved', items: PropertyInformationItem[]): void }>()

const propertiesStore = usePropertiesStore()
const toast = useToast()

const categoryOptions: InformationCategory[] = [
  'utilities', 'safety', 'access', 'rules', 'contacts', 'waste', 'other',
]

const CATEGORY_LABELS: Record<InformationCategory, string> = {
  utilities: 'Utilities',
  safety: 'Safety',
  access: 'Access',
  rules: 'Rules',
  contacts: 'Contacts',
  waste: 'Waste',
  other: 'Other',
}

const CATEGORY_ICONS: Record<InformationCategory, any> = {
  utilities: Wifi,
  safety: Shield,
  access: Key,
  rules: BookOpen,
  contacts: Phone,
  waste: Trash,
  other: Info,
}

function categoryLabel(c: InformationCategory) { return CATEGORY_LABELS[c] ?? c }
function categoryIcon(c: InformationCategory) { return CATEGORY_ICONS[c] ?? Info }

const suggestions: Array<{ label: string; category: InformationCategory; icon: any; body?: string }> = [
  { label: 'WiFi password', category: 'utilities', icon: Wifi },
  { label: 'Bin day / collection', category: 'waste', icon: Trash },
  { label: 'Alarm arming code', category: 'safety', icon: Shield },
  { label: 'Main electrical box location', category: 'utilities', icon: Info },
  { label: 'House rules', category: 'rules', icon: BookOpen },
  { label: 'Emergency contacts', category: 'contacts', icon: Phone },
]

// --- State ---------------------------------------------------------------

function cloneItems(source: PropertyInformationItem[] | undefined): PropertyInformationItem[] {
  return (source || []).map(it => ({
    id: it.id,
    label: it.label ?? '',
    body: it.body ?? '',
    category: (it.category as InformationCategory) ?? 'other',
    updated_at: it.updated_at ?? null,
  }))
}

const localItems = ref<PropertyInformationItem[]>(cloneItems(props.property.information_items))
const savedSnapshot = ref<string>(JSON.stringify(localItems.value))
const saving = ref(false)
const syncingBadge = ref(false)
const confirmingRemoveId = ref<string | null>(null)
const rowRefs = new Map<string, HTMLElement>()

watch(
  () => props.property.information_items,
  (v) => {
    if (!dirty.value) {
      localItems.value = cloneItems(v)
      savedSnapshot.value = JSON.stringify(localItems.value)
    }
  },
  { deep: true },
)

const dirty = computed(() => JSON.stringify(localItems.value) !== savedSnapshot.value)

const groupedItems = computed(() => {
  const order = categoryOptions
  const buckets = new Map<InformationCategory, PropertyInformationItem[]>()
  for (const cat of order) buckets.set(cat, [])
  for (const item of localItems.value) {
    const cat = categoryOptions.includes(item.category as InformationCategory)
      ? (item.category as InformationCategory)
      : 'other'
    buckets.get(cat)!.push(item)
  }
  return order
    .map(category => ({ category, items: buckets.get(category)! }))
    .filter(g => g.items.length > 0)
})

// --- Actions -------------------------------------------------------------

function newId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  return 'id-' + Math.random().toString(36).slice(2) + Date.now().toString(36)
}

function registerRowRef(id: string, el: any) {
  if (el instanceof HTMLElement) rowRefs.set(id, el)
}

async function focusRow(id: string) {
  await nextTick()
  const el = rowRefs.get(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    const input = el.querySelector('input[type="text"]') as HTMLInputElement | null
    input?.focus()
  }
}

function addBlank(preset?: Partial<PropertyInformationItem>) {
  const item: PropertyInformationItem = {
    id: newId(),
    label: preset?.label ?? '',
    body: preset?.body ?? '',
    category: (preset?.category as InformationCategory) ?? 'other',
    updated_at: null,
  }
  localItems.value.push(item)
  focusRow(item.id)
}

function addFromSuggestion(s: { label: string; category: InformationCategory; body?: string }) {
  addBlank({ label: s.label, category: s.category, body: s.body })
}

function removeItem(id: string) {
  localItems.value = localItems.value.filter(it => it.id !== id)
  confirmingRemoveId.value = null
  rowRefs.delete(id)
}

function autogrow(e: Event) {
  const ta = e.target as HTMLTextAreaElement
  ta.style.height = 'auto'
  ta.style.height = Math.min(ta.scrollHeight, 400) + 'px'
}

async function save() {
  // Basic client-side guard: drop entries with empty labels
  const payload = localItems.value
    .map(it => ({
      id: it.id,
      label: (it.label || '').trim(),
      body: (it.body || '').trim(),
      category: it.category || 'other',
    }))
    .filter(it => it.label.length > 0)

  if (payload.length !== localItems.value.length) {
    const dropped = localItems.value.length - payload.length
    if (dropped > 0) {
      toast.info(`Skipped ${dropped} entry without a label`)
    }
  }

  saving.value = true
  try {
    const updated = await propertiesStore.update(props.property.id, {
      information_items: payload as PropertyInformationItem[],
    })
    localItems.value = cloneItems(updated.information_items)
    savedSnapshot.value = JSON.stringify(localItems.value)
    emit('saved', localItems.value)
    toast.success('Saved')
    syncingBadge.value = true
    setTimeout(() => { syncingBadge.value = false }, 2500)
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to save'))
  } finally {
    saving.value = false
  }
}
</script>
