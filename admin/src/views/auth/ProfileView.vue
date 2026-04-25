<template>
  <div class="space-y-5">
    <PageHeader
      title="Profile"
      subtitle="Manage your account details"
      :crumbs="[{ label: 'Dashboard', to: '/' }, { label: 'Profile' }]"
    />

    <!-- Profile Info -->
    <div class="card p-5 space-y-4 max-w-lg">
      <h3 class="font-semibold text-gray-900">Personal Information</h3>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="label">First name</label>
          <input v-model="form.first_name" type="text" class="input" />
        </div>
        <div>
          <label class="label">Last name</label>
          <input v-model="form.last_name" type="text" class="input" />
        </div>
      </div>
      <div>
        <label class="label">Email</label>
        <input :value="auth.user?.email" class="input bg-gray-50" disabled />
      </div>
      <div>
        <label class="label">Phone</label>
        <input v-model="form.phone" type="tel" class="input" placeholder="082 123 4567" />
      </div>
      <div>
        <label class="label">Role</label>
        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium capitalize bg-navy/10 text-navy">
          {{ auth.user?.role }}
        </span>
      </div>
      <div v-if="profileMsg" :class="profileMsgError ? 'text-danger-600' : 'text-success-600'" class="text-sm">
        {{ profileMsg }}
      </div>
      <button @click="saveProfile" class="btn-primary" :disabled="savingProfile">
        <Loader2 v-if="savingProfile" :size="15" class="animate-spin" />
        Save Changes
      </button>
    </div>

    <!-- 2FA Method Preference -->
    <SecurityTab />

    <!-- AI Knowledge (admin only) -->
    <AIKnowledgeTab v-if="auth.user?.role === 'admin'" />

    <!-- Change Password -->
    <div class="card p-5 space-y-4 max-w-lg">
      <h3 class="font-semibold text-gray-900">Change Password</h3>
      <div v-if="hasPassword">
        <label class="label">Current password</label>
        <input v-model="pwForm.current_password" type="password" class="input" data-clarity-mask="true" />
      </div>
      <div>
        <label class="label">New password</label>
        <input v-model="pwForm.new_password" type="password" class="input" placeholder="Min 8 characters" data-clarity-mask="true" />
      </div>
      <div>
        <label class="label">Confirm new password</label>
        <input v-model="pwConfirm" type="password" class="input" data-clarity-mask="true" />
      </div>
      <div v-if="pwMsg" :class="pwMsgError ? 'text-danger-600' : 'text-success-600'" class="text-sm">
        {{ pwMsg }}
      </div>
      <button @click="changePassword" class="btn-primary" :disabled="changingPw">
        <Loader2 v-if="changingPw" :size="15" class="animate-spin" />
        Update Password
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import api from '../../api'
import { Loader2 } from 'lucide-vue-next'
import PageHeader from '../../components/PageHeader.vue'
import AIKnowledgeTab from '../settings/AIKnowledgeTab.vue'
import SecurityTab from '../settings/SecurityTab.vue'

const auth = useAuthStore()

const form = reactive({
  first_name: '',
  last_name: '',
  phone: '',
})

const savingProfile = ref(false)
const profileMsg = ref('')
const profileMsgError = ref(false)

const hasPassword = ref(true)
const pwForm = reactive({ current_password: '', new_password: '' })
const pwConfirm = ref('')
const changingPw = ref(false)
const pwMsg = ref('')
const pwMsgError = ref(false)

onMounted(async () => {
  try {
    const { data } = await api.get('/auth/me/')
    form.first_name = data.first_name || ''
    form.last_name = data.last_name || ''
    form.phone = data.phone || ''
    auth.user = data
  } catch { /* ignore */ }
})

async function saveProfile() {
  savingProfile.value = true
  profileMsg.value = ''
  try {
    const { data } = await api.patch('/auth/me/', {
      first_name: form.first_name,
      last_name: form.last_name,
      phone: form.phone,
    })
    auth.user = data
    profileMsg.value = 'Profile updated.'
    profileMsgError.value = false
  } catch (e: any) {
    profileMsg.value = e.response?.data?.detail || 'Failed to update profile.'
    profileMsgError.value = true
  } finally {
    savingProfile.value = false
  }
}

async function changePassword() {
  pwMsg.value = ''
  if (pwForm.new_password !== pwConfirm.value) {
    pwMsg.value = 'Passwords do not match.'
    pwMsgError.value = true
    return
  }
  changingPw.value = true
  try {
    await api.post('/auth/change-password/', pwForm)
    pwMsg.value = 'Password updated.'
    pwMsgError.value = false
    pwForm.current_password = ''
    pwForm.new_password = ''
    pwConfirm.value = ''
  } catch (e: any) {
    const detail = e.response?.data?.detail
    pwMsg.value = Array.isArray(detail) ? detail.join(' ') : (detail || 'Failed to change password.')
    pwMsgError.value = true
  } finally {
    changingPw.value = false
  }
}
</script>
