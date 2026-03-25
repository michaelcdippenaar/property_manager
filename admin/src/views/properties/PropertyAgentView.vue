<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-lg font-semibold text-gray-900">Property Agent</h1>
        <p class="text-xs text-gray-400 mt-0.5">Configure how the AI agent handles each property</p>
      </div>
    </div>

    <!-- Property selector -->
    <div class="flex items-center gap-3">
      <select v-model="selectedPropertyId" @change="loadConfig" class="input w-64 text-sm">
        <option :value="null" disabled>Select a property…</option>
        <option v-for="p in properties" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
      <div v-if="config && !loading" class="flex items-center gap-1.5 text-xs">
        <span
          class="w-2 h-2 rounded-full"
          :class="config.is_active ? 'bg-emerald-400' : 'bg-gray-300'"
        />
        <span :class="config.is_active ? 'text-emerald-700' : 'text-gray-400'">
          AI {{ config.is_active ? 'active' : 'inactive' }}
        </span>
        <button
          @click="toggleActive"
          :disabled="saving"
          class="ml-1 text-xs px-2 py-0.5 rounded border transition-colors"
          :class="config.is_active
            ? 'border-gray-300 text-gray-500 hover:bg-gray-50'
            : 'border-emerald-300 text-emerald-600 hover:bg-emerald-50'"
        >{{ config.is_active ? 'Disable' : 'Enable' }}</button>
      </div>
    </div>

    <!-- No property selected -->
    <div v-if="!selectedPropertyId" class="card p-12 text-center">
      <Bot :size="40" class="mx-auto mb-3 text-gray-300" />
      <p class="text-sm font-medium text-gray-500">Select a property to configure its AI agent</p>
    </div>

    <!-- Loading -->
    <div v-else-if="loading" class="space-y-4">
      <div class="card p-5 animate-pulse space-y-3">
        <div class="h-4 bg-gray-100 rounded w-1/4" />
        <div class="h-3 bg-gray-100 rounded w-3/4" />
        <div class="h-24 bg-gray-100 rounded" />
      </div>
      <div class="card p-5 animate-pulse space-y-3">
        <div class="h-4 bg-gray-100 rounded w-1/4" />
        <div class="h-3 bg-gray-100 rounded w-2/3" />
        <div class="h-16 bg-gray-100 rounded" />
      </div>
    </div>

    <template v-else-if="config">
      <!-- Split layout: config cards + preview panel -->
      <div class="grid grid-cols-1 xl:grid-cols-3 gap-5">

        <!-- Left: editor (2/3) -->
        <div class="xl:col-span-2 space-y-5">

          <!-- Maintenance Playbook -->
          <div class="card p-5">
            <div class="flex items-start gap-3 mb-4">
              <div class="w-8 h-8 rounded-lg bg-orange-100 flex items-center justify-center flex-shrink-0">
                <ClipboardList :size="16" class="text-orange-600" />
              </div>
              <div class="min-w-0">
                <h3 class="text-sm font-semibold text-gray-900">Maintenance Playbook</h3>
                <p class="text-xs text-gray-400 mt-0.5">
                  Instructions for how the AI should handle maintenance requests at this property —
                  escalation rules, preferred suppliers, special procedures, restrictions.
                </p>
              </div>
            </div>
            <textarea
              v-model="config.maintenance_playbook"
              rows="10"
              class="input resize-y font-mono text-xs leading-relaxed"
              placeholder="Example:
• Always escalate plumbing issues above medium priority to Bob's Plumbing.
• Do not dispatch anyone without owner approval for jobs over R5,000.
• The main distribution board is in the basement — require an electrician with a valid CoC.
• Garbage day is Tuesday — inform tenants if they report missed pickups.
• Pool maintenance is handled by AquaCare (not tracked in this system)."
            />
          </div>

          <!-- AI Context Notes -->
          <div class="card p-5">
            <div class="flex items-start gap-3 mb-4">
              <div class="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center flex-shrink-0">
                <BrainCircuit :size="16" class="text-indigo-600" />
              </div>
              <div class="min-w-0">
                <h3 class="text-sm font-semibold text-gray-900">AI Context Notes</h3>
                <p class="text-xs text-gray-400 mt-0.5">
                  General knowledge the AI should have about this property — quirks, history, tenant notes, building-specific details.
                </p>
              </div>
            </div>
            <textarea
              v-model="config.ai_notes"
              rows="7"
              class="input resize-y text-sm leading-relaxed"
              placeholder="e.g. This is an older building with cast-iron pipes — avoid high-pressure cleaning. The gate motor has a known fault that often false-trips; instruct tenants to manually override before calling a technician."
            />
          </div>

          <!-- Save -->
          <div class="flex items-center justify-between">
            <p v-if="saveSuccess" class="text-xs text-emerald-600 flex items-center gap-1.5">
              <CheckCircle2 :size="13" /> Saved successfully
            </p>
            <p v-else-if="saveError" class="text-xs text-red-600">{{ saveError }}</p>
            <div v-else />
            <button
              @click="saveConfig"
              :disabled="saving"
              class="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-40"
            >
              <Save :size="14" />
              {{ saving ? 'Saving…' : 'Save Config' }}
            </button>
          </div>
        </div>

        <!-- Right: info panel (1/3) -->
        <div class="space-y-4">

          <!-- Property stats -->
          <div class="card p-4">
            <h4 class="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-3">Property Overview</h4>
            <div class="space-y-2">
              <div class="flex justify-between text-sm">
                <span class="text-gray-500">Name</span>
                <span class="font-medium text-gray-800">{{ selectedProperty?.name }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-gray-500">Units</span>
                <span class="font-medium text-gray-800">{{ selectedProperty?.unit_count ?? '—' }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-gray-500">City</span>
                <span class="font-medium text-gray-800">{{ selectedProperty?.city ?? '—' }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-gray-500">Type</span>
                <span class="font-medium text-gray-800 capitalize">{{ selectedProperty?.property_type ?? '—' }}</span>
              </div>
            </div>
          </div>

          <!-- Tips card -->
          <div class="card p-4 bg-amber-50 border-amber-200">
            <div class="flex items-center gap-2 mb-2">
              <Lightbulb :size="14" class="text-amber-600" />
              <h4 class="text-xs font-semibold text-amber-800">Playbook Tips</h4>
            </div>
            <ul class="text-xs text-amber-700 space-y-1.5 leading-relaxed">
              <li>• Define escalation thresholds (e.g. cost limits, priority levels)</li>
              <li>• List preferred suppliers and their specialisations</li>
              <li>• Note any restrictions (owner approval, after-hours rules)</li>
              <li>• Include special procedures for common issues</li>
              <li>• Reference local knowledge (garbage day, parking rules)</li>
            </ul>
          </div>

          <!-- Updated at -->
          <p v-if="config.updated_at" class="text-[10px] text-gray-400 text-center">
            Last updated {{ formatDate(config.updated_at) }}
          </p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '../../api'
import {
  Bot, ClipboardList, BrainCircuit, Save, CheckCircle2, Lightbulb,
} from 'lucide-vue-next'

interface PropertySummary {
  id: number
  name: string
  city: string
  property_type: string
  unit_count: number
}

interface AgentConfig {
  id?: number
  property: number
  maintenance_playbook: string
  ai_notes: string
  is_active: boolean
  updated_at?: string
}

const properties = ref<PropertySummary[]>([])
const selectedPropertyId = ref<number | null>(null)
const config = ref<AgentConfig | null>(null)
const loading = ref(false)
const saving = ref(false)
const saveSuccess = ref(false)
const saveError = ref('')

const selectedProperty = computed(() =>
  properties.value.find(p => p.id === selectedPropertyId.value) ?? null
)

onMounted(async () => {
  try {
    const { data } = await api.get('/properties/')
    properties.value = (data.results ?? data).map((p: any) => ({
      id: p.id, name: p.name, city: p.city, property_type: p.property_type, unit_count: p.unit_count,
    }))
    if (properties.value.length === 1) {
      selectedPropertyId.value = properties.value[0].id
      loadConfig()
    }
  } catch { /* ignore */ }
})

async function loadConfig() {
  if (!selectedPropertyId.value) return
  loading.value = true
  config.value = null
  saveSuccess.value = false
  saveError.value = ''
  try {
    const { data } = await api.get(`/properties/agent-config/by-property/${selectedPropertyId.value}/`)
    config.value = data
  } catch {
    // Create a blank config in memory so the user can fill it in
    config.value = {
      property: selectedPropertyId.value,
      maintenance_playbook: '',
      ai_notes: '',
      is_active: true,
    }
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  if (!config.value) return
  saving.value = true
  saveSuccess.value = false
  saveError.value = ''
  try {
    const { data } = await api.put(
      `/properties/agent-config/by-property/${selectedPropertyId.value}/`,
      {
        property: selectedPropertyId.value,
        maintenance_playbook: config.value.maintenance_playbook,
        ai_notes: config.value.ai_notes,
        is_active: config.value.is_active,
      }
    )
    config.value = data
    saveSuccess.value = true
    setTimeout(() => { saveSuccess.value = false }, 3000)
  } catch (e: any) {
    saveError.value = e?.response?.data?.detail || 'Failed to save configuration.'
  } finally {
    saving.value = false
  }
}

async function toggleActive() {
  if (!config.value) return
  saving.value = true
  try {
    const { data } = await api.patch(
      `/properties/agent-config/by-property/${selectedPropertyId.value}/`,
      { property: selectedPropertyId.value, is_active: !config.value.is_active }
    )
    config.value = data
  } finally {
    saving.value = false
  }
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>
