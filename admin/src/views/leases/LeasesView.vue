<template>
  <div class="space-y-5">
    <!-- Header + sub-tabs -->
    <div class="flex items-center justify-between border-b border-gray-200 pb-0 -mb-5">
      <div class="flex items-center gap-6">
        <button
          @click="activeTab = 'leases'"
          class="flex items-center gap-1.5 pb-3 text-sm font-medium border-b-2 transition-all"
          :class="activeTab === 'leases' ? 'border-navy text-navy' : 'border-transparent text-gray-500 hover:text-gray-700'"
        >
          <FileText :size="14" />
          All Leases
        </button>
        <button
          @click="activeTab = 'templates'"
          class="flex items-center gap-1.5 pb-3 text-sm font-medium border-b-2 transition-all"
          :class="activeTab === 'templates' ? 'border-navy text-navy' : 'border-transparent text-gray-500 hover:text-gray-700'"
        >
          <FileSignature :size="14" />
          Build Lease Template
        </button>
      </div>

      <!-- All Leases actions -->
      <div v-if="activeTab === 'leases'" class="flex items-center gap-2">
        <button class="btn-ghost" @click="showImport = true">
          <Sparkles :size="14" class="text-pink-brand" />
          Import from PDF
        </button>
        <button class="btn-primary" @click="router.push('/leases/build')">
          <Plus :size="15" /> Add Lease
        </button>
      </div>

      <!-- Template actions -->
      <label v-if="activeTab === 'templates'" class="btn-primary cursor-pointer"
        :class="uploadingTemplate ? 'opacity-60 pointer-events-none' : ''">
        <Loader2 v-if="uploadingTemplate" :size="14" class="animate-spin" />
        <Plus v-else :size="15" />
        {{ uploadingTemplate ? 'Uploading…' : 'Upload Template' }}
        <input ref="tmplFileInput" type="file" accept=".docx,.pdf" class="hidden" @change="handleTmplUpload" />
      </label>
    </div>

    <!-- ── All Leases tab ─────────────────────────────────────────────── -->
    <div v-if="activeTab === 'leases'" class="card overflow-hidden">
      <div v-if="loading" class="p-6 space-y-3 animate-pulse">
        <div v-for="i in 4" :key="i" class="h-14 bg-gray-100 rounded-lg"></div>
      </div>

      <div v-else-if="!leases.length" class="py-16 text-center text-gray-400 text-sm">
        No leases yet — import one from a PDF or create manually
      </div>

      <div v-else class="divide-y divide-gray-200">
        <template v-for="([propName, propLeases]) in groupedLeases" :key="propName">

          <!-- Property group header -->
          <div class="flex items-center gap-2.5 px-5 py-2.5 bg-gray-50 border-b border-gray-100">
            <Home :size="13" class="text-gray-400 flex-shrink-0" />
            <span class="text-xs font-semibold text-gray-600">{{ propName }}</span>
            <span class="text-[11px] text-gray-400">· {{ propLeases.length }} lease{{ propLeases.length !== 1 ? 's' : '' }}</span>
          </div>

        <div v-for="lease in propLeases" :key="lease.id" class="border-b border-gray-100 last:border-0">

          <!-- Collapsed row -->
          <div
            class="flex items-center gap-4 px-5 py-3.5 cursor-pointer hover:bg-gray-50/60 transition-colors select-none"
            @click="toggle(lease.id)"
          >
            <!-- Dates — first so you can scan the timeline -->
            <div class="flex-shrink-0 w-32 text-xs text-gray-600">
              <div class="font-medium tabular-nums">{{ formatDate(lease.start_date) }}</div>
              <div class="text-gray-400 tabular-nums">{{ formatDate(lease.end_date) }}</div>
            </div>

            <!-- Tenant summary -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-medium text-gray-900 text-sm truncate">
                  {{ lease.all_tenant_names?.[0] || lease.tenant_name || '—' }}
                </span>
                <span v-if="(lease.all_tenant_names?.length ?? 0) > 1"
                  class="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium bg-gray-100 text-gray-500">
                  +{{ lease.all_tenant_names.length - 1 }} more
                </span>
              </div>
              <div class="text-xs text-gray-400 mt-0.5 truncate">
                {{ lease.unit_label?.split(' — ')[1] ?? lease.unit_label }}
                <span class="mx-1 text-gray-300">·</span>
                <span class="font-mono">{{ lease.lease_number }}</span>
              </div>
            </div>

            <!-- Rent -->
            <div class="text-sm font-semibold text-gray-800 flex-shrink-0 tabular-nums">
              R{{ Number(lease.monthly_rent).toLocaleString() }}
            </div>

            <!-- Status -->
            <div class="flex-shrink-0">
              <span :class="statusBadge(lease.status)">{{ lease.status }}</span>
            </div>

            <!-- Documents badge + chevron -->
            <div class="flex items-center gap-2 flex-shrink-0">
              <button
                @click.stop="openDocs(lease)"
                class="relative p-1.5 text-gray-400 hover:text-navy rounded-lg hover:bg-gray-100 transition-colors"
                title="Documents"
              >
                <Paperclip :size="15" />
                <span v-if="lease.document_count > 0"
                  class="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-navy text-white text-[9px] font-bold flex items-center justify-center">
                  {{ lease.document_count }}
                </span>
              </button>
              <ChevronDown
                :size="16"
                class="text-gray-400 transition-transform duration-200"
                :class="expanded.includes(lease.id) ? 'rotate-180' : ''"
              />
            </div>
          </div>

          <!-- Expanded detail panel -->
          <div v-if="expanded.includes(lease.id)" class="bg-gray-50/60 border-t border-gray-100 px-5 py-5 space-y-5">

            <!-- Action buttons -->
            <div class="flex justify-end gap-2">
              <button
                @click.stop="openBuilderFromLease(lease.id)"
                class="btn-ghost text-xs"
                title="Renew or rebuild this lease with AI"
              >
                <FileSignature :size="12" /> Renew
              </button>
              <button
                @click.stop="editingLease = lease; showEdit = true"
                class="btn-ghost text-xs"
              >
                <Pencil :size="12" /> Edit Lease
              </button>
              <button
                @click.stop="deleteLease(lease)"
                :disabled="deletingId === lease.id"
                class="btn-ghost text-xs text-red-500 hover:text-red-700 hover:bg-red-50"
              >
                <Loader2 v-if="deletingId === lease.id" :size="12" class="animate-spin" />
                <Trash2 v-else :size="12" />
                Delete
              </button>
            </div>

            <!-- Tenants grid -->
            <div>
              <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-2.5">
                Tenants — jointly &amp; severally liable
              </div>
              <div class="grid grid-cols-2 lg:grid-cols-4 gap-2">
                <div
                  v-for="(name, i) in (lease.all_tenant_names?.length ? lease.all_tenant_names : [lease.tenant_name])"
                  :key="i"
                  class="flex items-center gap-2.5 px-3 py-2.5 bg-white rounded-xl border border-gray-200 shadow-sm"
                >
                  <div class="w-6 h-6 rounded-full bg-navy/10 flex items-center justify-center text-navy text-[11px] font-bold flex-shrink-0">
                    {{ i + 1 }}
                  </div>
                  <span class="text-sm text-gray-800 font-medium leading-snug">{{ name }}</span>
                </div>
              </div>
            </div>

            <!-- Occupants (if any) -->
            <div v-if="lease.occupants?.length">
              <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-2.5">Occupants</div>
              <div class="flex flex-wrap gap-2">
                <div
                  v-for="oc in lease.occupants"
                  :key="oc.id"
                  class="flex items-center gap-1.5 px-2.5 py-1.5 bg-white rounded-lg border border-gray-200 text-sm text-gray-700"
                >
                  <Users :size="12" class="text-gray-400" />
                  {{ oc.person.full_name }}
                  <span v-if="oc.relationship_to_tenant" class="text-gray-400 text-xs">· {{ oc.relationship_to_tenant }}</span>
                </div>
              </div>
            </div>

            <!-- Terms grid -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-3 text-sm">
              <div>
                <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-0.5">Monthly rent</div>
                <div class="font-semibold text-gray-900">R{{ Number(lease.monthly_rent).toLocaleString() }}</div>
              </div>
              <div>
                <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-0.5">Deposit</div>
                <div class="font-semibold text-gray-900">R{{ Number(lease.deposit).toLocaleString() }}</div>
              </div>
              <div>
                <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-0.5">Period</div>
                <div class="font-semibold text-gray-900">{{ leasePeriodMonths(lease.start_date, lease.end_date) }}</div>
                <div class="text-[11px] text-gray-400">{{ formatDate(lease.start_date) }} → {{ formatDate(lease.end_date) }}</div>
              </div>
              <div>
                <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-0.5">Payment ref</div>
                <div class="font-semibold text-gray-900 font-mono text-xs">{{ lease.payment_reference || '—' }}</div>
              </div>
              <div>
                <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-0.5">Water</div>
                <div class="font-semibold text-gray-900">{{ lease.water_included ? `Included (${lease.water_limit_litres?.toLocaleString()} L)` : 'Excluded' }}</div>
              </div>
              <div>
                <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-0.5">Electricity</div>
                <div class="font-semibold text-gray-900">{{ lease.electricity_prepaid ? 'Prepaid' : 'Included' }}</div>
              </div>
              <div>
                <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-0.5">Notice period</div>
                <div class="font-semibold text-gray-900">{{ lease.notice_period_days }} days</div>
              </div>
              <div>
                <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-0.5">Max occupants</div>
                <div class="font-semibold text-gray-900">{{ lease.max_occupants }}</div>
              </div>
            </div>

            <!-- Documents inline -->
            <div>
              <div class="flex items-center justify-between mb-2.5">
                <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-widest">
                  Documents ({{ lease.document_count ?? 0 }})
                </div>
                <button @click.stop="openDocs(lease)" class="btn-ghost text-xs px-2 py-1">
                  <Paperclip :size="11" /> Upload / manage
                </button>
              </div>
              <div v-if="lease.documents?.length" class="flex flex-wrap gap-2">
                <a
                  v-for="doc in lease.documents"
                  :key="doc.id"
                  :href="doc.file_url"
                  target="_blank"
                  class="flex items-center gap-1.5 px-2.5 py-1.5 bg-white rounded-lg border border-gray-200 hover:border-navy/30 hover:bg-navy/5 transition-colors text-xs text-gray-700 group"
                >
                  <FileText :size="12" class="text-gray-400 group-hover:text-navy" />
                  {{ doc.description || doc.document_type.replace('_', ' ') }}
                  <Download :size="11" class="text-gray-300 group-hover:text-navy ml-0.5" />
                </a>
              </div>
              <p v-else class="text-xs text-gray-400">No documents attached</p>
            </div>

          </div>
        </div>
        </template>
      </div>
    </div>

    <!-- ── Build Lease Template tab ──────────────────────────────────── -->
    <div v-if="activeTab === 'templates'" class="space-y-4">
      <div v-if="tmplUploadError" class="flex items-center gap-2 text-sm text-red-600 bg-red-50 px-4 py-3 rounded-xl">
        <AlertCircle :size="14" /> {{ tmplUploadError }}
      </div>

      <div v-if="!templates.length" class="card py-16 text-center text-gray-400 text-sm space-y-3">
        <FileSignature :size="32" class="mx-auto text-gray-200" />
        <div>No templates yet — upload a <strong>.docx</strong> or <strong>.pdf</strong> to get started.</div>
        <div class="text-xs text-gray-300">DOCX templates support merge fields (e.g. &#123;&#123; tenant_name &#125;&#125;) and can be previewed before signing.</div>
      </div>

      <div v-else class="card divide-y divide-gray-100">
        <div v-for="t in templates" :key="t.id" class="px-5 py-4 space-y-3">

          <!-- Top row -->
          <div class="flex items-start gap-4">
            <!-- Icon -->
            <div class="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
              :class="t.docx_file?.endsWith('.pdf') ? 'bg-red-50' : 'bg-blue-50'">
              <FileText :size="16" :class="t.docx_file?.endsWith('.pdf') ? 'text-red-500' : 'text-blue-600'" />
            </div>

            <!-- Info -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-medium text-gray-900 text-sm">{{ t.name }}</span>
                <span class="text-xs text-gray-400">v{{ t.version }}</span>
                <span v-if="t.province" class="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{{ t.province }}</span>
                <span v-if="t.is_active" class="text-xs bg-emerald-50 text-emerald-600 px-1.5 py-0.5 rounded font-medium">Active</span>
              </div>
              <div v-if="t.fields_schema?.length" class="mt-1 text-xs text-gray-400">
                {{ t.fields_schema.length }} merge fields:
                <span class="font-mono">{{ t.fields_schema.slice(0,5).join(', ') }}{{ t.fields_schema.length > 5 ? ` +${t.fields_schema.length - 5} more` : '' }}</span>
              </div>
              <div class="mt-0.5 text-xs text-gray-300">Uploaded {{ formatDate(t.created_at) }}</div>
            </div>

            <!-- Actions -->
            <div class="flex items-center gap-2 flex-shrink-0">
              <button @click="editTemplateWithAI(t.id)"
                class="btn-ghost text-xs flex items-center gap-1">
                <Sparkles :size="12" class="text-pink-brand" /> Edit with AI
              </button>
              <button v-if="!t.is_active" @click="setActiveTemplate(t.id)"
                class="btn-ghost text-xs">Set active</button>
              <button @click="deleteTemplate(t.id)" :disabled="deletingTmplId === t.id"
                class="btn-ghost text-xs text-red-500 hover:text-red-700 hover:bg-red-50">
                <Loader2 v-if="deletingTmplId === t.id" :size="12" class="animate-spin" />
                <Trash2 v-else :size="12" />
              </button>
            </div>
          </div>

          <!-- Completeness score row -->
          <div class="ml-13 pl-0.5">
            <div class="flex items-center gap-3">
              <!-- Score badge -->
              <span
                class="text-xs font-semibold px-2 py-0.5 rounded border cursor-pointer select-none"
                :class="scoreTemplate(t).labelClass"
                @click="toggleScore(t.id)"
                :title="expandedScores.has(t.id) ? 'Hide details' : 'Show what\'s missing'"
              >
                {{ scoreTemplate(t).score }}% · {{ scoreTemplate(t).label }}
              </span>
              <!-- Progress bar -->
              <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden max-w-xs">
                <div
                  class="h-full rounded-full transition-all duration-500"
                  :class="scoreTemplate(t).barClass"
                  :style="{ width: scoreTemplate(t).score + '%' }"
                />
              </div>
              <!-- Toggle details link -->
              <button class="text-[11px] text-gray-400 hover:text-gray-600" @click="toggleScore(t.id)">
                {{ expandedScores.has(t.id) ? '▲ hide' : '▼ details' }}
              </button>
            </div>

            <!-- Expandable details -->
            <div v-if="expandedScores.has(t.id)" class="mt-2 grid grid-cols-2 gap-x-6 gap-y-1">
              <div v-for="item in scoreTemplate(t).passed" :key="item"
                class="flex items-center gap-1.5 text-[11px] text-emerald-600">
                <span class="w-3 h-3 rounded-full bg-emerald-100 flex items-center justify-center text-[9px] font-bold">✓</span>
                {{ item }}
              </div>
              <div v-for="item in scoreTemplate(t).missing" :key="item"
                class="flex items-center gap-1.5 text-[11px] text-gray-400">
                <span class="w-3 h-3 rounded-full bg-gray-100 flex items-center justify-center text-[9px] font-bold text-gray-400">✗</span>
                {{ item }}
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>

    <!-- Import wizard (full screen) -->
    <ImportLeaseWizard v-if="showImport" @close="showImport = false" @done="onImportDone" />

    <!-- Edit drawer (full screen) -->
    <EditLeaseDrawer
      v-if="showEdit && editingLease"
      :lease="editingLease"
      @close="showEdit = false"
      @done="onEditDone"
    />

    <!-- Documents Drawer -->
    <Teleport to="body">
      <div v-if="docsDrawer" class="fixed inset-0 z-50 flex justify-end">
        <div class="absolute inset-0 bg-black/30 backdrop-blur-sm" @click="docsDrawer = false" />
        <div class="relative bg-white w-full max-w-sm shadow-xl flex flex-col overflow-hidden">
          <div class="flex items-center justify-between px-5 py-4 border-b border-gray-200">
            <div>
              <div class="font-semibold text-gray-900 text-sm">Documents</div>
              <div class="text-xs text-gray-500">{{ selectedLease?.all_tenant_names?.join(', ') || selectedLease?.tenant_name }}</div>
            </div>
            <button @click="docsDrawer = false" class="text-gray-400 hover:text-gray-600"><X :size="18" /></button>
          </div>

          <div class="flex-1 overflow-y-auto p-5 space-y-4">
            <div class="space-y-3">
              <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Upload Document</h3>
              <div>
                <label class="label">Type</label>
                <select v-model="uploadType" class="input">
                  <option value="signed_lease">Signed Lease</option>
                  <option value="id_copy">ID Copy</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label class="label">Description (optional)</label>
                <input v-model="uploadDescription" class="input" placeholder="e.g. John Smith ID" />
              </div>
              <div>
                <label class="label">File</label>
                <input
                  ref="fileInputRef"
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  class="input file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:font-medium file:bg-navy file:text-white hover:file:bg-navy-dark"
                  @change="onFileChange"
                />
              </div>
              <button class="btn-primary w-full justify-center" :disabled="!uploadFile || uploading" @click="uploadDocument">
                <Loader2 v-if="uploading" :size="14" class="animate-spin" />
                {{ uploading ? 'Uploading…' : 'Upload' }}
              </button>
            </div>

            <div>
              <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Attached</h3>
              <div v-if="docsLoading" class="space-y-2 animate-pulse">
                <div v-for="i in 3" :key="i" class="h-12 bg-gray-100 rounded-lg"></div>
              </div>
              <div v-else class="space-y-2">
                <div v-for="doc in documents" :key="doc.id" class="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                  <div>
                    <span :class="docTypeBadge(doc.document_type)" class="mb-1 inline-block">
                      {{ doc.document_type.replace('_', ' ') }}
                    </span>
                    <div class="text-xs text-gray-500">{{ doc.description || formatDate(doc.uploaded_at) }}</div>
                  </div>
                  <div class="flex items-center gap-1">
                    <a :href="doc.file_url" target="_blank" class="p-1.5 text-navy hover:bg-navy/10 rounded-lg transition-colors">
                      <Download :size="15" />
                    </a>
                    <button
                      @click="deleteDocument(doc)"
                      class="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete document"
                    >
                      <Trash2 :size="15" />
                    </button>
                  </div>
                </div>
                <div v-if="!documents.length" class="text-center text-gray-400 py-6 text-sm">No documents yet</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Manual Create Lease Dialog -->
    <Teleport to="body">
      <div v-if="createDialog" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="createDialog = false" />
        <div class="relative card w-full max-w-lg max-h-[90vh] overflow-y-auto p-6 space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="font-semibold text-gray-900">New Lease</h2>
            <button @click="createDialog = false" class="text-gray-400 hover:text-gray-600"><X :size="18" /></button>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="col-span-2">
              <label class="label">Unit</label>
              <select v-model="newLease.unit" class="input">
                <option value="" disabled>Select unit…</option>
                <option v-for="u in units" :key="u.id" :value="u.id">{{ u.label }}</option>
              </select>
            </div>
            <div>
              <label class="label">Start date</label>
              <input v-model="newLease.start_date" type="date" class="input" />
            </div>
            <div>
              <label class="label">End date</label>
              <input v-model="newLease.end_date" type="date" class="input" />
            </div>
            <div>
              <label class="label">Monthly rent (R)</label>
              <input v-model="newLease.monthly_rent" type="number" class="input" placeholder="5000" />
            </div>
            <div>
              <label class="label">Deposit (R)</label>
              <input v-model="newLease.deposit" type="number" class="input" placeholder="5000" />
            </div>
            <div class="col-span-2">
              <label class="label">Primary tenant name</label>
              <input v-model="primaryTenantName" class="input" placeholder="Full name" />
            </div>
            <div class="col-span-2">
              <label class="label">Payment reference</label>
              <input v-model="newLease.payment_reference" class="input" placeholder="18 Irene - Smith" />
            </div>
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button class="btn-ghost" @click="createDialog = false">Cancel</button>
            <button class="btn-primary" :disabled="saving" @click="createLease">
              <Loader2 v-if="saving" :size="14" class="animate-spin" />
              Create Lease
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'
import { Plus, Paperclip, X, Download, Loader2, Sparkles, ChevronDown, FileText, Users, Home, Pencil, Trash2, FileSignature, AlertCircle } from 'lucide-vue-next'
import ImportLeaseWizard from './ImportLeaseWizard.vue'
import EditLeaseDrawer from './EditLeaseDrawer.vue'

const router = useRouter()

const loading = ref(true)
const saving = ref(false)
const activeTab = ref<'leases' | 'templates'>('leases')
const showImport = ref(false)
const showEdit = ref(false)
const editingLease = ref<any>(null)
const leases = ref<any[]>([])
const units = ref<any[]>([])
const expanded = ref<number[]>([])
const deletingId = ref<number | null>(null)

// Group by property name, sorted by start_date desc within each group
const groupedLeases = computed(() => {
  const map = new Map<string, any[]>()
  for (const lease of leases.value) {
    const prop = lease.unit_label?.split(' — ')[0] ?? 'Unknown Property'
    if (!map.has(prop)) map.set(prop, [])
    map.get(prop)!.push(lease)
  }
  // Sort within each group by start_date descending
  for (const group of map.values()) {
    group.sort((a, b) => new Date(b.start_date).getTime() - new Date(a.start_date).getTime())
  }
  // Return as array of [propertyName, leases[]] sorted by property name
  return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b))
})

// Documents drawer
const docsDrawer = ref(false)
const docsLoading = ref(false)
const uploading = ref(false)
const selectedLease = ref<any>(null)
const documents = ref<any[]>([])
const uploadFile = ref<File | null>(null)
const uploadType = ref('signed_lease')
const uploadDescription = ref('')
const fileInputRef = ref<HTMLInputElement | null>(null)

// Manual create
const createDialog = ref(false)
const primaryTenantName = ref('')
const newLease = ref({
  unit: '', start_date: '', end_date: '',
  monthly_rent: '', deposit: '', payment_reference: '',
  max_occupants: 1, water_included: true, electricity_prepaid: true,
})

onMounted(async () => {
  await Promise.all([loadLeases(), loadUnits(), loadTemplates()])
})

async function loadLeases() {
  loading.value = true
  try {
    const { data } = await api.get('/leases/')
    leases.value = data.results ?? data
  } finally {
    loading.value = false
  }
}

async function loadUnits() {
  const { data } = await api.get('/properties/units/')
  units.value = (data.results ?? data).map((u: any) => ({
    ...u,
    label: `${u.property_name ?? u.property} — Unit ${u.unit_number}`,
  }))
}

function toggle(id: number) {
  const idx = expanded.value.indexOf(id)
  if (idx === -1) expanded.value.push(id)
  else expanded.value.splice(idx, 1)
}

function openCreateDialog() {
  primaryTenantName.value = ''
  Object.assign(newLease.value, {
    unit: '', start_date: '', end_date: '',
    monthly_rent: '', deposit: '', payment_reference: '',
    max_occupants: 1, water_included: true, electricity_prepaid: true,
  })
  createDialog.value = true
}

async function createLease() {
  saving.value = true
  try {
    const { data: person } = await api.post('/auth/persons/', {
      person_type: 'individual',
      full_name: primaryTenantName.value,
    })
    await api.post('/leases/', { ...newLease.value, primary_tenant: person.id })
    createDialog.value = false
    await loadLeases()
  } finally {
    saving.value = false
  }
}

async function deleteLease(lease: any) {
  const names = lease.all_tenant_names?.join(', ') || lease.tenant_name || ''
  const label = `${lease.lease_number || '#' + lease.id}${names ? ' — ' + names : ''}`
  if (!confirm(`Delete lease ${label}?\n\nThis will also remove all attached documents, tenants, occupants, and guarantors. This cannot be undone.`)) {
    return
  }
  deletingId.value = lease.id
  try {
    await api.delete(`/leases/${lease.id}/`)
    leases.value = leases.value.filter((l: any) => l.id !== lease.id)
    expanded.value = expanded.value.filter((id) => id !== lease.id)
  } catch (e: any) {
    const d = e?.response?.data?.detail ?? e?.response?.data ?? e?.message
    alert(typeof d === 'string' ? d : 'Could not delete lease.')
  } finally {
    deletingId.value = null
  }
}

async function openDocs(lease: any) {
  selectedLease.value = lease
  docsDrawer.value = true
  docsLoading.value = true
  try {
    const { data } = await api.get(`/leases/${lease.id}/documents/`)
    documents.value = data
  } finally {
    docsLoading.value = false
  }
}

function onFileChange(e: Event) {
  uploadFile.value = (e.target as HTMLInputElement).files?.[0] ?? null
}

async function uploadDocument() {
  if (!uploadFile.value || !selectedLease.value) return
  uploading.value = true
  try {
    const form = new FormData()
    form.append('file', uploadFile.value)
    form.append('document_type', uploadType.value)
    form.append('description', uploadDescription.value)
    const { data } = await api.post(`/leases/${selectedLease.value.id}/documents/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    documents.value.unshift(data)
    // Also refresh the lease list so document_count updates
    const leaseIdx = leases.value.findIndex(l => l.id === selectedLease.value.id)
    if (leaseIdx !== -1) {
      leases.value[leaseIdx] = { ...leases.value[leaseIdx], document_count: (leases.value[leaseIdx].document_count ?? 0) + 1, documents: [data, ...(leases.value[leaseIdx].documents ?? [])] }
    }
    uploadFile.value = null
    uploadDescription.value = ''
    if (fileInputRef.value) fileInputRef.value.value = ''
  } finally {
    uploading.value = false
  }
}

async function deleteDocument(doc: any) {
  if (!confirm(`Delete "${doc.description || doc.document_type.replace('_', ' ')}"? This cannot be undone.`)) return
  try {
    await api.delete(`/leases/${selectedLease.value.id}/documents/${doc.id}/`)
    documents.value = documents.value.filter((d: any) => d.id !== doc.id)
    const leaseIdx = leases.value.findIndex((l: any) => l.id === selectedLease.value.id)
    if (leaseIdx !== -1) {
      leases.value[leaseIdx] = {
        ...leases.value[leaseIdx],
        document_count: Math.max(0, (leases.value[leaseIdx].document_count ?? 1) - 1),
        documents: (leases.value[leaseIdx].documents ?? []).filter((d: any) => d.id !== doc.id),
      }
    }
  } catch (e: any) {
    alert('Could not delete document.')
  }
}

async function onImportDone() {
  showImport.value = false
  await loadLeases()
}

function openBuilderFromLease(_leaseId: number) {
  router.push('/leases/build')
}

function editTemplateWithAI(templateId: number) {
  router.push(`/leases/templates/${templateId}/edit`)
}

// ── Template completeness scoring ─────────────────────────────────────────
interface TemplateScore {
  score: number
  label: string
  labelClass: string
  barClass: string
  passed: string[]
  missing: string[]
}

function scoreTemplate(t: any): TemplateScore {
  const rawFields: string[] = [
    ...(t.fields_schema ?? []),
    ...Object.values(t.detected_variables ?? {}).flat() as string[],
  ]
  const fieldSet = new Set(rawFields.map((f: string) => f.toLowerCase()))
  const html = (t.content_html ?? '').toLowerCase()

  const hasField = (...names: string[]) => names.some(n => fieldSet.has(n))
  const hasText  = (...words: string[]) => words.some(w => html.includes(w))
  const hasSig   = () => [...fieldSet].some(f => f.includes('signature'))

  const checks: { name: string; ok: boolean; pts: number }[] = [
    // Core parties & property (5 pts each)
    { name: 'Landlord details',   ok: hasField('landlord_name', 'landlord'),            pts: 5 },
    { name: 'Tenant name',        ok: hasField('tenant_name', 'tenant_1_name'),          pts: 5 },
    { name: 'Property / unit',    ok: hasField('property_address', 'unit_number'),        pts: 5 },
    // Lease terms (5 pts each)
    { name: 'Lease dates',        ok: hasField('lease_start', 'lease_end'),               pts: 5 },
    { name: 'Monthly rent',       ok: hasField('monthly_rent'),                           pts: 5 },
    { name: 'Deposit amount',     ok: hasField('deposit'),                                pts: 5 },
    { name: 'Notice period',      ok: hasField('notice_period_days'),                     pts: 5 },
    // Signatures (4 pts each)
    { name: 'Signature fields',   ok: hasSig(),                                           pts: 4 },
    { name: 'Date signed',        ok: [...fieldSet].some(f => f.includes('date')),         pts: 4 },
    // Legal sections in document content (4 pts each)
    { name: 'Deposit / RHA clause',    ok: hasText('deposit', 'interest-bearing'),        pts: 4 },
    { name: 'Notice / termination',    ok: hasText('notice period', 'termination'),       pts: 4 },
    { name: 'POPIA clause',            ok: hasText('popia', 'personal information'),      pts: 4 },
    { name: 'Dispute resolution',      ok: hasText('tribunal', 'dispute'),                pts: 4 },
    { name: 'Consumer Protection Act', ok: hasText('consumer protection', ' cpa '),       pts: 4 },
    // Good to have (3 pts each)
    { name: 'Tenant ID / contact',  ok: hasField('tenant_id', 'tenant_1_id', 'tenant_phone'),  pts: 3 },
    { name: 'Landlord ID',          ok: hasField('landlord_id'),                          pts: 3 },
    { name: 'Escalation clause',    ok: hasField('escalation_percent'),                   pts: 3 },
    { name: 'Utilities',            ok: hasField('water_included', 'electricity_prepaid'), pts: 3 },
  ]

  const total   = checks.reduce((s, c) => s + c.pts, 0)
  const earned  = checks.filter(c => c.ok).reduce((s, c) => s + c.pts, 0)
  const score   = Math.round((earned / total) * 100)
  const passed  = checks.filter(c => c.ok).map(c => c.name)
  const missing = checks.filter(c => !c.ok).map(c => c.name)

  let label = 'Incomplete'; let labelClass = 'text-red-600 bg-red-50 border-red-100'; let barClass = 'bg-red-400'
  if (score >= 85) { label = 'Complete';    labelClass = 'text-emerald-700 bg-emerald-50 border-emerald-100'; barClass = 'bg-emerald-500' }
  else if (score >= 65) { label = 'Good';   labelClass = 'text-blue-700 bg-blue-50 border-blue-100';         barClass = 'bg-blue-500' }
  else if (score >= 40) { label = 'Fair';   labelClass = 'text-amber-700 bg-amber-50 border-amber-100';      barClass = 'bg-amber-400' }

  return { score, label, labelClass, barClass, passed, missing }
}

const expandedScores = ref<Set<number>>(new Set())
function toggleScore(id: number) {
  if (expandedScores.value.has(id)) expandedScores.value.delete(id)
  else expandedScores.value.add(id)
}

// ── Template management ────────────────────────────────────────────────────
const templates = ref<any[]>([])
const uploadingTemplate = ref(false)
const tmplUploadError = ref('')
const tmplFileInput = ref<HTMLInputElement | null>(null)
const deletingTmplId = ref<number | null>(null)

async function loadTemplates() {
  try {
    const { data } = await api.get('/leases/templates/')
    templates.value = data.results ?? data
  } catch { /* non-fatal */ }
}

async function handleTmplUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const lower = file.name.toLowerCase()
  if (!lower.endsWith('.docx') && !lower.endsWith('.pdf')) {
    tmplUploadError.value = 'Only .docx or .pdf files are accepted.'
    return
  }
  tmplUploadError.value = ''
  uploadingTemplate.value = true
  try {
    const fd = new FormData()
    fd.append('name', file.name.replace(/\.(docx|pdf)$/i, ''))
    fd.append('template_file', file)
    await api.post('/leases/templates/', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    await loadTemplates()
  } catch (err: any) {
    tmplUploadError.value = err?.response?.data?.error ?? 'Upload failed.'
  } finally {
    uploadingTemplate.value = false
    if (tmplFileInput.value) tmplFileInput.value.value = ''
  }
}

async function setActiveTemplate(id: number) {
  await api.patch(`/leases/templates/${id}/`, { is_active: true })
  await loadTemplates()
}

async function deleteTemplate(id: number) {
  if (!confirm('Delete this template?')) return
  deletingTmplId.value = id
  try {
    await api.delete(`/leases/templates/${id}/`)
    await loadTemplates()
  } finally {
    deletingTmplId.value = null
  }
}

async function onEditDone(_updated: any) {
  showEdit.value = false
  editingLease.value = null
  await loadLeases()
}

function statusBadge(s: string) {
  return { active: 'badge-green', pending: 'badge-amber', expired: 'badge-red', terminated: 'badge-gray' }[s] ?? 'badge-gray'
}
function docTypeBadge(t: string) {
  return { signed_lease: 'badge-purple', id_copy: 'badge-blue', other: 'badge-gray' }[t] ?? 'badge-gray'
}
function formatDate(d: string) {
  return d ? new Date(d).toLocaleDateString('en-ZA') : '—'
}

function leasePeriodMonths(start: string, end: string): string {
  if (!start || !end) return '—'
  const s = new Date(start)
  const e = new Date(end)
  const months = (e.getFullYear() - s.getFullYear()) * 12 + (e.getMonth() - s.getMonth())
  return months > 0 ? `${months} month${months !== 1 ? 's' : ''}` : '—'
}
</script>
