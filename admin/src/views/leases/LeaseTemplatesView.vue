<template>
  <div class="max-w-4xl mx-auto space-y-5">
    <PageHeader
      title="Lease Templates"
      subtitle="Build and manage reusable lease document templates. Templates are not property-specific — one template can be used across all properties."
      :crumbs="[{ label: 'Dashboard', to: '/' }, { label: 'Leases', to: '/leases' }, { label: 'Templates' }]"
    >
      <template #actions>
        <button class="btn-primary flex-shrink-0" @click="showCreate = true">
          <Plus :size="15" /> New Template
        </button>
      </template>
    </PageHeader>

    <!-- Template grid -->
    <LoadingState v-if="loading" variant="cards" :rows="4" grid-cols="grid-cols-1 sm:grid-cols-2" />

    <ErrorState
      v-else-if="loadError"
      :on-retry="reloadTemplates"
      :offline="isOffline"
    />

    <EmptyState
      v-else-if="!templates.length"
      title="No templates yet"
      description="Create your first lease template to get started."
      :icon="FileSignature"
    />

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div
        v-for="tmpl in templates" :key="tmpl.id"
        class="card p-4 hover:border-navy/40 hover:shadow-sm transition-all cursor-pointer group relative"
        @click="renameId !== tmpl.id && router.push({ name: 'lease-template-edit', params: { id: tmpl.id } })"
      >
        <!-- Status badge + menu — top right -->
        <div class="flex items-center justify-between mb-3">
          <FileText :size="18" class="text-navy flex-shrink-0" />
          <div class="flex items-center gap-1.5">
            <span
              class="badge"
              :class="tmpl.is_active ? 'badge-green' : 'badge-gray'"
            >{{ tmpl.is_active ? 'Active' : 'Inactive' }}</span>
            <!-- Context menu trigger -->
            <div class="relative">
              <button
                class="p-1 rounded hover:bg-gray-100 text-gray-300 hover:text-gray-600 transition-colors"
                @click="toggleMenu($event, tmpl.id)"
              >
                <MoreVertical :size="14" />
              </button>
              <div v-if="menuOpenId === tmpl.id" class="fixed inset-0 z-30" @click.stop="menuOpenId = null" />
              <div
                v-if="menuOpenId === tmpl.id"
                class="absolute right-0 top-full mt-1 w-36 bg-white border border-gray-200 rounded-lg shadow-lg z-40 py-1"
              >
                <button
                  class="w-full text-left px-3 py-2 text-xs hover:bg-gray-50 flex items-center gap-2 text-gray-700"
                  @click.stop="startRename(tmpl)"
                >
                  <Pencil :size="12" /> Rename
                </button>
                <button
                  class="w-full text-left px-3 py-2 text-xs hover:bg-gray-50 flex items-center gap-2 text-danger-500"
                  @click="archiveTemplate($event, tmpl)"
                >
                  <Archive :size="12" /> Archive
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Name (inline rename) -->
        <div v-if="renameId === tmpl.id" class="flex items-center gap-1.5" @click.stop>
          <input
            v-model="renameName"
            class="flex-1 text-sm font-semibold border border-navy/40 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-navy/30"
            @keydown.enter="submitRename(tmpl)"
            @keydown.escape="renameId = null"
            @vue:mounted="({ el }: any) => el.focus()"
          />
          <button class="text-xs text-navy font-semibold px-2 py-1 hover:bg-navy/10 rounded" @click.stop="submitRename(tmpl)">Save</button>
          <button class="text-xs text-gray-400 px-1 py-1 hover:text-gray-600" @click.stop="renameId = null">✕</button>
        </div>
        <div v-else class="font-semibold text-sm text-gray-900 truncate" :title="tmpl.name">{{ tmpl.name }}</div>
        <div class="text-xs text-gray-400 mt-0.5">v{{ tmpl.version }}{{ tmpl.province ? ` · ${tmpl.province}` : '' }}</div>

        <!-- Footer meta -->
        <div class="mt-3 pt-3 border-t border-gray-100 flex items-center gap-2 text-xs text-gray-500">
          <span>{{ tmpl.fields_schema?.length ?? 0 }} fields</span>
          <span v-if="tmpl.updated_at" class="text-gray-400">· {{ formatRelativeDate(tmpl.updated_at) }}</span>
          <span class="ml-auto text-gray-300 group-hover:text-navy transition-colors">Edit →</span>
        </div>
      </div>
    </div>

    <!-- Create template modal — choose source -->
    <BaseModal :open="showCreate" title="New Lease Template" @close="showCreate = false">
      <!-- Step 1: choose source -->
      <div v-if="createStep === 'choose'" class="space-y-3">
        <p class="text-xs text-gray-500">How would you like to start?</p>
        <div class="grid grid-cols-1 gap-2">
          <button
            class="flex items-center gap-3 p-4 border border-gray-200 rounded-xl text-left hover:border-navy/40 hover:bg-navy/5 transition-all"
            @click="createStep = 'details'; createSource = 'blank'"
          >
            <div class="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
              <FilePlus :size="18" class="text-gray-500" />
            </div>
            <div>
              <div class="text-sm font-semibold text-gray-800">Blank Template</div>
              <div class="text-xs text-gray-400">Start from scratch with an empty document</div>
            </div>
          </button>
          <button
            class="flex items-center gap-3 p-4 border border-gray-200 rounded-xl text-left hover:border-navy/40 hover:bg-navy/5 transition-all"
            @click="createStep = 'details'; createSource = 'upload'"
          >
            <div class="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
              <Upload :size="18" class="text-gray-500" />
            </div>
            <div>
              <div class="text-sm font-semibold text-gray-800">Upload Contract</div>
              <div class="text-xs text-gray-400">Import an existing DOCX or PDF document</div>
            </div>
          </button>
          <button
            v-if="templates.length"
            class="flex items-center gap-3 p-4 border border-gray-200 rounded-xl text-left hover:border-navy/40 hover:bg-navy/5 transition-all"
            @click="createStep = 'pick'; createSource = 'duplicate'"
          >
            <div class="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
              <Copy :size="18" class="text-gray-500" />
            </div>
            <div>
              <div class="text-sm font-semibold text-gray-800">From Existing Template</div>
              <div class="text-xs text-gray-400">Duplicate and edit an existing template</div>
            </div>
          </button>
        </div>
      </div>

      <!-- Step 1b: pick existing template to duplicate -->
      <div v-else-if="createStep === 'pick'" class="space-y-3">
        <p class="text-xs text-gray-500">Select a template to duplicate:</p>
        <div class="space-y-1.5 max-h-48 overflow-y-auto">
          <button
            v-for="tmpl in templates" :key="tmpl.id"
            class="w-full flex items-center gap-3 p-3 border rounded-lg text-left transition-all"
            :class="form.duplicateId === tmpl.id ? 'border-navy bg-navy/5' : 'border-gray-200 hover:border-navy/40'"
            @click="form.duplicateId = tmpl.id; form.name = tmpl.name + ' (Copy)'"
          >
            <FileText :size="15" class="text-navy flex-shrink-0" />
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-gray-800 truncate">{{ tmpl.name }}</div>
              <div class="text-micro text-gray-400">v{{ tmpl.version }}</div>
            </div>
          </button>
        </div>
        <button
          class="btn-primary w-full"
          :disabled="!form.duplicateId"
          @click="createStep = 'details'"
        >
          Continue
        </button>
      </div>

      <!-- Step 2: name + details -->
      <div v-else-if="createStep === 'details'" class="space-y-3">
        <div>
          <label class="label">Template name <span class="text-danger-500">*</span></label>
          <input v-model="form.name" class="input" placeholder="e.g. Standard Residential Lease" />
          <p class="text-micro text-gray-400 mt-1">Use a generic name — this template will be reusable across all properties.</p>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">Version</label>
            <input v-model="form.version" class="input" placeholder="1.0" />
          </div>
          <div>
            <label class="label">Province (optional)</label>
            <input v-model="form.province" class="input" placeholder="Western Cape" />
          </div>
        </div>
        <div v-if="createSource === 'upload'">
          <label class="label">Upload DOCX or PDF</label>
          <label class="flex flex-col items-center justify-center w-full h-20 border-2 border-dashed border-gray-200 rounded-lg cursor-pointer hover:border-navy/40 transition-colors text-xs text-gray-400 gap-1">
            <Upload :size="16" />
            <span>{{ form.file ? form.file.name : 'Click to choose file' }}</span>
            <input type="file" class="hidden" accept=".docx,.pdf" @change="onFileChange" />
          </label>
        </div>
      </div>

      <template #footer>
        <button v-if="createStep !== 'choose'" class="btn-ghost" @click="createStep = 'choose'">Back</button>
        <button v-else class="btn-ghost" @click="showCreate = false">Cancel</button>
        <button
          v-if="createStep === 'details'"
          class="btn-primary"
          :disabled="!form.name || creating"
          @click="createTemplate"
        >
          <Loader2 v-if="creating" :size="15" class="animate-spin" />
          {{ creating ? 'Creating…' : 'Create & Open Editor' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { FileSignature, FileText, FilePlus, Plus, Upload, Copy, Loader2, MoreVertical, Pencil, Archive } from 'lucide-vue-next'
import api from '../../api'
import BaseModal from '../../components/BaseModal.vue'
import EmptyState from '../../components/EmptyState.vue'
import LoadingState from '../../components/states/LoadingState.vue'
import ErrorState from '../../components/states/ErrorState.vue'
import PageHeader from '../../components/PageHeader.vue'
import { useToast } from '../../composables/useToast'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const loading   = ref(true)
const loadError = ref(false)
const isOffline = ref(false)
const templates = ref<any[]>([])
// Create template modal open state is tied to ?create=1 in the URL so the
// browser back button closes the modal instead of leaving the templates page.
const showCreate = computed({
  get: () => route.query.create === '1',
  set: (v: boolean) => {
    const q: any = { ...route.query }
    if (v) {
      q.create = '1'
      router.push({ query: q })
    } else {
      delete q.create
      router.replace({ query: q })
    }
  },
})
const creating  = ref(false)
const createStep = ref<'choose' | 'pick' | 'details'>('choose')
const createSource = ref<'blank' | 'upload' | 'duplicate'>('blank')

const form = ref({ name: '', version: '1.0', province: '', file: null as File | null, duplicateId: null as number | null })

function formatRelativeDate(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMins = Math.floor(diffMs / 60_000)
  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHrs = Math.floor(diffMins / 60)
  if (diffHrs < 24) return `${diffHrs}h ago`
  const diffDays = Math.floor(diffHrs / 24)
  if (diffDays < 7) return `${diffDays}d ago`
  return d.toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' })
}

// ── Context menu (rename / archive) ──────────────────────────────────────
const menuOpenId = ref<number | null>(null)
const renameId = ref<number | null>(null)
const renameName = ref('')

function toggleMenu(e: Event, id: number) {
  e.stopPropagation()
  menuOpenId.value = menuOpenId.value === id ? null : id
}

function startRename(tmpl: any) {
  renameId.value = tmpl.id
  renameName.value = tmpl.name
  menuOpenId.value = null
}

async function submitRename(tmpl: any) {
  const newName = renameName.value.trim()
  if (!newName || newName === tmpl.name) { renameId.value = null; return }
  try {
    await api.patch(`/leases/templates/${tmpl.id}/`, { name: newName })
    tmpl.name = newName
    toast.success('Renamed')
  } catch { toast.error('Failed to rename') }
  renameId.value = null
}

async function archiveTemplate(e: Event, tmpl: any) {
  e.stopPropagation()
  menuOpenId.value = null
  try {
    await api.patch(`/leases/templates/${tmpl.id}/`, { is_active: false })
    templates.value = templates.value.filter((t: any) => t.id !== tmpl.id)
    toast.success('Template archived')
  } catch { toast.error('Failed to archive') }
}

async function reloadTemplates() {
  loading.value = true
  loadError.value = false
  isOffline.value = false
  try {
    const { data } = await api.get('/leases/templates/')
    templates.value = data.results ?? data
  } catch (err: any) {
    isOffline.value = !navigator.onLine
    loadError.value = true
  } finally {
    loading.value = false
  }
}

onMounted(reloadTemplates)

function onFileChange(e: Event) {
  form.value.file = (e.target as HTMLInputElement).files?.[0] ?? null
}

async function createTemplate() {
  if (!form.value.name) return
  creating.value = true
  try {
    const fd = new FormData()
    fd.append('name', form.value.name)
    fd.append('version', form.value.version || '1.0')
    if (form.value.province) fd.append('province', form.value.province)

    if (createSource.value === 'upload' && form.value.file) {
      fd.append('template_file', form.value.file)
    } else if (createSource.value === 'duplicate' && form.value.duplicateId) {
      fd.append('duplicate_from', String(form.value.duplicateId))
    }
    // blank template — no file needed, backend handles it

    const { data } = await api.post('/leases/templates/', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    showCreate.value = false
    createStep.value = 'choose'
    form.value = { name: '', version: '1.0', province: '', file: null, duplicateId: null }
    toast.success('Template created')
    router.push({ name: 'lease-template-edit', params: { id: data.id } })
  } catch (e: any) {
    toast.error(e?.response?.data?.error || 'Failed to create template')
  } finally {
    creating.value = false
  }
}
</script>
