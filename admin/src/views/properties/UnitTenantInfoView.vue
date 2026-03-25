<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h1 class="text-lg font-semibold text-gray-900">Unit & Tenant Info</h1>
      <button @click="openAdd" class="btn-primary flex items-center gap-2 text-sm">
        <Plus :size="15" />
        Add Item
      </button>
    </div>

    <!-- Filters -->
    <div class="flex gap-3 items-center flex-wrap">
      <select v-model="selectedProperty" @change="onPropertyFilter" class="input text-sm w-56">
        <option :value="null">All properties</option>
        <option v-for="p in properties" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
      <select v-model="selectedUnit" @change="loadItems" class="input text-sm w-48" :disabled="!selectedProperty">
        <option :value="null">All units</option>
        <option v-for="u in filterUnits" :key="u.id" :value="u.id">Unit {{ u.unit_number }}</option>
      </select>
    </div>

    <!-- Loading skeletons -->
    <div v-if="loading" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      <div v-for="i in 8" :key="i" class="card p-4 animate-pulse space-y-2">
        <div class="w-9 h-9 bg-gray-100 rounded-xl mb-3" />
        <div class="h-3 bg-gray-100 rounded w-1/2" />
        <div class="h-4 bg-gray-100 rounded w-3/4" />
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="!items.length" class="card p-12 text-center">
      <Info :size="40" class="mx-auto mb-3 text-gray-300" />
      <p class="text-sm font-medium text-gray-500 mb-1">No info items yet</p>
      <p class="text-xs text-gray-400">Add WiFi codes, alarm codes, garbage days, parking info and more.</p>
    </div>

    <!-- Cards grid -->
    <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      <div
        v-for="item in items" :key="item.id"
        class="card p-4 group relative hover:shadow-md transition-shadow cursor-pointer"
        @click="openEdit(item)"
      >
        <div class="w-9 h-9 rounded-xl flex items-center justify-center mb-3" :class="iconBg(item.icon_type)">
          <component :is="iconComponent(item.icon_type)" :size="18" :class="iconColor(item.icon_type)" />
        </div>
        <p class="text-[11px] text-gray-400 font-semibold uppercase tracking-wide mb-0.5">{{ item.label }}</p>
        <p class="text-sm font-semibold text-gray-800 leading-snug break-words">{{ item.value }}</p>
        <p class="text-[10px] text-gray-400 mt-1.5">
          {{ item.unit_number ? `Unit ${item.unit_number}` : item.property_name }}
        </p>
        <button
          @click.stop="confirmDelete(item.id)"
          class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded text-gray-400 hover:text-red-500"
        >
          <Trash2 :size="13" />
        </button>
      </div>
    </div>

    <!-- Drawer -->
    <Teleport to="body">
      <div v-if="drawerOpen" class="fixed inset-0 z-50 flex justify-end">
        <div class="absolute inset-0 bg-black/30 backdrop-blur-[1px]" @click="drawerOpen = false" />
        <div class="relative w-full max-w-sm bg-white h-full shadow-xl flex flex-col">
          <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between flex-shrink-0">
            <h2 class="text-sm font-semibold text-gray-900">{{ editing ? 'Edit Info Item' : 'New Info Item' }}</h2>
            <button @click="drawerOpen = false" class="text-gray-400 hover:text-gray-600"><X :size="18" /></button>
          </div>

          <div class="flex-1 overflow-y-auto p-5 space-y-4">
            <div>
              <label class="label">Property <span class="text-red-400">*</span></label>
              <select v-model="form.property" @change="onFormPropertyChange" class="input">
                <option :value="null" disabled>Select property…</option>
                <option v-for="p in properties" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
            </div>

            <div>
              <label class="label">
                Unit
                <span class="text-[11px] text-gray-400 font-normal ml-1">(optional)</span>
              </label>
              <select v-model="form.unit" class="input" :disabled="!form.property">
                <option :value="null">Property-wide</option>
                <option v-for="u in formUnits" :key="u.id" :value="u.id">Unit {{ u.unit_number }}</option>
              </select>
            </div>

            <div>
              <label class="label">Icon</label>
              <div class="grid grid-cols-5 gap-2 mt-1">
                <button
                  v-for="ic in iconTypes" :key="ic.value"
                  @click="form.icon_type = ic.value"
                  type="button"
                  class="flex flex-col items-center gap-1 p-2 rounded-lg border text-[10px] font-medium transition-colors"
                  :class="form.icon_type === ic.value
                    ? 'border-indigo-400 bg-indigo-50 text-indigo-700'
                    : 'border-gray-200 text-gray-500 hover:border-gray-300'"
                >
                  <component :is="ic.icon" :size="16" />
                  {{ ic.label }}
                </button>
              </div>
            </div>

            <div>
              <label class="label">Label <span class="text-red-400">*</span></label>
              <input v-model="form.label" class="input" placeholder="e.g. WiFi Password, Garbage Day…" />
            </div>

            <div>
              <label class="label">Value <span class="text-red-400">*</span></label>
              <textarea v-model="form.value" rows="3" class="input resize-none" placeholder="e.g. Apartment@2024" />
            </div>
          </div>

          <div class="p-4 border-t border-gray-100 flex gap-3 flex-shrink-0">
            <button @click="drawerOpen = false" class="btn-secondary flex-1 text-sm">Cancel</button>
            <button
              @click="saveItem"
              :disabled="!form.property || !form.label.trim() || !form.value.trim() || saving"
              class="btn-primary flex-1 text-sm disabled:opacity-40"
            >{{ saving ? 'Saving…' : 'Save' }}</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'
import {
  Wifi, ShieldCheck, Trash2 as TrashIcon2, ParkingSquare, Zap, Droplets,
  Flame, DoorOpen, WashingMachine, Info, Plus, X, Trash2,
} from 'lucide-vue-next'

interface InfoItem {
  id: number
  property: number
  property_name: string
  unit: number | null
  unit_number: string | null
  icon_type: string
  label: string
  value: string
}

const iconTypes = [
  { value: 'wifi',        label: 'WiFi',     icon: Wifi },
  { value: 'alarm',       label: 'Alarm',    icon: ShieldCheck },
  { value: 'garbage',     label: 'Bin',      icon: TrashIcon2 },
  { value: 'parking',     label: 'Parking',  icon: ParkingSquare },
  { value: 'electricity', label: 'Electric', icon: Zap },
  { value: 'water',       label: 'Water',    icon: Droplets },
  { value: 'gas',         label: 'Gas',      icon: Flame },
  { value: 'intercom',    label: 'Intercom', icon: DoorOpen },
  { value: 'laundry',     label: 'Laundry',  icon: WashingMachine },
  { value: 'other',       label: 'Other',    icon: Info },
]

const items = ref<InfoItem[]>([])
const properties = ref<{ id: number; name: string }[]>([])
const filterUnits = ref<{ id: number; unit_number: string }[]>([])
const formUnits = ref<{ id: number; unit_number: string }[]>([])
const selectedProperty = ref<number | null>(null)
const selectedUnit = ref<number | null>(null)
const loading = ref(true)
const drawerOpen = ref(false)
const saving = ref(false)
const editing = ref<InfoItem | null>(null)

const form = ref({
  property: null as number | null,
  unit: null as number | null,
  icon_type: 'other',
  label: '',
  value: '',
})

onMounted(async () => {
  try {
    const { data } = await api.get('/properties/')
    properties.value = (data.results ?? data).map((p: any) => ({ id: p.id, name: p.name }))
  } catch { /* ignore */ }
  loadItems()
})

async function onPropertyFilter() {
  selectedUnit.value = null
  filterUnits.value = []
  if (selectedProperty.value) {
    try {
      const { data } = await api.get('/properties/units/', { params: { property: selectedProperty.value } })
      filterUnits.value = (data.results ?? data).map((u: any) => ({ id: u.id, unit_number: u.unit_number }))
    } catch { /* ignore */ }
  }
  loadItems()
}

async function loadItems() {
  loading.value = true
  try {
    const params: Record<string, any> = {}
    if (selectedProperty.value) params.property = selectedProperty.value
    if (selectedUnit.value) params.unit = selectedUnit.value
    const { data } = await api.get('/properties/unit-info/', { params })
    items.value = data.results ?? data
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

async function onFormPropertyChange() {
  form.value.unit = null
  formUnits.value = []
  if (!form.value.property) return
  try {
    const { data } = await api.get('/properties/units/', { params: { property: form.value.property } })
    formUnits.value = (data.results ?? data).map((u: any) => ({ id: u.id, unit_number: u.unit_number }))
  } catch { /* ignore */ }
}

function openAdd() {
  editing.value = null
  form.value = { property: selectedProperty.value, unit: selectedUnit.value, icon_type: 'other', label: '', value: '' }
  drawerOpen.value = true
  if (form.value.property) onFormPropertyChange()
}

function openEdit(item: InfoItem) {
  editing.value = item
  form.value = { property: item.property, unit: item.unit, icon_type: item.icon_type, label: item.label, value: item.value }
  drawerOpen.value = true
  onFormPropertyChange()
}

async function saveItem() {
  if (!form.value.property || !form.value.label.trim() || !form.value.value.trim()) return
  saving.value = true
  try {
    const payload = { ...form.value }
    if (editing.value) {
      const { data } = await api.patch(`/properties/unit-info/${editing.value.id}/`, payload)
      const idx = items.value.findIndex(i => i.id === data.id)
      if (idx !== -1) items.value[idx] = data
    } else {
      const { data } = await api.post('/properties/unit-info/', payload)
      items.value.unshift(data)
    }
    drawerOpen.value = false
  } catch { /* ignore */ } finally {
    saving.value = false
  }
}

async function confirmDelete(id: number) {
  if (!confirm('Delete this info item?')) return
  try {
    await api.delete(`/properties/unit-info/${id}/`)
    items.value = items.value.filter(i => i.id !== id)
  } catch { /* ignore */ }
}

function iconComponent(type: string) {
  return iconTypes.find(i => i.value === type)?.icon ?? Info
}

function iconBg(type: string): string {
  const m: Record<string, string> = {
    wifi: 'bg-blue-50', alarm: 'bg-red-50', garbage: 'bg-gray-100', parking: 'bg-slate-100',
    electricity: 'bg-yellow-50', water: 'bg-cyan-50', gas: 'bg-orange-50',
    intercom: 'bg-purple-50', laundry: 'bg-teal-50', other: 'bg-gray-100',
  }
  return m[type] ?? 'bg-gray-100'
}

function iconColor(type: string): string {
  const m: Record<string, string> = {
    wifi: 'text-blue-500', alarm: 'text-red-500', garbage: 'text-gray-500', parking: 'text-slate-600',
    electricity: 'text-yellow-500', water: 'text-cyan-500', gas: 'text-orange-500',
    intercom: 'text-purple-500', laundry: 'text-teal-500', other: 'text-gray-400',
  }
  return m[type] ?? 'text-gray-400'
}
</script>
