<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-xl font-bold text-gray-900">Users</h2>
        <p class="text-sm text-gray-500 mt-0.5">Manage user accounts and roles</p>
      </div>
      <button @click="showInvite = true" class="btn-primary">
        <UserPlus :size="16" />
        Invite User
      </button>
    </div>

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
      <select v-model="roleFilter" class="input w-40" @change="loadUsers">
        <option value="">All roles</option>
        <option value="admin">Admin</option>
        <option value="agent">Agent</option>
        <option value="tenant">Tenant</option>
        <option value="owner">Owner</option>
        <option value="supplier">Supplier</option>
      </select>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-400">
        <Loader2 :size="20" class="animate-spin mx-auto" />
      </div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="text-left px-4 py-3 font-medium text-gray-600">Name</th>
            <th class="text-left px-4 py-3 font-medium text-gray-600">Email</th>
            <th class="text-left px-4 py-3 font-medium text-gray-600">Role</th>
            <th class="text-left px-4 py-3 font-medium text-gray-600">Status</th>
            <th class="text-left px-4 py-3 font-medium text-gray-600">Last Login</th>
            <th class="text-right px-4 py-3 font-medium text-gray-600">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="u in users" :key="u.id" class="hover:bg-gray-50">
            <td class="px-4 py-3 font-medium text-gray-900">{{ u.full_name }}</td>
            <td class="px-4 py-3 text-gray-600">{{ u.email }}</td>
            <td class="px-4 py-3">
              <span :class="roleBadgeClass(u.role)" class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize">
                {{ u.role }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span :class="u.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'" class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium">
                {{ u.is_active ? 'Active' : 'Inactive' }}
              </span>
            </td>
            <td class="px-4 py-3 text-gray-500">{{ u.last_login ? formatDate(u.last_login) : 'Never' }}</td>
            <td class="px-4 py-3 text-right space-x-1">
              <button @click="editUser(u)" class="text-gray-400 hover:text-navy p-1 rounded">
                <Pencil :size="15" />
              </button>
              <button @click="confirmDelete(u)" class="text-gray-400 hover:text-red-600 p-1 rounded">
                <Trash2 :size="15" />
              </button>
            </td>
          </tr>
          <tr v-if="!users.length">
            <td colspan="6" class="px-4 py-8 text-center text-gray-400">No users found</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pending Invites -->
    <div v-if="invites.length" class="card overflow-hidden">
      <div class="px-4 py-3 bg-gray-50 border-b border-gray-200">
        <h3 class="text-sm font-semibold text-gray-700">Pending Invites</h3>
      </div>
      <table class="w-full text-sm">
        <thead class="border-b border-gray-100">
          <tr>
            <th class="text-left px-4 py-2 font-medium text-gray-500">Email</th>
            <th class="text-left px-4 py-2 font-medium text-gray-500">Role</th>
            <th class="text-left px-4 py-2 font-medium text-gray-500">Invited by</th>
            <th class="text-left px-4 py-2 font-medium text-gray-500">Sent</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr v-for="inv in invites" :key="inv.id" class="text-gray-600">
            <td class="px-4 py-2">{{ inv.email }}</td>
            <td class="px-4 py-2">
              <span :class="roleBadgeClass(inv.role)" class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize">{{ inv.role }}</span>
            </td>
            <td class="px-4 py-2">{{ inv.invited_by || '—' }}</td>
            <td class="px-4 py-2 text-gray-400">{{ formatDate(inv.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Edit Modal -->
    <div v-if="editingUser" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="editingUser = null">
      <div class="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h3 class="text-lg font-semibold text-gray-900">Edit User</h3>
        <div>
          <label class="label">Email</label>
          <input :value="editingUser.email" class="input bg-gray-50" disabled />
        </div>
        <div>
          <label class="label">Role</label>
          <select v-model="editForm.role" class="input">
            <option value="admin">Admin</option>
            <option value="agent">Agent</option>
            <option value="tenant">Tenant</option>
            <option value="owner">Owner</option>
            <option value="supplier">Supplier</option>
          </select>
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
        <div v-if="editError" class="text-sm text-red-600">{{ editError }}</div>
        <div class="flex justify-end gap-2 pt-2">
          <button @click="editingUser = null" class="btn-secondary">Cancel</button>
          <button @click="saveUser" class="btn-primary" :disabled="saving">
            <Loader2 v-if="saving" :size="15" class="animate-spin" />
            Save
          </button>
        </div>
      </div>
    </div>

    <!-- Invite Modal -->
    <div v-if="showInvite" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="showInvite = false">
      <div class="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4">
        <h3 class="text-lg font-semibold text-gray-900">Invite User</h3>
        <div>
          <label class="label">Email</label>
          <input v-model="inviteForm.email" type="email" class="input" placeholder="user@example.com" />
        </div>
        <div>
          <label class="label">Role</label>
          <select v-model="inviteForm.role" class="input">
            <option value="agent">Agent</option>
            <option value="tenant">Tenant</option>
            <option value="owner">Owner</option>
            <option value="supplier">Supplier</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <div>
          <label class="label">First name <span class="text-gray-400 font-normal">(optional)</span></label>
          <input v-model="inviteForm.first_name" type="text" class="input" placeholder="John" />
        </div>
        <div v-if="inviteError" class="text-sm text-red-600">{{ inviteError }}</div>
        <div v-if="inviteSuccess" class="text-sm text-green-600">{{ inviteSuccess }}</div>
        <div class="flex justify-end gap-2 pt-2">
          <button @click="showInvite = false" class="btn-secondary">Close</button>
          <button @click="sendInvite" class="btn-primary" :disabled="inviting">
            <Loader2 v-if="inviting" :size="15" class="animate-spin" />
            Send Invite
          </button>
        </div>
      </div>
    </div>
    <!-- Delete Confirmation Modal -->
    <div v-if="deletingUser" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="deletingUser = null">
      <div class="bg-white rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4">
        <h3 class="text-lg font-semibold text-gray-900">Delete User</h3>
        <p class="text-sm text-gray-600">
          Are you sure you want to deactivate <strong>{{ deletingUser.full_name || deletingUser.email }}</strong>?
          This will prevent them from signing in.
        </p>
        <div v-if="deleteError" class="text-sm text-red-600">{{ deleteError }}</div>
        <div class="flex justify-end gap-2 pt-2">
          <button @click="deletingUser = null" class="btn-secondary">Cancel</button>
          <button @click="deleteUser" class="btn-primary !bg-red-600 hover:!bg-red-700" :disabled="deleting">
            <Loader2 v-if="deleting" :size="15" class="animate-spin" />
            Delete
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api'
import { Search, UserPlus, Pencil, Trash2, Loader2 } from 'lucide-vue-next'

interface UserRecord {
  id: number
  email: string
  full_name: string
  role: string
  is_active: boolean
  last_login: string | null
}

const users = ref<UserRecord[]>([])
const loading = ref(false)
const search = ref('')
const roleFilter = ref('')

const invites = ref<{ id: number; email: string; role: string; invited_by: string | null; created_at: string }[]>([])

const showInvite = ref(false)
const inviteForm = ref({ email: '', role: 'agent', first_name: '' })
const inviting = ref(false)
const inviteError = ref('')
const inviteSuccess = ref('')

const editingUser = ref<UserRecord | null>(null)
const editForm = ref({ role: '', is_active: true })
const saving = ref(false)
const editError = ref('')

const deletingUser = ref<UserRecord | null>(null)
const deleting = ref(false)
const deleteError = ref('')

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

function editUser(u: UserRecord) {
  editingUser.value = u
  editForm.value = { role: u.role, is_active: u.is_active }
  editError.value = ''
}

async function saveUser() {
  if (!editingUser.value) return
  saving.value = true
  editError.value = ''
  try {
    await api.patch(`/auth/users/${editingUser.value.id}/`, editForm.value)
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
    await api.post('/auth/users/invite/', inviteForm.value)
    inviteSuccess.value = `Invitation sent to ${inviteForm.value.email}`
    inviteForm.value = { email: '', role: 'agent', first_name: '' }
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
    // Silent background refresh — no loading spinner
    api.get('/auth/users/', { params: { search: search.value, role: roleFilter.value } })
      .then(r => { users.value = r.data.results ?? r.data })
      .catch(() => {})
  } catch (e: any) {
    deleteError.value = e.response?.data?.detail || 'Failed to delete user.'
  } finally {
    deleting.value = false
  }
}

function roleBadgeClass(role: string) {
  const map: Record<string, string> = {
    admin: 'bg-navy/10 text-navy',
    agent: 'bg-blue-100 text-blue-700',
    tenant: 'bg-green-100 text-green-700',
    owner: 'bg-purple-100 text-purple-700',
    supplier: 'bg-orange-100 text-orange-700',
  }
  return map[role] || 'bg-gray-100 text-gray-600'
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' })
}

onMounted(loadUsers)
</script>
