<template>
  <div class="space-y-4">

    <!-- Header row -->
    <div class="flex items-center justify-between">
      <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide">E-Signing</div>
      <button class="btn-ghost text-xs px-2 py-1" @click="openCreateModal">
        <Plus :size="12" />
        New signing request
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center gap-2 text-sm text-gray-400 py-3">
      <Loader2 :size="14" class="animate-spin" />
      Loading…
    </div>

    <!-- Empty state -->
    <div v-else-if="!requests.length" class="py-4 text-center">
      <div class="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center mx-auto mb-2">
        <PenLine :size="18" class="text-gray-400" />
      </div>
      <p class="text-sm text-gray-500">No signing requests yet.</p>
      <p class="text-xs text-gray-400 mt-0.5">Create one to send this lease for e-signature.</p>
    </div>

    <!-- Signing request cards -->
    <div v-else class="space-y-3">
      <div
        v-for="req in requests"
        :key="req.id"
        class="border border-gray-200 rounded-xl overflow-hidden"
      >
        <!-- Request header -->
        <div class="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-100">
          <div class="flex items-center gap-2">
            <span
              class="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full"
              :class="statusClass(req.status)"
            >
              <span class="w-1.5 h-1.5 rounded-full" :class="statusDot(req.status)" />
              {{ req.status.replace('_', ' ') }}
            </span>
            <span class="text-xs text-gray-500">{{ formatDate(req.created_at) }}</span>
          </div>
          <button
            v-if="req.status !== 'completed'"
            class="btn-ghost text-xs px-2 py-1"
            :disabled="resendingId === req.id"
            @click="resendInvites(req.id)"
          >
            <Loader2 v-if="resendingId === req.id" :size="11" class="animate-spin" />
            <Send v-else :size="11" />
            Resend
          </button>
        </div>

        <!-- Parties -->
        <div class="divide-y divide-gray-100">
          <div
            v-for="party in req.parties"
            :key="party.id"
            class="flex items-center justify-between px-4 py-2.5"
          >
            <div class="flex items-center gap-2.5 min-w-0">
              <div class="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 text-xs font-bold text-gray-500">
                {{ initials(party.name) }}
              </div>
              <div class="min-w-0">
                <div class="text-sm font-medium text-gray-900 truncate">{{ party.name }}</div>
                <div class="text-xs text-gray-400 truncate">{{ party.role }} · {{ party.email }}</div>
              </div>
            </div>
            <span
              class="text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0 ml-2"
              :class="partyStatusClass(party.status)"
            >
              {{ party.status }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Create Request Modal ───────────────────────────────────────────── -->
    <div
      v-if="showCreateModal"
      class="fixed inset-0 z-[60] flex items-center justify-center p-4"
      @click.self="showCreateModal = false"
    >
      <div class="absolute inset-0 bg-black/40" @click="showCreateModal = false" />
      <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-5">
        <div class="flex items-center justify-between">
          <div class="font-semibold text-gray-900">New Signing Request</div>
          <button class="text-gray-400 hover:text-gray-600" @click="showCreateModal = false"><X :size="16" /></button>
        </div>

        <!-- Template selector -->
        <div class="space-y-1.5">
          <label class="label">Signing template</label>
          <div v-if="loadingTemplates" class="text-xs text-gray-400 flex items-center gap-1">
            <Loader2 :size="12" class="animate-spin" /> Loading templates…
          </div>
          <select v-else v-model="newRequest.template_id" class="input">
            <option :value="null" disabled>Select a template</option>
            <option v-for="t in signingTemplates" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
          <p v-if="!signingTemplates.length && !loadingTemplates" class="text-xs text-amber-600">
            No signing templates found. Set one up in DocuSeal first.
          </p>
        </div>

        <!-- Parties -->
        <div class="space-y-2">
          <label class="label">Parties</label>
          <div
            v-for="(party, i) in newRequest.parties"
            :key="i"
            class="border border-gray-200 rounded-xl p-3 space-y-2 relative"
          >
            <button class="absolute top-2.5 right-2.5 text-gray-400 hover:text-red-500" @click="newRequest.parties.splice(i, 1)">
              <X :size="12" />
            </button>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <label class="label">Name</label>
                <input v-model="party.name" class="input text-xs" placeholder="Full name" />
              </div>
              <div>
                <label class="label">Role</label>
                <select v-model="party.role" class="input text-xs">
                  <option value="tenant">Tenant</option>
                  <option value="co_tenant">Co-Tenant</option>
                  <option value="guarantor">Guarantor</option>
                  <option value="agent">Agent</option>
                  <option value="landlord">Landlord</option>
                </select>
              </div>
              <div class="col-span-2">
                <label class="label">Email</label>
                <input v-model="party.email" type="email" class="input text-xs" placeholder="email@example.com" />
              </div>
              <div class="col-span-2 flex items-center gap-2">
                <input v-model="party.sign_in_app" type="checkbox" class="rounded" id="`sign-in-app-${i}`" />
                <label :for="`sign-in-app-${i}`" class="text-xs text-gray-600 cursor-pointer">
                  Sign in tenant portal (embed) — otherwise DocuSeal emails a link
                </label>
              </div>
            </div>
          </div>

          <button class="btn-ghost text-xs px-2 py-1.5 w-full" @click="addParty">
            <Plus :size="12" /> Add party
          </button>
        </div>

        <div v-if="createError" class="text-sm text-red-600 flex items-center gap-1.5">
          <AlertCircle :size="13" />
          {{ createError }}
        </div>

        <div class="flex justify-end gap-2 pt-1">
          <button class="btn-ghost" @click="showCreateModal = false">Cancel</button>
          <button class="btn-primary" :disabled="creating || !newRequest.template_id" @click="submitCreateRequest">
            <Loader2 v-if="creating" :size="13" class="animate-spin" />
            {{ creating ? 'Creating…' : 'Send for signing' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'
import { Plus, Loader2, PenLine, X, AlertCircle, Send } from 'lucide-vue-next'

const props = defineProps<{ leaseId: number; leaseTenants?: any[] }>()
const emit = defineEmits<{ signed: [] }>()

// ── Signing requests ──────────────────────────────────────────────────────

const loading = ref(false)
const requests = ref<any[]>([])
const resendingId = ref<number | null>(null)

async function loadRequests() {
  if (!props.leaseId) return
  loading.value = true
  try {
    const { data } = await api.get(`/esigning/requests/?lease_id=${props.leaseId}`)
    requests.value = data.results ?? data
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

async function resendInvites(requestId: number) {
  resendingId.value = requestId
  try {
    await api.post(`/esigning/requests/${requestId}/send/`)
  } finally {
    resendingId.value = null
  }
}

// ── Create request modal ──────────────────────────────────────────────────

const showCreateModal = ref(false)
const creating = ref(false)
const createError = ref('')
const signingTemplates = ref<any[]>([])
const loadingTemplates = ref(false)

const newRequest = ref<{
  template_id: number | null
  parties: { name: string; email: string; role: string; sign_in_app: boolean }[]
}>({
  template_id: null,
  parties: [],
})

async function openCreateModal() {
  createError.value = ''
  newRequest.value = { template_id: null, parties: [] }

  // Pre-populate parties from lease tenants if provided
  if (props.leaseTenants?.length) {
    newRequest.value.parties = props.leaseTenants.map((t: any) => ({
      name: t.person?.full_name ?? t.full_name ?? '',
      email: t.person?.email ?? t.email ?? '',
      role: 'tenant',
      sign_in_app: false,
    }))
  }

  showCreateModal.value = true
  loadingTemplates.value = true
  try {
    const { data } = await api.get('/esigning/templates/')
    signingTemplates.value = data.results ?? data
  } finally {
    loadingTemplates.value = false
  }
}

function addParty() {
  newRequest.value.parties.push({ name: '', email: '', role: 'tenant', sign_in_app: false })
}

async function submitCreateRequest() {
  if (!newRequest.value.template_id) return
  creating.value = true
  createError.value = ''
  try {
    await api.post('/esigning/requests/create/', {
      lease_id: props.leaseId,
      template_id: newRequest.value.template_id,
      parties: newRequest.value.parties,
    })
    showCreateModal.value = false
    await loadRequests()
    emit('signed')
  } catch (e: any) {
    const detail = e?.response?.data?.error ?? e?.response?.data ?? e?.message ?? 'Failed to create request'
    createError.value = typeof detail === 'string' ? detail : JSON.stringify(detail)
  } finally {
    creating.value = false
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────

function statusClass(s: string) {
  if (s === 'completed') return 'bg-emerald-100 text-emerald-700'
  if (s === 'in_progress') return 'bg-blue-100 text-blue-700'
  if (s === 'expired') return 'bg-gray-100 text-gray-600'
  return 'bg-amber-100 text-amber-700'
}

function statusDot(s: string) {
  if (s === 'completed') return 'bg-emerald-500'
  if (s === 'in_progress') return 'bg-blue-500'
  if (s === 'expired') return 'bg-gray-400'
  return 'bg-amber-500'
}

function partyStatusClass(s: string) {
  if (s === 'completed') return 'bg-emerald-100 text-emerald-700'
  if (s === 'opened') return 'bg-blue-100 text-blue-700'
  return 'bg-gray-100 text-gray-600'
}

function formatDate(d: string) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })
}

function initials(name: string) {
  return (name || '?').split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()
}

onMounted(loadRequests)
</script>
