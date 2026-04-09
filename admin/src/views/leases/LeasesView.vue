<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <p class="text-sm text-gray-500">View and manage all lease agreements.</p>
      <div class="flex items-center gap-2 flex-shrink-0">
        <button class="btn-ghost" @click="showImport = true">
          <Sparkles :size="15" class="text-accent" />
          Import from PDF
        </button>
        <button class="btn-primary" @click="router.push('/leases/build')">
          <Plus :size="15" /> New Lease
        </button>
      </div>
    </div>

    <!-- Status tabs -->
    <div class="flex gap-1 border-b border-gray-200">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px"
        :class="activeTab === tab.key
          ? 'border-navy text-navy'
          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
        <span
          v-if="tab.count != null"
          class="ml-1.5 text-[11px] font-semibold px-1.5 py-0.5 rounded-full"
          :class="activeTab === tab.key ? 'bg-navy/10 text-navy' : 'bg-gray-100 text-gray-500'"
        >{{ tab.count }}</span>
      </button>
    </div>

    <!-- ── Tab: All / Active / Expired — Lease table ── -->
    <div v-if="activeTab !== 'draft'" class="card overflow-hidden">
      <div v-if="loading" class="p-6 space-y-3 animate-pulse">
        <div v-for="i in 4" :key="i" class="h-14 bg-gray-100 rounded-lg"></div>
      </div>

      <EmptyState
        v-else-if="!filteredLeases.length"
        :title="activeTab === 'all' ? 'No leases yet' : `No ${activeTab} leases`"
        :description="activeTab === 'all' ? 'Import one from a PDF or create manually to get started.' : ''"
        :icon="FileText"
      />

      <div v-else class="divide-y divide-gray-200">
        <template v-for="([propName, propLeases]) in filteredGroupedLeases" :key="propName">

          <!-- Property group header -->
          <div class="flex items-center gap-2.5 px-5 py-2.5 bg-gray-50 border-b border-gray-100">
            <Home :size="13" class="text-gray-400 flex-shrink-0" />
            <span class="text-xs font-semibold text-gray-600">{{ propName }}</span>
            <span class="text-micro text-gray-400">· {{ propLeases.length }} lease{{ propLeases.length !== 1 ? 's' : '' }}</span>
          </div>

        <div v-for="lease in propLeases" :key="lease.id" class="border-b border-gray-100 last:border-0">

          <!-- Collapsed row -->
          <div
            class="flex items-center gap-4 px-5 py-3.5 cursor-pointer hover:bg-gray-50/60 transition-colors select-none border-l-2"
            :class="[expanded.includes(lease.id) ? 'bg-slate-50' : '', leaseLineClass(lease)]"
            @click="toggle(lease.id)"
          >
            <!-- Dates -->
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
                  class="inline-flex items-center px-1.5 py-0.5 rounded text-micro font-medium bg-gray-100 text-gray-500">
                  +{{ lease.all_tenant_names.length - 1 }} more
                </span>
              </div>
              <div class="text-xs text-gray-400 mt-0.5 truncate">
                {{ lease.unit_label?.split(' — ')[1] ?? lease.unit_label }}
                <span class="mx-1 text-gray-300">·</span>
                <span class="font-mono">{{ lease.lease_number }}</span>
              </div>
            </div>

            <!-- Live signing signer chips -->
            <div v-if="liveSigners(lease.id).length" class="hidden sm:flex items-center gap-1 flex-shrink-0">
              <div
                v-for="signer in liveSigners(lease.id)"
                :key="signer.name"
                class="flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 text-[11px] font-medium"
                :title="`${signer.name}: ${signer.status}`"
              >
                <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" :class="signerDot(signer.status)"></span>
                {{ signer.name }}
              </div>
            </div>

            <!-- Rent -->
            <div class="text-sm font-semibold text-gray-800 flex-shrink-0 tabular-nums">
              R{{ Number(lease.monthly_rent).toLocaleString() }}
            </div>

            <!-- Status + signing CTA -->
            <div class="flex items-center gap-1.5 flex-shrink-0">
              <span :class="statusBadge(lease.status)">{{ lease.status }}</span>
              <button
                v-if="signingNarrative(lease.id).label === 'Needs signing' && lease.status === 'active'"
                class="flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-navy/10 text-navy hover:bg-navy hover:text-white transition-colors"
                @click.stop="expandAndSign(lease.id)"
                aria-label="Send for signing"
              >
                <FileSignature :size="11" />
                Send for signing
              </button>
              <span
                v-else
                :class="signingNarrative(lease.id).badge"
                class="text-micro"
              >{{ signingNarrative(lease.id).label }}</span>
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
                  class="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-navy text-white text-micro font-bold flex items-center justify-center">
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
          <div v-if="expanded.includes(lease.id)" class="bg-slate-50 border-t-2 border-b-2 border-navy/10 px-5 py-4">
            <div class="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-4">
              <!-- Left column -->
              <div class="space-y-4">
                <!-- People card -->
                <div class="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
                  <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Tenants — jointly &amp; severally liable</div>
                  <div class="flex flex-wrap gap-2">
                    <div
                      v-for="(name, i) in (lease.all_tenant_names?.length ? lease.all_tenant_names : [lease.tenant_name])"
                      :key="i"
                      class="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg"
                    >
                      <div class="w-5 h-5 rounded-full bg-navy/10 flex items-center justify-center text-navy text-micro font-bold flex-shrink-0">
                        {{ i + 1 }}
                      </div>
                      <span class="text-sm text-gray-800 font-medium">{{ name }}</span>
                    </div>
                  </div>
                  <div v-if="lease.occupants?.length" class="pt-2 border-t border-gray-100">
                    <div class="text-xs text-gray-400 mb-1.5">Occupants</div>
                    <div class="flex flex-wrap gap-1.5">
                      <span
                        v-for="oc in lease.occupants"
                        :key="oc.id"
                        class="inline-flex items-center gap-1 px-2 py-1 bg-gray-50 rounded text-xs text-gray-600"
                      >
                        <Users :size="10" class="text-gray-400" />
                        {{ oc.person.full_name }}
                        <span v-if="oc.relationship_to_tenant" class="text-gray-400">· {{ oc.relationship_to_tenant }}</span>
                      </span>
                    </div>
                  </div>
                </div>

                <!-- Terms card -->
                <div class="bg-white rounded-xl border border-gray-200 p-4">
                  <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Lease terms</div>
                  <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div>
                      <div class="text-xs text-gray-400">Monthly rent</div>
                      <div class="text-sm font-semibold text-gray-900">R{{ Number(lease.monthly_rent).toLocaleString() }}</div>
                    </div>
                    <div>
                      <div class="text-xs text-gray-400">Deposit</div>
                      <div class="text-sm font-semibold text-gray-900">R{{ Number(lease.deposit).toLocaleString() }}</div>
                    </div>
                    <div>
                      <div class="text-xs text-gray-400">Period</div>
                      <div class="text-sm font-semibold text-gray-900">{{ leasePeriodMonths(lease.start_date, lease.end_date) }}</div>
                      <div class="text-micro text-gray-400">{{ formatDate(lease.start_date) }} → {{ formatDate(lease.end_date) }}</div>
                    </div>
                    <div>
                      <div class="text-xs text-gray-400">Payment ref</div>
                      <div class="text-sm font-semibold text-gray-900 font-mono">{{ lease.payment_reference || '—' }}</div>
                    </div>
                  </div>
                  <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3 pt-3 border-t border-gray-100">
                    <div>
                      <div class="text-xs text-gray-400">Water</div>
                      <div class="text-sm text-gray-700">{{ lease.water_included ? `Included (${lease.water_limit_litres?.toLocaleString()} L)` : 'Excluded' }}</div>
                    </div>
                    <div>
                      <div class="text-xs text-gray-400">Electricity</div>
                      <div class="text-sm text-gray-700">{{ lease.electricity_prepaid ? 'Prepaid' : 'Included' }}</div>
                    </div>
                    <div>
                      <div class="text-xs text-gray-400">Notice period</div>
                      <div class="text-sm text-gray-700">{{ lease.notice_period_days }} days</div>
                    </div>
                    <div>
                      <div class="text-xs text-gray-400">Max occupants</div>
                      <div class="text-sm text-gray-700">{{ lease.max_occupants }}</div>
                    </div>
                  </div>
                </div>

                <!-- E-Signing inline -->
                <div class="bg-white rounded-xl border border-gray-200 p-4">
                  <ESigningPanel
                    :ref="(el: any) => { if (el) signingPanelRefs[lease.id] = el }"
                    :key="lease.id"
                    :lease-id="lease.id"
                    :lease-tenants="leaseTenants(lease)"
                    :lease-data="lease"
                    :auto-open="Number(route.query.expand) === lease.id && route.query.sign === '1'"
                  />
                </div>
              </div>

              <!-- Right column: actions + documents -->
              <div class="space-y-4">
                <div class="bg-white rounded-xl border border-gray-200 p-4 space-y-2">
                  <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Actions</div>
                  <button @click.stop="openBuilderFromLease(lease.id)" class="btn-ghost btn-xs w-full justify-start" title="Renew or rebuild this lease with AI">
                    <FileSignature :size="13" /> Renew lease
                  </button>
                  <button @click.stop="editingLease = lease; showEdit = true" class="btn-ghost btn-xs w-full justify-start">
                    <Pencil :size="13" /> Edit details
                  </button>
                  <button @click.stop="deleteLease(lease)" :disabled="deletingId === lease.id" class="btn-danger btn-xs w-full justify-start">
                    <Loader2 v-if="deletingId === lease.id" :size="13" class="animate-spin" />
                    <Trash2 v-else :size="13" />
                    Delete lease
                  </button>
                </div>

                <div class="bg-white rounded-xl border border-gray-200 p-4">
                  <div class="flex items-center justify-between mb-3">
                    <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      Documents ({{ lease.document_count ?? 0 }})
                    </div>
                    <button @click.stop="openDocs(lease)" class="text-xs text-navy hover:underline">Manage</button>
                  </div>
                  <div v-if="lease.documents?.length" class="space-y-1.5">
                    <a
                      v-for="doc in lease.documents" :key="doc.id"
                      :href="doc.file_url" target="_blank"
                      class="flex items-center gap-2 px-2.5 py-2 rounded-lg hover:bg-gray-50 transition-colors text-xs text-gray-700 group"
                    >
                      <FileText :size="13" class="text-gray-400 group-hover:text-navy flex-shrink-0" />
                      <span class="truncate">{{ doc.description || doc.document_type.replace('_', ' ') }}</span>
                      <Download :size="11" class="text-gray-300 group-hover:text-navy ml-auto flex-shrink-0" />
                    </a>
                  </div>
                  <p v-else class="text-xs text-gray-400">No documents attached</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        </template>

        <!-- Expired leases toggle (All tab only) -->
        <div
          v-if="activeTab === 'all' && expiredCount > 0"
          class="flex items-center justify-center gap-2 px-5 py-3 border-t border-gray-100 cursor-pointer hover:bg-navy/5 transition-colors select-none group"
          @click="showExpiredInAll = !showExpiredInAll"
        >
          <ChevronDown
            :size="13"
            class="text-navy transition-transform duration-200"
            :class="showExpiredInAll ? 'rotate-180' : ''"
          />
          <span class="text-xs text-navy font-semibold group-hover:underline">
            {{ showExpiredInAll ? 'Hide' : 'Show' }} {{ expiredCount }} expired lease{{ expiredCount !== 1 ? 's' : '' }}
          </span>
        </div>

      </div>
    </div>

    <!-- ── Tab: Draft — Builder sessions ── -->
    <div v-if="activeTab === 'draft'" class="card overflow-hidden">
      <div v-if="loadingDrafts" class="p-6 space-y-3 animate-pulse">
        <div v-for="i in 3" :key="i" class="h-14 bg-gray-100 rounded-lg"></div>
      </div>

      <EmptyState
        v-else-if="!drafts.length"
        title="No drafts yet"
        description="Start building a new lease to save your first draft."
        :icon="FolderOpen"
      >
        <button class="btn-primary btn-sm" @click="router.push('/leases/build')">
          <Plus :size="14" /> New Lease
        </button>
      </EmptyState>

      <div v-else class="divide-y divide-gray-100">
        <div
          v-for="d in drafts" :key="d.id"
          class="flex items-center gap-4 px-5 py-3.5 hover:bg-gray-50/60 transition-colors"
        >
          <!-- Summary -->
          <div class="flex-1 min-w-0">
            <div class="font-medium text-sm text-gray-900 truncate">{{ d.summary || 'Untitled draft' }}</div>
            <div class="text-xs text-gray-400 mt-0.5">
              Last edited {{ formatDraftDate(d.updated_at) }}
            </div>
          </div>

          <!-- Status -->
          <span class="badge-amber text-micro flex-shrink-0">{{ d.status }}</span>

          <!-- Actions -->
          <div class="flex items-center gap-1.5 flex-shrink-0">
            <button
              class="btn-primary btn-xs"
              @click="router.push(`/leases/build?draft=${d.id}`)"
            >
              Resume
            </button>
            <button
              class="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
              title="Delete draft"
              @click="deleteDraft(d.id)"
            >
              <Trash2 :size="14" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Import wizard -->
    <ImportLeaseWizard v-if="showImport" @close="showImport = false" @done="onImportDone" />

    <!-- Edit drawer -->
    <EditLeaseDrawer
      v-if="showEdit && editingLease"
      :lease="editingLease"
      @close="showEdit = false"
      @done="onEditDone"
    />

    <!-- Documents Drawer -->
    <BaseDrawer :open="docsDrawer" size="sm" @close="docsDrawer = false">
      <template #header>
        <div>
          <div class="font-semibold text-gray-900 text-sm">Documents</div>
          <div class="text-xs text-gray-500">{{ selectedLease?.all_tenant_names?.join(', ') || selectedLease?.tenant_name }}</div>
        </div>
      </template>

      <div class="p-5 space-y-4">
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
    </BaseDrawer>

    <!-- Manual Create Lease Dialog -->
    <BaseModal :open="createDialog" title="New Lease" size="lg" @close="createDialog = false">
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

      <template #footer>
        <button class="btn-ghost" @click="createDialog = false">Cancel</button>
        <button class="btn-primary" :disabled="saving" @click="createLease">
          <Loader2 v-if="saving" :size="14" class="animate-spin" />
          Create Lease
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onActivated, onDeactivated, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../api'
import { Plus, Paperclip, Download, Loader2, Sparkles, ChevronDown, FileText, Users, Home, Pencil, Trash2, FileSignature, FolderOpen } from 'lucide-vue-next'
import ImportLeaseWizard from './ImportLeaseWizard.vue'
import EditLeaseDrawer from './EditLeaseDrawer.vue'
import ESigningPanel from './ESigningPanel.vue'
import EmptyState from '../../components/EmptyState.vue'
import BaseDrawer from '../../components/BaseDrawer.vue'
import BaseModal from '../../components/BaseModal.vue'
import { useToast } from '../../composables/useToast'

const route = useRoute()
const router = useRouter()
const toast = useToast()

// ── Tabs ──
type TabKey = 'all' | 'draft' | 'active' | 'expired'
const validTabs: TabKey[] = ['all', 'draft', 'active', 'expired']
const qTab = route.query.tab as string | undefined
const activeTab = ref<TabKey>(validTabs.includes(qTab as TabKey) ? (qTab as TabKey) : 'all')

const tabs = computed(() => [
  { key: 'all' as const, label: 'All', count: leases.value.length || null },
  { key: 'draft' as const, label: 'Draft', count: drafts.value.length || null },
  { key: 'active' as const, label: 'Active', count: leases.value.filter(l => l.status === 'active').length || null },
  { key: 'expired' as const, label: 'Expired', count: leases.value.filter(l => l.status === 'expired' || l.status === 'terminated').length || null },
])

// ── Lease state ──
const loading = ref(true)
const saving = ref(false)
const showImport = ref(false)
const showEdit = ref(false)
const editingLease = ref<any>(null)
const leases = ref<any[]>([])
const units = ref<any[]>([])
const expanded = ref<number[]>([])
const deletingId = ref<number | null>(null)

// ── Draft state ──
const loadingDrafts = ref(false)
const drafts = ref<any[]>([])

const showExpiredInAll = ref(false)
const expiredCount = computed(() =>
  leases.value.filter(l => l.status === 'expired' || l.status === 'terminated').length
)

// Filter leases by active tab
const filteredLeases = computed(() => {
  if (activeTab.value === 'active') return leases.value.filter(l => l.status === 'active')
  if (activeTab.value === 'expired') return leases.value.filter(l => l.status === 'expired' || l.status === 'terminated')
  // 'all' tab: hide expired/terminated by default, reveal with toggle
  const nonExpired = leases.value.filter(l => l.status !== 'expired' && l.status !== 'terminated')
  const expired = leases.value.filter(l => l.status === 'expired' || l.status === 'terminated')
  return showExpiredInAll.value ? [...nonExpired, ...expired] : nonExpired
})

// Group filtered leases by property
const filteredGroupedLeases = computed(() => {
  const map = new Map<string, any[]>()
  for (const lease of filteredLeases.value) {
    const prop = lease.unit_label?.split(' — ')[0] ?? 'Unknown Property'
    if (!map.has(prop)) map.set(prop, [])
    map.get(prop)!.push(lease)
  }
  for (const group of map.values()) {
    group.sort((a: any, b: any) => new Date(b.start_date).getTime() - new Date(a.start_date).getTime())
  }
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

async function initView() {
  await Promise.all([loadLeases(), loadUnits(), loadDrafts()])
  // Deep-link: auto-expand a lease from query params
  const expandId = Number(route.query.expand)
  if (expandId && leases.value.some((l: any) => l.id === expandId)) {
    if (!expanded.value.includes(expandId)) expanded.value.push(expandId)
  }
}

onActivated(() => {
  initView()
  connectLeasesSocket()
})

onDeactivated(() => {
  disconnectLeasesSocket()
})

// ── Real-time lease updates via WebSocket ──
let leasesSocket: WebSocket | null = null
let leasesReconnectTimer: ReturnType<typeof setTimeout> | null = null

function getWsBase() {
  const env = import.meta.env as any
  if (env.VITE_WS_URL) return env.VITE_WS_URL
  const apiUrl = env.VITE_API_URL || ''
  if (apiUrl) {
    // Derive WS URL from API URL (http://localhost:8000/api/v1 → ws://localhost:8000)
    return apiUrl.replace(/^http/, 'ws').replace(/\/api\/v1\/?$/, '')
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}`
}

function connectLeasesSocket() {
  // Already connected / connecting — no-op
  if (leasesSocket && (leasesSocket.readyState === WebSocket.OPEN || leasesSocket.readyState === WebSocket.CONNECTING)) {
    return
  }
  const host = getWsBase()
  const token = localStorage.getItem('access_token') || ''
  try {
    leasesSocket = new WebSocket(`${host}/ws/leases/updates/?token=${token}`)
  } catch (err) {
    console.warn('Failed to open leases WebSocket', err)
    scheduleLeasesReconnect()
    return
  }

  leasesSocket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.event === 'lease_created' || data.event === 'lease_updated') {
        // Simple + safe: refetch the list. Cheap (single `/leases/` call)
        // and guarantees the UI stays in sync with server-side filters/annotations.
        loadLeases()
      }
    } catch {
      // Ignore malformed frames
    }
  }

  leasesSocket.onerror = () => {
    console.warn('Leases WebSocket errored')
  }

  leasesSocket.onclose = () => {
    scheduleLeasesReconnect()
  }
}

function scheduleLeasesReconnect() {
  if (leasesReconnectTimer) return
  leasesReconnectTimer = setTimeout(() => {
    leasesReconnectTimer = null
    // Only reconnect if we're still the active view
    if (!leasesSocket || leasesSocket.readyState === WebSocket.CLOSED) {
      connectLeasesSocket()
    }
  }, 5000)
}

function disconnectLeasesSocket() {
  if (leasesReconnectTimer) {
    clearTimeout(leasesReconnectTimer)
    leasesReconnectTimer = null
  }
  if (leasesSocket) {
    // Clear close handler first so it doesn't schedule a reconnect
    leasesSocket.onclose = null
    leasesSocket.onmessage = null
    leasesSocket.onerror = null
    try { leasesSocket.close() } catch { /* ignore */ }
    leasesSocket = null
  }
}

// ── Signing data (full submission objects, not just status strings) ──
const signingData = ref(new Map<number, any>())
const signingPanelRefs = ref<Record<number, any>>({})

async function loadLeases() {
  loading.value = true
  try {
    const { data } = await api.get('/leases/')
    leases.value = data.results ?? data
  } finally {
    loading.value = false
  }
  loadSigningStatuses()
}

async function loadSigningStatuses() {
  const ids = leases.value.map((l: any) => l.id)
  const results = await Promise.allSettled(
    ids.map(id =>
      api.get('/esigning/submissions/', { params: { lease_id: id } })
        .then(({ data }: any) => ({ id, submissions: data.results ?? data }))
    )
  )
  const next = new Map<number, any>()
  for (const r of results) {
    if (r.status !== 'fulfilled') continue
    const { id, submissions } = r.value
    next.set(id, submissions[0] ?? null)
  }
  signingData.value = next
}

function signingNarrative(leaseId: number): { label: string; badge: string } {
  const sub = signingData.value.get(leaseId)
  if (!sub) return { label: 'Needs signing', badge: 'badge-gray' }

  const signers = sub.signers ?? []
  const firstName = (name: string) => name?.split(' ')[0] || 'Signer'

  if (sub.status === 'completed') return { label: 'All signed', badge: 'badge-green' }
  if (sub.status === 'declined') {
    const who = signers.find((s: any) => (s.status ?? '').toLowerCase() === 'declined')
    return { label: who ? `${firstName(who.name)} declined` : 'Declined', badge: 'badge-red' }
  }
  if (sub.status === 'expired') return { label: 'Signing expired', badge: 'badge-gray' }

  // Active: find the most interesting signer status
  const viewing = signers.find((s: any) => (s.status ?? '').toLowerCase() === 'opened')
  if (viewing) return { label: `${firstName(viewing.name)} is reviewing`, badge: 'badge-blue' }

  const unsigned = signers.filter((s: any) => {
    const st = (s.status ?? '').toLowerCase()
    return st !== 'completed' && st !== 'signed'
  })
  if (unsigned.length === 1) return { label: `Sent to ${firstName(unsigned[0].name)}`, badge: 'badge-amber' }
  if (unsigned.length > 1) return { label: `Sent to ${unsigned.length} signers`, badge: 'badge-amber' }

  return { label: 'Signing pending', badge: 'badge-amber' }
}

function liveSigners(leaseId: number): { name: string; status: string }[] {
  const sub = signingData.value.get(leaseId)
  if (!sub || sub.status === 'expired') return []
  return (sub.signers ?? []).map((s: any) => ({
    name: s.name?.split(' ')[0] || 'Signer',
    status: (s.status ?? 'pending').toLowerCase(),
  }))
}

function signerDot(status: string): string {
  if (status === 'completed' || status === 'signed') return 'bg-emerald-500'
  if (status === 'opened') return 'bg-blue-500'
  if (status === 'declined') return 'bg-red-500'
  return 'bg-gray-300'
}

function leaseTenants(lease: any) {
  const co = (lease.co_tenants ?? []).map((ct: any) => ct.person ?? ct)
  const primary = lease.primary_tenant_detail
  return primary ? [primary, ...co] : co
}

async function loadUnits() {
  const { data } = await api.get('/properties/units/')
  units.value = (data.results ?? data).map((u: any) => ({
    ...u,
    label: `${u.property_name ?? u.property} — Unit ${u.unit_number}`,
  }))
}

async function loadDrafts() {
  loadingDrafts.value = true
  try {
    const { data } = await api.get('/leases/builder/drafts/')
    drafts.value = data
  } catch { /* silent */ }
  finally { loadingDrafts.value = false }
}

async function deleteDraft(id: number) {
  if (!confirm('Delete this draft? This cannot be undone.')) return
  try {
    await api.delete(`/leases/builder/drafts/${id}/`)
    drafts.value = drafts.value.filter(d => d.id !== id)
    toast.success('Draft deleted')
  } catch {
    toast.error('Failed to delete draft')
  }
}

function toggle(id: number) {
  const idx = expanded.value.indexOf(id)
  if (idx === -1) expanded.value.push(id)
  else expanded.value.splice(idx, 1)
}

function expandAndSign(id: number) {
  if (!expanded.value.includes(id)) expanded.value.push(id)
  nextTick(() => signingPanelRefs.value[id]?.openModal())
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
    toast.success('Lease created successfully')
    await loadLeases()
  } catch (e: any) {
    toast.error(e?.response?.data?.detail ?? 'Failed to create lease')
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
    toast.success('Lease deleted')
  } catch (e: any) {
    const d = e?.response?.data?.detail ?? e?.response?.data ?? e?.message
    toast.error(typeof d === 'string' ? d : 'Could not delete lease.')
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
    const leaseIdx = leases.value.findIndex(l => l.id === selectedLease.value.id)
    if (leaseIdx !== -1) {
      leases.value[leaseIdx] = { ...leases.value[leaseIdx], document_count: (leases.value[leaseIdx].document_count ?? 0) + 1, documents: [data, ...(leases.value[leaseIdx].documents ?? [])] }
    }
    uploadFile.value = null
    uploadDescription.value = ''
    if (fileInputRef.value) fileInputRef.value.value = ''
    toast.success('Document uploaded')
  } catch (e: any) {
    toast.error('Failed to upload document')
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
    toast.success('Document deleted')
  } catch (e: any) {
    toast.error('Could not delete document.')
  }
}

async function onImportDone() {
  showImport.value = false
  toast.success('Lease imported successfully')
  await loadLeases()
}

function openBuilderFromLease(_leaseId: number) {
  router.push('/leases/build')
}

async function onEditDone(_updated: any) {
  showEdit.value = false
  editingLease.value = null
  toast.success('Lease updated')
  await loadLeases()
}

function statusBadge(s: string) {
  return { active: 'badge-green', pending: 'badge-amber', expired: 'badge-red', terminated: 'badge-gray' }[s] ?? 'badge-gray'
}

function leaseDaysLeft(lease: any): number {
  if (!lease.end_date) return Infinity
  return Math.ceil((new Date(lease.end_date).getTime() - Date.now()) / 86400000)
}

function leaseLineClass(lease: any): string {
  if (lease.status === 'expired' || lease.status === 'terminated') return 'border-l-gray-200'
  const days = leaseDaysLeft(lease)
  const isSigned = signingData.value.get(lease.id)?.status === 'completed'
  if (!isSigned) return 'border-l-gray-300'
  if (days <= 30) return 'border-l-danger-400'
  if (days <= 90) return 'border-l-warning-400'
  return 'border-l-success-400'
}
function docTypeBadge(t: string) {
  return { signed_lease: 'badge-purple', id_copy: 'badge-blue', other: 'badge-gray' }[t] ?? 'badge-gray'
}
function formatDate(d: string) {
  return d ? new Date(d).toLocaleDateString('en-ZA') : '—'
}
function formatDraftDate(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function leasePeriodMonths(start: string, end: string): string {
  if (!start || !end) return '—'
  const s = new Date(start)
  const e = new Date(end)
  const months = (e.getFullYear() - s.getFullYear()) * 12 + (e.getMonth() - s.getMonth())
  return months > 0 ? `${months} month${months !== 1 ? 's' : ''}` : '—'
}
</script>
