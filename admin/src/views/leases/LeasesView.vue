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
        <button class="btn-primary" @click="addLeaseStartMode = 'form'; editingTemplateId = null; showAddLease = true">
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
                <div class="font-semibold text-gray-900">{{ formatDate(lease.start_date) }} → {{ formatDate(lease.end_date) }}</div>
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

            <!-- Events Timeline -->
            <div>
              <div class="flex items-center justify-between mb-2.5">
                <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-widest">Upcoming Events</div>
                <button @click.stop="generateEvents(lease)" :disabled="generatingEvents === lease.id" class="btn-ghost text-xs px-2 py-1">
                  <Loader2 v-if="generatingEvents === lease.id" :size="11" class="animate-spin" />
                  <CalendarDays v-else :size="11" />
                  Generate
                </button>
              </div>
              <div v-if="leaseEvents[lease.id] === undefined" class="text-xs text-gray-400">
                Click "Generate" to auto-create calendar events
              </div>
              <div v-else-if="!leaseEvents[lease.id]?.length" class="text-xs text-gray-400">No upcoming events</div>
              <div v-else class="flex flex-col gap-1">
                <div
                  v-for="ev in leaseEvents[lease.id].slice(0, 5)"
                  :key="ev.id"
                  class="flex items-center gap-3 px-3 py-2 bg-white rounded-xl border border-gray-100 text-xs"
                >
                  <div class="w-2 h-2 rounded-full flex-shrink-0" :style="{ background: eventColor(ev.event_type) }"></div>
                  <div class="flex-1 font-medium text-gray-800">{{ ev.title }}</div>
                  <div class="text-gray-400 tabular-nums">{{ formatDate(ev.date) }}</div>
                  <span :class="eventStatusBadge(ev.status)" class="text-[10px]">{{ ev.status }}</span>
                </div>
              </div>
            </div>

            <!-- Onboarding Checklist -->
            <div v-if="onboardingSteps[lease.id]?.length">
              <div class="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-2.5">
                Onboarding ({{ onboardingSteps[lease.id].filter((s: any) => s.is_completed).length }}/{{ onboardingSteps[lease.id].length }})
              </div>
              <div class="grid grid-cols-2 gap-1.5">
                <div
                  v-for="step in onboardingSteps[lease.id]"
                  :key="step.id"
                  class="flex items-center gap-2 px-3 py-2 bg-white rounded-xl border border-gray-100 cursor-pointer hover:border-navy/20 transition-colors"
                  @click.stop="toggleOnboarding(lease, step)"
                >
                  <div
                    class="w-4 h-4 rounded flex items-center justify-center flex-shrink-0 border transition-colors"
                    :class="step.is_completed ? 'bg-emerald-500 border-emerald-500' : 'border-gray-300'"
                  >
                    <Check v-if="step.is_completed" :size="10" class="text-white" />
                  </div>
                  <span class="text-xs text-gray-700 leading-tight" :class="step.is_completed ? 'line-through text-gray-400' : ''">
                    {{ step.title }}
                  </span>
                </div>
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
        <div v-for="t in templates" :key="t.id" class="flex items-start gap-4 px-5 py-4">
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
      </div>
    </div>

    <!-- Import wizard (full screen) -->
    <ImportLeaseWizard v-if="showImport" @close="showImport = false" @done="onImportDone" />

    <!-- Template editor (full screen 3-panel) -->
    <TemplateEditorView
      v-if="showTemplateEditor && templateEditorId"
      :template-id="templateEditorId"
      @close="showTemplateEditor = false; templateEditorId = null"
    />

    <LeaseBuilderView
      v-if="showAddLease"
      :start-mode="addLeaseStartMode"
      :template-id="editingTemplateId"
      @close="showAddLease = false; editingTemplateId = null"
      @done="onAddLeaseDone"
    />

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
import api from '../../api'
import { Plus, Paperclip, X, Download, Loader2, Sparkles, ChevronDown, FileText, Users, Home, Pencil, Trash2, FileSignature, AlertCircle, CalendarDays, Check } from 'lucide-vue-next'
import ImportLeaseWizard from './ImportLeaseWizard.vue'
import EditLeaseDrawer from './EditLeaseDrawer.vue'
import LeaseBuilderView from './LeaseBuilderView.vue'
import TemplateEditorView from './TemplateEditorView.vue'

const loading = ref(true)
const saving = ref(false)
const activeTab = ref<'leases' | 'templates'>('leases')
const showImport = ref(false)
const showAddLease = ref(false)
const addLeaseStartMode = ref<'form' | 'chat'>('form')
const editingTemplateId = ref<number | null>(null)
const showTemplateEditor = ref(false)
const templateEditorId = ref<number | null>(null)
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

// Events & Onboarding
const leaseEvents = ref<Record<number, any[]>>({})
const onboardingSteps = ref<Record<number, any[]>>({})
const generatingEvents = ref<number | null>(null)

const EVENT_COLORS: Record<string, string> = {
  contract_start: '#1e3a5f', contract_end: '#1e3a5f',
  deposit_due: '#7c3aed', first_rent: '#2563eb', rent_due: '#2563eb',
  inspection_in: '#d97706', inspection_out: '#d97706', inspection_routine: '#d97706',
  notice_deadline: '#dc2626', renewal_review: '#059669', custom: '#6b7280',
}

function eventColor(type: string) {
  return EVENT_COLORS[type] ?? '#6b7280'
}

function eventStatusBadge(s: string) {
  return { upcoming: 'badge-gray', due: 'badge-amber', completed: 'badge-green', overdue: 'badge-red', cancelled: 'badge-gray' }[s] ?? 'badge-gray'
}

async function generateEvents(lease: any) {
  generatingEvents.value = lease.id
  try {
    await api.post(`/leases/${lease.id}/generate-events/`)
    const today = new Date().toISOString().slice(0, 10)
    const [evRes, obRes] = await Promise.all([
      api.get(`/leases/${lease.id}/events/`),
      api.get(`/leases/${lease.id}/onboarding/`),
    ])
    leaseEvents.value[lease.id] = (evRes.data as any[]).filter(e => e.date >= today)
    onboardingSteps.value[lease.id] = obRes.data
  } catch (e: any) {
    alert(e?.response?.data?.detail ?? 'Could not generate events.')
  } finally {
    generatingEvents.value = null
  }
}

async function toggleOnboarding(lease: any, step: any) {
  const newVal = !step.is_completed
  try {
    await api.patch(`/leases/${lease.id}/onboarding/${step.id}/`, { is_completed: newVal })
    step.is_completed = newVal
    if (newVal) step.completed_at = new Date().toISOString()
  } catch {
    // revert on error
    step.is_completed = !newVal
  }
}

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

async function toggle(id: number) {
  const idx = expanded.value.indexOf(id)
  if (idx === -1) {
    expanded.value.push(id)
    // Load events & onboarding if not already loaded
    if (leaseEvents.value[id] === undefined) {
      try {
        const today = new Date().toISOString().slice(0, 10)
        const [evRes, obRes] = await Promise.all([
          api.get(`/leases/${id}/events/`),
          api.get(`/leases/${id}/onboarding/`),
        ])
        leaseEvents.value[id] = (evRes.data as any[]).filter((e: any) => e.date >= today)
        onboardingSteps.value[id] = obRes.data
      } catch {
        // Non-fatal — events just won't show
      }
    }
  } else {
    expanded.value.splice(idx, 1)
  }
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

async function onAddLeaseDone() {
  showAddLease.value = false
  editingTemplateId.value = null
  await loadLeases()
}

function openBuilderFromLease(_leaseId: number) {
  addLeaseStartMode.value = 'form'
  editingTemplateId.value = null
  showAddLease.value = true
}

function editTemplateWithAI(templateId: number) {
  templateEditorId.value = templateId
  showTemplateEditor.value = true
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
</script>
