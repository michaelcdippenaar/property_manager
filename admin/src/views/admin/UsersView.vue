<template>
  <div class="space-y-6">
    <PageHeader
      title="Users"
      subtitle="Manage user accounts and roles"
      :crumbs="[{ label: 'Dashboard', to: '/' }, { label: 'Admin' }, { label: 'Users' }]"
    >
      <template #actions>
        <button @click="openInviteModal" class="btn-primary">
          <UserPlus :size="16" />
          Invite User
        </button>
      </template>
    </PageHeader>

    <!-- Filters -->
    <div class="card p-4 flex items-center gap-3">
      <div class="relative flex-1 max-w-xs">
        <Search :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          v-model="search"
          type="text"
          class="input pl-9"
          placeholder="Search by name or email..."
          @input="debouncedLoad"
        />
      </div>
      <select v-model="roleFilter" class="input w-48" @change="loadUsers">
        <option value="">All roles</option>
        <optgroup v-for="(group, key) in ROLE_GROUPS" :key="key" :label="group.label">
          <option v-for="r in group.roles" :key="r.value" :value="r.value">{{ r.label }}</option>
        </optgroup>
      </select>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-400">
        <Loader2 :size="20" class="animate-spin mx-auto" />
      </div>
      <table v-else class="table-wrap">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Agency</th>
            <th>Status</th>
            <th>Last Login</th>
            <th class="!text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td class="font-medium text-gray-900">{{ u.full_name }}</td>
            <td class="text-gray-600">{{ u.email }}</td>
            <td>
              <span :class="roleBadgeClass(u.role)" class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium">
                {{ roleLabel(u.role) }}
              </span>
            </td>
            <td class="text-gray-500">{{ u.agency_name || '—' }}</td>
            <td>
              <span :class="u.is_active ? 'bg-success-100 text-success-700' : 'bg-gray-100 text-gray-500'" class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium">
                {{ u.is_active ? 'Active' : 'Inactive' }}
              </span>
            </td>
            <td class="text-gray-500">{{ u.last_login ? formatDate(u.last_login) : 'Never' }}</td>
            <td class="text-right space-x-1">
              <button @click="editUser(u)" class="text-gray-400 hover:text-navy p-1 rounded">
                <Pencil :size="15" />
              </button>
              <button @click="confirmDelete(u)" class="text-gray-400 hover:text-danger-600 p-1 rounded">
                <Trash2 :size="15" />
              </button>
            </td>
          </tr>
          <tr v-if="!users.length">
            <td colspan="7" class="px-4 py-8 text-center text-gray-400">No users found</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pending Invites -->
    <div v-if="invites.length" class="card overflow-hidden">
      <div class="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
        <h3 class="text-sm font-semibold text-gray-700">Pending Invites</h3>
        <span class="text-xs text-gray-400">{{ invites.length }} awaiting acceptance</span>
      </div>
      <table class="w-full text-sm">
        <thead class="border-b border-gray-100">
          <tr>
            <th class="text-left px-4 py-2 font-medium text-gray-500">Email</th>
            <th class="text-left px-4 py-2 font-medium text-gray-500">Role</th>
            <th class="text-left px-4 py-2 font-medium text-gray-500">Agency</th>
            <th class="text-left px-4 py-2 font-medium text-gray-500">Invited by</th>
            <th class="text-left px-4 py-2 font-medium text-gray-500">Sent</th>
            <th class="text-right px-4 py-2 font-medium text-gray-500">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr v-for="inv in invites" :key="inv.id" class="text-gray-600">
            <td class="px-4 py-2.5">{{ inv.email }}</td>
            <td class="px-4 py-2.5">
              <span :class="roleBadgeClass(inv.role)" class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium">{{ roleLabel(inv.role) }}</span>
            </td>
            <td class="px-4 py-2.5 text-gray-500">{{ inv.agency_name || '—' }}</td>
            <td class="px-4 py-2.5">{{ inv.invited_by || '—' }}</td>
            <td class="px-4 py-2.5 text-gray-400">{{ formatDate(inv.created_at) }}</td>
            <td class="px-4 py-2.5 text-right space-x-1">
              <button
                @click="resendInvite(inv)"
                class="text-gray-400 hover:text-navy p-1 rounded transition-colors"
                :disabled="resendingInviteId === inv.id"
                title="Resend invite"
              >
                <Loader2 v-if="resendingInviteId === inv.id" :size="14" class="animate-spin" />
                <Send v-else :size="14" />
              </button>
              <button
                @click="confirmCancelInvite(inv)"
                class="text-gray-400 hover:text-danger-500 p-1 rounded transition-colors"
                title="Revoke invite"
              >
                <Trash2 :size="14" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Cancel Invite Confirmation Modal -->
    <BaseModal :open="!!cancellingInvite" title="Revoke Invitation" size="sm" @close="cancellingInvite = null">
      <p class="text-sm text-gray-600">
        Are you sure you want to revoke the invitation for
        <strong class="text-gray-800">{{ cancellingInvite?.email }}</strong>?
        If they click the link in their email, they'll see an "Invitation Expired" page.
      </p>
      <div v-if="cancelInviteError" class="text-sm text-danger-600 mt-3">{{ cancelInviteError }}</div>
      <template #footer>
        <button @click="cancellingInvite = null" class="btn-ghost">Keep</button>
        <button @click="cancelInvite" class="btn-danger" :disabled="cancellingInviteLoading">
          <Loader2 v-if="cancellingInviteLoading" :size="15" class="animate-spin" />
          Revoke
        </button>
      </template>
    </BaseModal>

    <!-- Edit Modal -->
    <BaseModal :open="!!editingUser" title="Edit User" size="lg" @close="editingUser = null">
      <div v-if="editingUser" class="space-y-4">
        <div>
          <label class="label">Email</label>
          <input :value="editingUser.email" class="input bg-gray-50" disabled />
        </div>
        <div>
          <label class="label">Role</label>
          <select v-model="editForm.role" class="input">
            <optgroup v-for="(group, key) in ROLE_GROUPS" :key="key" :label="group.label">
              <option v-for="r in group.roles" :key="r.value" :value="r.value">{{ r.label }}</option>
            </optgroup>
          </select>
          <p v-if="roleDescription(editForm.role)" class="text-xs text-gray-400 mt-1">{{ roleDescription(editForm.role) }}</p>
        </div>
        <!-- Agency (read-only) -->
        <div v-if="editingUser.agency_name">
          <label class="label">Agency</label>
          <input :value="editingUser.agency_name" class="input bg-gray-50" disabled />
        </div>
        <!-- Module access for viewer -->
        <div v-if="editForm.role === 'viewer'">
          <label class="label">Module Access</label>
          <div class="grid grid-cols-2 gap-2 mt-1">
            <label v-for="mod in MODULES" :key="mod" class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                :checked="editForm.module_access.includes(mod)"
                @change="toggleModule(editForm.module_access, mod)"
                class="rounded border-gray-300 text-navy focus:ring-navy/30"
              />
              {{ capitalise(mod) }}
            </label>
          </div>
        </div>
        <!-- FFC fields for agent roles -->
        <div v-if="isAgentRole(editForm.role)" class="grid grid-cols-2 gap-4">
          <div>
            <label class="label">FFC Number</label>
            <input v-model="editForm.ffc_number" type="text" class="input" placeholder="F148660" />
          </div>
          <div>
            <label class="label">FFC Category</label>
            <select v-model="editForm.ffc_category" class="input">
              <option value="">— None —</option>
              <option value="estate">Estate Agent</option>
              <option value="managing">Managing Agent</option>
            </select>
          </div>
        </div>
        <!-- Property Assignments for agent roles -->
        <div v-if="isAgentRole(editForm.role)">
          <div class="flex items-center justify-between mb-2">
            <label class="label mb-0 flex items-center gap-1.5">
              <Building2 :size="14" class="text-gray-400" />
              Property Assignments
            </label>
            <button @click="openAddProperty" class="text-xs text-navy hover:text-navy/80 flex items-center gap-1">
              <Plus :size="13" /> Assign Property
            </button>
          </div>
          <!-- Add property inline form -->
          <div v-if="showAddProperty" class="border border-gray-200 rounded-lg p-3 mb-2 space-y-2 bg-gray-50">
            <select v-model="addPropertyForm.property" class="input text-sm">
              <option value="">Select a property...</option>
              <option
                v-for="p in unassignedProperties"
                :key="p.id"
                :value="p.id"
              >{{ p.name }} — {{ p.address }}</option>
            </select>
            <div class="flex gap-2">
              <label class="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
                <input type="radio" v-model="addPropertyForm.assignment_type" value="managing" class="text-navy focus:ring-navy/30" />
                Managing
              </label>
              <label class="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
                <input type="radio" v-model="addPropertyForm.assignment_type" value="estate" class="text-navy focus:ring-navy/30" />
                Estate
              </label>
            </div>
            <div v-if="addPropertyError" class="text-xs text-danger-600">{{ addPropertyError }}</div>
            <div class="flex justify-end gap-2">
              <button @click="showAddProperty = false" class="text-xs text-gray-400 hover:text-gray-600">Cancel</button>
              <button @click="addPropertyAssignment" class="btn-primary btn-xs" :disabled="addingProperty || !addPropertyForm.property">
                <Loader2 v-if="addingProperty" :size="12" class="animate-spin" />
                <template v-else>Assign</template>
              </button>
            </div>
          </div>
          <!-- Assignments list -->
          <div v-if="loadingAssignments" class="text-center py-3">
            <Loader2 :size="16" class="animate-spin mx-auto text-gray-400" />
          </div>
          <div v-else-if="userAssignments.length" class="space-y-1.5">
            <div
              v-for="a in userAssignments"
              :key="a.id"
              class="flex items-center justify-between px-3 py-2 rounded-lg border border-gray-100 bg-white text-sm"
            >
              <div class="min-w-0 flex-1">
                <span class="font-medium text-gray-800">{{ a.property_name }}</span>
                <div class="flex items-center gap-2 mt-0.5">
                  <span :class="a.assignment_type === 'estate' ? 'bg-info-50 text-info-700' : 'bg-info-100 text-info-700'" class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium">
                    {{ a.assignment_type_display }}
                  </span>
                  <select
                    :value="a.status"
                    @change="updateUserAssignmentStatus(a, ($event.target as HTMLSelectElement).value)"
                    class="text-xs border-0 bg-transparent text-gray-400 p-0 focus:ring-0 cursor-pointer"
                  >
                    <option value="active">Active</option>
                    <option value="completed">Completed</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
              </div>
              <button @click="removeUserAssignment(a)" class="text-gray-300 hover:text-danger-500 p-1 ml-2 flex-shrink-0" title="Remove assignment">
                <X :size="14" />
              </button>
            </div>
          </div>
          <p v-else class="text-xs text-gray-400 text-center py-2">No properties assigned</p>
        </div>
        <div class="flex items-center gap-2">
          <label class="label mb-0">Active</label>
          <button
            @click="editForm.is_active = !editForm.is_active"
            :class="editForm.is_active ? 'bg-navy' : 'bg-gray-300'"
            class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors"
          >
            <span :class="editForm.is_active ? 'translate-x-5' : 'translate-x-1'" class="inline-block h-3 w-3 rounded-full bg-white transition-transform" />
          </button>
        </div>
        <div v-if="editError" class="text-sm text-danger-600">{{ editError }}</div>
      </div>
      <template #footer>
        <button @click="editingUser = null" class="btn-ghost">Cancel</button>
        <button @click="saveUser" class="btn-primary" :disabled="saving">
          <Loader2 v-if="saving" :size="15" class="animate-spin" />
          Save
        </button>
      </template>
    </BaseModal>

    <!-- Invite Modal -->
    <BaseModal :open="showInvite" title="Invite User" size="md" @close="showInvite = false">
      <div class="space-y-4">
        <div>
          <label class="label">Email</label>
          <input v-model="inviteForm.email" type="email" class="input" placeholder="user@example.com" />
        </div>
        <div>
          <label class="label">First name <span class="text-gray-400 font-normal">(optional)</span></label>
          <input v-model="inviteForm.first_name" type="text" class="input" placeholder="John" />
        </div>
        <div>
          <label class="label">Role</label>
          <select v-model="inviteForm.role" class="input">
            <optgroup v-for="(group, key) in ROLE_GROUPS" :key="key" :label="group.label">
              <option v-for="r in group.roles" :key="r.value" :value="r.value">{{ r.label }}</option>
            </optgroup>
          </select>
          <!-- Role description -->
          <div v-if="roleDescription(inviteForm.role)" class="mt-2 px-3 py-2 rounded-lg bg-gray-50 border border-gray-100">
            <p class="text-xs text-gray-500">{{ roleDescription(inviteForm.role) }}</p>
          </div>
        </div>
        <!-- Module access for viewer -->
        <div v-if="inviteForm.role === 'viewer'">
          <label class="label">Module Access</label>
          <div class="grid grid-cols-2 gap-2 mt-1">
            <label v-for="mod in MODULES" :key="mod" class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                :checked="inviteForm.module_access.includes(mod)"
                @change="toggleModule(inviteForm.module_access, mod)"
                class="rounded border-gray-300 text-navy focus:ring-navy/30"
              />
              {{ capitalise(mod) }}
            </label>
          </div>
        </div>
        <div v-if="inviteError" class="text-sm text-danger-600">{{ inviteError }}</div>
        <div v-if="inviteSuccess" class="text-sm text-success-600">{{ inviteSuccess }}</div>
      </div>
      <template #footer>
        <button @click="showInvite = false" class="btn-ghost">Close</button>
        <button @click="sendInvite" class="btn-primary" :disabled="inviting">
          <Loader2 v-if="inviting" :size="15" class="animate-spin" />
          Send Invite
        </button>
      </template>
    </BaseModal>

    <!-- Delete Confirmation Modal -->
    <BaseModal :open="!!deletingUser" title="Delete User" size="sm" @close="deletingUser = null">
      <p class="text-sm text-gray-600">
        Are you sure you want to deactivate <strong>{{ deletingUser?.full_name || deletingUser?.email }}</strong>?
        This will prevent them from signing in.
      </p>
      <div v-if="deleteError" class="text-sm text-danger-600 mt-3">{{ deleteError }}</div>
      <template #footer>
        <button @click="deletingUser = null" class="btn-ghost">Cancel</button>
        <button @click="deleteUser" class="btn-danger" :disabled="deleting">
          <Loader2 v-if="deleting" :size="15" class="animate-spin" />
          Delete
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'
import { useToast } from '../../composables/useToast'
import { Search, UserPlus, Pencil, Trash2, Loader2, Building2, Plus, X, Send } from 'lucide-vue-next'
import PageHeader from '../../components/PageHeader.vue'
import BaseModal from '../../components/BaseModal.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const toast = useToast()

// ── Role configuration ──

const ALL_ROLE_GROUPS: Record<string, { label: string; roles: { value: string; label: string; badge: string; description: string }[] }> = {
  staff: {
    label: 'Staff',
    roles: [
      { value: 'agency_admin', label: 'Agency Admin', badge: 'badge-indigo', description: 'Principal practitioner — manages agency, invites team, sees all agency properties' },
      { value: 'estate_agent', label: 'Estate Agent', badge: 'badge-blue', description: 'Transaction agent — assigned to properties for letting/sales deals' },
      { value: 'managing_agent', label: 'Managing Agent', badge: 'badge-blue', description: 'Ongoing property manager — maintenance, tenants, fiduciary duty to owner' },
      { value: 'accountant', label: 'Accountant', badge: 'badge-emerald', description: 'Read-only financial access — statements, trust account, reconciliation' },
      { value: 'viewer', label: 'Viewer', badge: 'bg-gray-100 text-gray-600', description: 'Read-only access to selected modules — admin assistant or trainee' },
    ],
  },
  external: {
    label: 'External',
    roles: [
      { value: 'owner', label: 'Owner', badge: 'badge-purple', description: 'Property owner — sees own properties via ownership chain' },
      { value: 'tenant', label: 'Tenant', badge: 'badge-green', description: 'Tenant — mobile app, own lease and unit only' },
      { value: 'supplier', label: 'Supplier', badge: 'badge-amber', description: 'Contractor — assigned jobs only, POPIA data minimisation' },
    ],
  },
  system: {
    label: 'System',
    roles: [
      { value: 'admin', label: 'Admin', badge: 'bg-navy/10 text-navy', description: 'Full system access across all agencies and properties' },
      { value: 'agent', label: 'Agent (Legacy)', badge: 'badge-gray', description: 'Deprecated — use Estate Agent or Managing Agent instead' },
    ],
  },
}

// Agency admins can only assign staff + external roles, not system roles
const ROLE_GROUPS = computed(() => {
  if (auth.user?.role === 'admin') return ALL_ROLE_GROUPS
  const { system, ...rest } = ALL_ROLE_GROUPS
  return rest
})

// Flattened lookup for quick access (always includes all for display purposes)
const ALL_ROLES = Object.values(ALL_ROLE_GROUPS).flatMap(g => g.roles)

function roleLabel(value: string): string {
  return ALL_ROLES.find(r => r.value === value)?.label ?? value
}

function roleBadgeClass(value: string): string {
  return ALL_ROLES.find(r => r.value === value)?.badge ?? 'badge-gray'
}

function roleDescription(value: string): string {
  return ALL_ROLES.find(r => r.value === value)?.description ?? ''
}

function isAgentRole(value: string): boolean {
  return ['estate_agent', 'managing_agent', 'agency_admin', 'agent'].includes(value)
}

const MODULES = ['properties', 'leases', 'maintenance', 'inspections', 'tenants', 'suppliers']

function capitalise(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function toggleModule(list: string[], mod: string) {
  const idx = list.indexOf(mod)
  if (idx >= 0) list.splice(idx, 1)
  else list.push(mod)
}

// ── Types ──

interface UserRecord {
  id: number
  email: string
  full_name: string
  role: string
  is_active: boolean
  last_login: string | null
  agency: number | null
  agency_name: string | null
  module_access: string[]
  ffc_number: string
  ffc_category: string
}

interface InviteRecord {
  id: number
  email: string
  role: string
  invited_by: string | null
  agency_name: string | null
  created_at: string
}

// ── State ──

const users = ref<UserRecord[]>([])
const loading = ref(false)
const search = ref('')
const roleFilter = ref('')

const invites = ref<InviteRecord[]>([])

// Invite modal open state is tied to ?invite=1 in the URL so the browser
// back button closes the modal instead of leaving the users page.
const showInvite = computed({
  get: () => route.query.invite === '1',
  set: (v: boolean) => {
    const q: any = { ...route.query }
    if (v) {
      q.invite = '1'
      router.push({ query: q })
    } else {
      delete q.invite
      router.replace({ query: q })
    }
  },
})
const inviteForm = ref({ email: '', role: 'estate_agent', first_name: '', module_access: [] as string[] })
const inviting = ref(false)
const inviteError = ref('')
const inviteSuccess = ref('')

const editingUser = ref<UserRecord | null>(null)
const editForm = ref({ role: '', is_active: true, module_access: [] as string[], ffc_number: '', ffc_category: '' })
const saving = ref(false)
const editError = ref('')

const deletingUser = ref<UserRecord | null>(null)
const deleting = ref(false)
const deleteError = ref('')

const cancellingInvite = ref<InviteRecord | null>(null)
const cancellingInviteLoading = ref(false)
const cancelInviteError = ref('')
const resendingInviteId = ref<number | null>(null)

// ── Property assignment state (edit modal) ──
interface AssignmentRecord {
  id: number
  property: number
  property_name: string
  property_address: string
  assignment_type: string
  assignment_type_display: string
  status: string
  status_display: string
  created_at: string
}
interface PropertyOption { id: number; name: string; address: string }

const userAssignments = ref<AssignmentRecord[]>([])
const loadingAssignments = ref(false)
const allProperties = ref<PropertyOption[]>([])
const showAddProperty = ref(false)
const addPropertyForm = ref({ property: '' as string | number, assignment_type: 'managing' })
const addingProperty = ref(false)
const addPropertyError = ref('')

const unassignedProperties = computed(() => {
  const assignedIds = new Set(userAssignments.value.map(a => a.property))
  return allProperties.value.filter(p => !assignedIds.has(p.id))
})

// ── Actions ──

let debounceTimer: ReturnType<typeof setTimeout>
function debouncedLoad() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadUsers, 300)
}

async function loadUsers() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (search.value) params.search = search.value
    if (roleFilter.value) params.role = roleFilter.value
    const [usersRes, invitesRes] = await Promise.all([
      api.get('/auth/users/', { params }),
      api.get('/auth/users/invites/'),
    ])
    users.value = usersRes.data.results ?? usersRes.data
    invites.value = invitesRes.data
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

function openInviteModal() {
  inviteForm.value = { email: '', role: 'estate_agent', first_name: '', module_access: [] }
  inviteError.value = ''
  inviteSuccess.value = ''
  showInvite.value = true
}

function editUser(u: UserRecord) {
  editingUser.value = u
  editForm.value = {
    role: u.role,
    is_active: u.is_active,
    module_access: [...(u.module_access || [])],
    ffc_number: u.ffc_number || '',
    ffc_category: u.ffc_category || '',
  }
  editError.value = ''
  // Load property assignments for agent roles
  userAssignments.value = []
  showAddProperty.value = false
  addPropertyError.value = ''
  if (isAgentRole(u.role)) {
    loadUserAssignments(u.id)
  }
}

async function loadUserAssignments(userId: number) {
  loadingAssignments.value = true
  try {
    const { data } = await api.get('/properties/agent-assignments/', { params: { agent: userId } })
    userAssignments.value = data.results ?? data
  } catch { /* ignore */ } finally {
    loadingAssignments.value = false
  }
}

async function loadAllProperties() {
  if (allProperties.value.length) return
  try {
    const { data } = await api.get('/properties/', { params: { page_size: 500 } })
    const results = data.results ?? data
    allProperties.value = results.map((p: any) => ({ id: p.id, name: p.name, address: p.address }))
  } catch { /* ignore */ }
}

function openAddProperty() {
  showAddProperty.value = true
  addPropertyForm.value = { property: '', assignment_type: 'managing' }
  addPropertyError.value = ''
  loadAllProperties()
}

async function addPropertyAssignment() {
  if (!editingUser.value || !addPropertyForm.value.property) return
  addingProperty.value = true
  addPropertyError.value = ''
  try {
    await api.post('/properties/agent-assignments/', {
      property: addPropertyForm.value.property,
      agent: editingUser.value.id,
      assignment_type: addPropertyForm.value.assignment_type,
    })
    showAddProperty.value = false
    await loadUserAssignments(editingUser.value.id)
  } catch (e: any) {
    addPropertyError.value = e.response?.data?.detail || e.response?.data?.non_field_errors?.[0] || 'Failed to assign property.'
  } finally {
    addingProperty.value = false
  }
}

async function removeUserAssignment(assignment: AssignmentRecord) {
  if (!editingUser.value) return
  try {
    await api.delete(`/properties/agent-assignments/${assignment.id}/`)
    userAssignments.value = userAssignments.value.filter(a => a.id !== assignment.id)
  } catch { /* ignore */ }
}

async function updateUserAssignmentStatus(assignment: AssignmentRecord, newStatus: string) {
  try {
    await api.patch(`/properties/agent-assignments/${assignment.id}/`, { status: newStatus })
    assignment.status = newStatus
    assignment.status_display = newStatus.charAt(0).toUpperCase() + newStatus.slice(1)
  } catch { /* ignore */ }
}

async function saveUser() {
  if (!editingUser.value) return
  saving.value = true
  editError.value = ''
  try {
    const payload: Record<string, any> = { role: editForm.value.role, is_active: editForm.value.is_active }
    if (editForm.value.role === 'viewer') {
      payload.module_access = editForm.value.module_access
    }
    if (isAgentRole(editForm.value.role)) {
      payload.ffc_number = editForm.value.ffc_number
      payload.ffc_category = editForm.value.ffc_category
    }
    await api.patch(`/auth/users/${editingUser.value.id}/`, payload)
    editingUser.value = null
    await loadUsers()
  } catch (e: any) {
    editError.value = e.response?.data?.detail || 'Failed to update user.'
  } finally {
    saving.value = false
  }
}

async function sendInvite() {
  inviting.value = true
  inviteError.value = ''
  inviteSuccess.value = ''
  try {
    const payload: Record<string, any> = {
      email: inviteForm.value.email,
      role: inviteForm.value.role,
      first_name: inviteForm.value.first_name,
    }
    await api.post('/auth/users/invite/', payload)
    inviteForm.value = { email: '', role: 'estate_agent', first_name: '', module_access: [] }
    showInvite.value = false
    await loadUsers()
  } catch (e: any) {
    inviteError.value = e.response?.data?.detail || 'Failed to send invite.'
  } finally {
    inviting.value = false
  }
}

function confirmDelete(u: UserRecord) {
  deletingUser.value = u
  deleteError.value = ''
}

async function deleteUser() {
  if (!deletingUser.value) return
  deleting.value = true
  deleteError.value = ''
  const id = deletingUser.value.id
  try {
    await api.delete(`/auth/users/${id}/`)
    users.value = users.value.filter(u => u.id !== id)
    deletingUser.value = null
    api.get('/auth/users/', { params: { search: search.value, role: roleFilter.value } })
      .then(r => { users.value = r.data.results ?? r.data })
      .catch(() => {})
  } catch (e: any) {
    deleteError.value = e.response?.data?.detail || 'Failed to delete user.'
  } finally {
    deleting.value = false
  }
}

function confirmCancelInvite(inv: InviteRecord) {
  cancellingInvite.value = inv
  cancelInviteError.value = ''
}

async function cancelInvite() {
  if (!cancellingInvite.value) return
  cancellingInviteLoading.value = true
  cancelInviteError.value = ''
  try {
    await api.delete(`/auth/users/invites/${cancellingInvite.value.id}/`)
    invites.value = invites.value.filter(i => i.id !== cancellingInvite.value!.id)
    cancellingInvite.value = null
  } catch (e: any) {
    cancelInviteError.value = e.response?.data?.detail || 'Failed to revoke invite.'
  } finally {
    cancellingInviteLoading.value = false
  }
}

async function resendInvite(inv: InviteRecord) {
  resendingInviteId.value = inv.id
  try {
    await api.post(`/auth/users/invites/${inv.id}/resend/`)
    toast.success(`Invite resent to ${inv.email}`)
  } catch {
    toast.error('Failed to resend invite.')
  } finally {
    resendingInviteId.value = null
  }
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })
}

onMounted(loadUsers)
</script>
