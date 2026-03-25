<template>
  <!-- Full-height split pane -->
  <div class="-m-6 h-[calc(100vh-3.5rem)] flex overflow-hidden">

    <!-- ── LEFT LIST ─────────────────────────────────────────── -->
    <div class="w-72 flex-shrink-0 border-r border-gray-200 bg-white flex flex-col overflow-hidden">

      <!-- Header -->
      <div class="px-4 pt-4 pb-3 border-b border-gray-100 flex-shrink-0">
        <div class="flex items-center gap-2 mb-3">
          <Wrench :size="15" class="text-orange-500" />
          <h2 class="text-sm font-semibold text-gray-900">Skill Library</h2>
          <span class="ml-auto text-xs text-gray-400">{{ skills.length }}</span>
        </div>
        <!-- Search -->
        <div class="relative">
          <Search :size="13" class="absolute left-2.5 top-2.5 text-gray-400" />
          <input
            v-model="search"
            @input="debouncedLoad"
            placeholder="Search skills…"
            class="w-full pl-8 pr-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-400/40 focus:border-orange-400"
          />
        </div>
        <!-- Trade filter -->
        <div class="flex gap-1 flex-wrap mt-2">
          <button
            v-for="t in ['', ...trades.map(tr => tr.value)]"
            :key="t"
            @click="activeTrade = t; loadSkills()"
            class="px-2 py-0.5 rounded-full text-[10px] font-medium transition-colors"
            :class="activeTrade === t ? 'bg-navy text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'"
          >{{ t === '' ? 'All' : trades.find(tr => tr.value === t)?.short ?? t }}</button>
        </div>
      </div>

      <!-- Skill list -->
      <div class="flex-1 overflow-y-auto">
        <div v-if="listLoading" class="p-4 space-y-3">
          <div v-for="i in 6" :key="i" class="animate-pulse space-y-1.5">
            <div class="h-3 bg-gray-100 rounded w-1/3" />
            <div class="h-3.5 bg-gray-100 rounded w-3/4" />
          </div>
        </div>

        <div v-else-if="!skills.length" class="p-6 text-center text-sm text-gray-400">
          <BookOpen :size="28" class="mx-auto mb-2 text-gray-300" />
          No skills found
        </div>

        <button
          v-for="skill in skills" :key="skill.id"
          @click="selectSkill(skill)"
          class="w-full text-left px-4 py-3 border-b border-gray-100 hover:bg-gray-50 transition-colors"
          :class="selected?.id === skill.id ? 'bg-orange-50 border-l-2 border-l-orange-400 pl-3.5' : ''"
        >
          <div class="flex items-center gap-2 mb-0.5">
            <span class="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded"
              :class="tradeBadge(skill.trade)"
            >{{ skill.trade_label }}</span>
            <span
              class="ml-auto text-[10px] font-semibold px-1.5 rounded"
              :class="difficultyColor(skill.difficulty)"
            >{{ skill.difficulty }}</span>
            <span v-if="!skill.is_active" class="text-[10px] text-gray-400">off</span>
          </div>
          <p class="text-xs font-medium text-gray-800">{{ skill.name }}</p>
          <p class="text-[10px] text-gray-400 mt-0.5">{{ skill.symptom_phrases.length }} phrases · {{ skill.steps.length }} steps</p>
        </button>
      </div>

      <!-- Add button -->
      <div class="p-3 border-t border-gray-100 flex-shrink-0">
        <button @click="openNew" class="w-full flex items-center justify-center gap-2 px-3 py-2 bg-orange-500 hover:bg-orange-600 text-white text-xs font-semibold rounded-lg transition-colors">
          <Plus :size="13" />
          New Skill
        </button>
      </div>
    </div>

    <!-- ── RIGHT PANEL ────────────────────────────────────────── -->
    <div class="flex-1 flex flex-col overflow-hidden bg-gray-50">

      <!-- Empty state -->
      <div v-if="!selected && !isNew" class="flex-1 flex flex-col items-center justify-center text-gray-400 gap-3">
        <Wrench :size="40" class="text-gray-300" />
        <p class="text-sm font-medium text-gray-500">Select a skill to edit</p>
        <p class="text-xs text-gray-400">Or create a new one to teach the AI how to handle issues</p>
      </div>

      <template v-else>
        <!-- Skill header bar -->
        <div class="flex-shrink-0 bg-white border-b border-gray-200 px-5 py-3 flex items-center gap-3">
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-gray-900 truncate">{{ form.name || 'New Skill' }}</p>
            <p class="text-xs text-gray-400">{{ isNew ? 'Creating new skill' : `Last updated ${formatDate(selected?.updated_at)}` }}</p>
          </div>
          <button
            v-if="!isNew && selected"
            @click="toggleActive"
            :disabled="saving"
            class="text-xs px-2.5 py-1 rounded-full font-semibold border transition-colors"
            :class="selected.is_active
              ? 'border-emerald-300 text-emerald-700 bg-emerald-50 hover:bg-emerald-100'
              : 'border-gray-300 text-gray-500 hover:bg-gray-100'"
          >{{ selected.is_active ? 'Active' : 'Inactive' }}</button>
          <button
            v-if="!isNew && selected"
            @click="confirmDelete"
            class="p-1.5 text-gray-400 hover:text-red-500 transition-colors rounded"
          ><Trash2 :size="15" /></button>
        </div>

        <!-- Scrollable form -->
        <div class="flex-1 overflow-y-auto p-5 space-y-5">

          <!-- Basic info row -->
          <div class="grid grid-cols-3 gap-4">
            <div class="col-span-2">
              <label class="label">Skill Name <span class="text-red-400">*</span></label>
              <input v-model="form.name" class="input" placeholder="e.g. Burst Pipe Emergency" />
            </div>
            <div>
              <label class="label">Trade</label>
              <select v-model="form.trade" class="input">
                <option v-for="t in trades" :key="t.value" :value="t.value">{{ t.label }}</option>
              </select>
            </div>
          </div>

          <div>
            <label class="label">Difficulty</label>
            <div class="flex gap-3">
              <label v-for="d in difficulties" :key="d.value"
                class="flex items-center gap-2 cursor-pointer text-sm"
              >
                <input type="radio" v-model="form.difficulty" :value="d.value"
                  class="w-3.5 h-3.5 text-orange-500 border-gray-300 focus:ring-orange-400" />
                <span :class="d.color">{{ d.label }}</span>
              </label>
            </div>
          </div>

          <!-- Symptom phrases -->
          <div class="bg-white rounded-xl border border-gray-200 p-4">
            <div class="flex items-center justify-between mb-3">
              <label class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Symptom Phrases</label>
              <span class="text-[10px] text-gray-400">Used for AI issue matching</span>
            </div>
            <div class="space-y-2">
              <div v-for="(phrase, i) in form.symptom_phrases" :key="i" class="flex items-center gap-2">
                <input
                  v-model="form.symptom_phrases[i]"
                  class="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-orange-400/40 focus:border-orange-400"
                  placeholder="e.g. water leaking from ceiling"
                />
                <button @click="removePhrase(i)" class="text-gray-400 hover:text-red-500 p-1">
                  <X :size="14" />
                </button>
              </div>
              <button
                @click="addPhrase"
                class="text-xs text-orange-600 hover:text-orange-700 font-medium flex items-center gap-1 mt-1"
              >
                <Plus :size="12" /> Add phrase
              </button>
            </div>
          </div>

          <!-- Resolution steps -->
          <div class="bg-white rounded-xl border border-gray-200 p-4">
            <div class="flex items-center justify-between mb-3">
              <label class="text-xs font-semibold text-gray-600 uppercase tracking-wide">Resolution Steps</label>
              <span class="text-[10px] text-gray-400">Ordered instructions for resolving this issue</span>
            </div>
            <div class="space-y-2">
              <div v-for="(step, i) in form.steps" :key="i" class="flex items-start gap-2">
                <span class="flex-shrink-0 w-5 h-5 mt-1.5 rounded-full bg-orange-100 text-orange-600 text-[10px] font-bold flex items-center justify-center">
                  {{ i + 1 }}
                </span>
                <textarea
                  v-model="form.steps[i]"
                  rows="2"
                  class="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-1.5 resize-none focus:outline-none focus:ring-2 focus:ring-orange-400/40 focus:border-orange-400"
                  placeholder="Describe this step…"
                />
                <div class="flex flex-col gap-0.5 flex-shrink-0 mt-1">
                  <button @click="moveStep(i, -1)" :disabled="i === 0" class="text-gray-300 hover:text-gray-600 disabled:opacity-20 p-0.5">
                    <ChevronUp :size="13" />
                  </button>
                  <button @click="moveStep(i, 1)" :disabled="i === form.steps.length - 1" class="text-gray-300 hover:text-gray-600 disabled:opacity-20 p-0.5">
                    <ChevronDown :size="13" />
                  </button>
                  <button @click="removeStep(i)" class="text-gray-300 hover:text-red-400 p-0.5">
                    <X :size="13" />
                  </button>
                </div>
              </div>
              <button
                @click="addStep"
                class="text-xs text-orange-600 hover:text-orange-700 font-medium flex items-center gap-1 mt-1"
              >
                <Plus :size="12" /> Add step
              </button>
            </div>
          </div>

          <!-- Notes -->
          <div>
            <label class="label">Notes <span class="text-[11px] text-gray-400 font-normal">(optional)</span></label>
            <textarea
              v-model="form.notes"
              rows="3"
              class="input resize-none"
              placeholder="Any additional context for the AI or technicians…"
            />
          </div>

          <p v-if="saveError" class="text-xs text-red-600">{{ saveError }}</p>
        </div>

        <!-- Save bar -->
        <div class="flex-shrink-0 border-t border-gray-200 bg-white px-5 py-3 flex justify-end gap-3">
          <button v-if="isNew" @click="cancelNew" class="btn-secondary text-sm">Cancel</button>
          <button
            @click="saveSkill"
            :disabled="!form.name.trim() || saving"
            class="flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-40"
          >
            <Save :size="14" />
            {{ saving ? 'Saving…' : isNew ? 'Create Skill' : 'Save Changes' }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'
import {
  Wrench, Search, Plus, X, Trash2, Save,
  BookOpen, ChevronUp, ChevronDown,
} from 'lucide-vue-next'

interface Skill {
  id: number
  name: string
  trade: string
  trade_label: string
  difficulty: string
  difficulty_label: string
  symptom_phrases: string[]
  steps: string[]
  notes: string
  is_active: boolean
  created_at: string
  updated_at: string
}

const skills = ref<Skill[]>([])
const selected = ref<Skill | null>(null)
const isNew = ref(false)
const listLoading = ref(true)
const saving = ref(false)
const saveError = ref('')
const search = ref('')
const activeTrade = ref('')

const form = ref({
  name: '',
  trade: 'general',
  difficulty: 'medium',
  symptom_phrases: [] as string[],
  steps: [] as string[],
  notes: '',
  is_active: true,
})

const trades = [
  { value: 'plumbing',   label: 'Plumbing',           short: 'Plumb' },
  { value: 'electrical', label: 'Electrical',          short: 'Elec' },
  { value: 'carpentry',  label: 'Carpentry',           short: 'Carp' },
  { value: 'painting',   label: 'Painting',            short: 'Paint' },
  { value: 'hvac',       label: 'HVAC / Air Con',      short: 'HVAC' },
  { value: 'roofing',    label: 'Roofing',             short: 'Roof' },
  { value: 'general',    label: 'General Maintenance', short: 'Gen' },
  { value: 'appliance',  label: 'Appliance Repair',    short: 'Appl' },
  { value: 'pest',       label: 'Pest Control',        short: 'Pest' },
  { value: 'other',      label: 'Other',               short: 'Other' },
]

const difficulties = [
  { value: 'easy',   label: 'Easy',   color: 'text-emerald-600' },
  { value: 'medium', label: 'Medium', color: 'text-amber-600' },
  { value: 'hard',   label: 'Hard',   color: 'text-red-600' },
]

let debounceTimer: ReturnType<typeof setTimeout>
function debouncedLoad() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadSkills, 300)
}

onMounted(() => loadSkills())

async function loadSkills() {
  listLoading.value = true
  try {
    const params: Record<string, string> = {}
    if (activeTrade.value) params.trade = activeTrade.value
    if (search.value) params.search = search.value
    const { data } = await api.get('/maintenance/skills/', { params })
    skills.value = data.results ?? data
  } catch {
    skills.value = []
  } finally {
    listLoading.value = false
  }
}

function selectSkill(skill: Skill) {
  isNew.value = false
  selected.value = skill
  form.value = {
    name: skill.name,
    trade: skill.trade,
    difficulty: skill.difficulty,
    symptom_phrases: [...skill.symptom_phrases],
    steps: [...skill.steps],
    notes: skill.notes,
    is_active: skill.is_active,
  }
  saveError.value = ''
}

function openNew() {
  isNew.value = true
  selected.value = null
  form.value = { name: '', trade: 'general', difficulty: 'medium', symptom_phrases: [], steps: [], notes: '', is_active: true }
  saveError.value = ''
}

function cancelNew() {
  isNew.value = false
  selected.value = null
}

async function saveSkill() {
  if (!form.value.name.trim()) return
  saveError.value = ''
  saving.value = true
  try {
    if (isNew.value) {
      const { data } = await api.post('/maintenance/skills/', { ...form.value })
      skills.value.unshift(data)
      isNew.value = false
      selected.value = data
    } else if (selected.value) {
      const { data } = await api.patch(`/maintenance/skills/${selected.value.id}/`, { ...form.value })
      const idx = skills.value.findIndex(s => s.id === data.id)
      if (idx !== -1) skills.value[idx] = data
      selected.value = data
    }
  } catch (e: any) {
    saveError.value = e?.response?.data?.detail || 'Failed to save skill.'
  } finally {
    saving.value = false
  }
}

async function toggleActive() {
  if (!selected.value) return
  saving.value = true
  try {
    const { data } = await api.patch(`/maintenance/skills/${selected.value.id}/`, { is_active: !selected.value.is_active })
    const idx = skills.value.findIndex(s => s.id === data.id)
    if (idx !== -1) skills.value[idx] = data
    selected.value = data
    form.value.is_active = data.is_active
  } finally {
    saving.value = false
  }
}

async function confirmDelete() {
  if (!selected.value || !confirm(`Delete skill "${selected.value.name}"?`)) return
  try {
    await api.delete(`/maintenance/skills/${selected.value.id}/`)
    skills.value = skills.value.filter(s => s.id !== selected.value!.id)
    selected.value = null
    isNew.value = false
  } catch { /* ignore */ }
}

function addPhrase() { form.value.symptom_phrases.push('') }
function removePhrase(i: number) { form.value.symptom_phrases.splice(i, 1) }
function addStep() { form.value.steps.push('') }
function removeStep(i: number) { form.value.steps.splice(i, 1) }
function moveStep(i: number, dir: -1 | 1) {
  const j = i + dir
  if (j < 0 || j >= form.value.steps.length) return
  const tmp = form.value.steps[i]
  form.value.steps[i] = form.value.steps[j]
  form.value.steps[j] = tmp
}

function tradeBadge(trade: string): string {
  const m: Record<string, string> = {
    plumbing: 'bg-blue-100 text-blue-700', electrical: 'bg-yellow-100 text-yellow-700',
    carpentry: 'bg-amber-100 text-amber-700', painting: 'bg-pink-100 text-pink-700',
    hvac: 'bg-cyan-100 text-cyan-700', roofing: 'bg-slate-100 text-slate-700',
    general: 'bg-gray-100 text-gray-700', appliance: 'bg-violet-100 text-violet-700',
    pest: 'bg-green-100 text-green-700', other: 'bg-gray-100 text-gray-600',
  }
  return m[trade] ?? 'bg-gray-100 text-gray-600'
}

function difficultyColor(d: string): string {
  return d === 'easy' ? 'text-emerald-600' : d === 'hard' ? 'text-red-500' : 'text-amber-600'
}

function formatDate(iso?: string) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })
}
</script>
