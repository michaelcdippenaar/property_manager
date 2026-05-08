<template>
  <div class="min-h-screen bg-lavender flex items-center justify-center px-4 py-12">
    <div class="w-full max-w-2xl">

      <!-- Logo -->
      <div class="text-center mb-6">
        <span class="text-3xl font-bold text-navy">Klikk<span class="text-pink-brand">.</span></span>
        <p class="text-gray-500 text-sm mt-1">Set up your {{ isAgency ? 'agency' : 'workspace' }}</p>
      </div>

      <!-- Stepper -->
      <div class="flex items-center justify-center gap-2 mb-6" data-testid="stepper">
        <template v-for="(s, idx) in stepLabels" :key="idx">
          <div class="flex items-center gap-2">
            <div
              class="h-7 w-7 rounded-full flex items-center justify-center text-xs font-semibold border-2 transition-all"
              :class="step > idx + 1
                ? 'bg-navy border-navy text-white'
                : step === idx + 1
                  ? 'border-navy text-navy bg-white'
                  : 'border-gray-200 text-gray-400 bg-white'"
            >{{ idx + 1 }}</div>
            <span class="text-xs font-medium" :class="step >= idx + 1 ? 'text-navy' : 'text-gray-400'">{{ s }}</span>
          </div>
          <ChevronRight v-if="idx < stepLabels.length - 1" :size="14" class="text-gray-300" />
        </template>
      </div>

      <div class="card p-8">
        <form @submit.prevent="onNext" class="space-y-5">

          <!-- ── Step 1: Agency identity ── -->
          <section v-if="step === 1" class="space-y-4">
            <header class="space-y-1">
              <h2 class="text-lg font-semibold text-navy">{{ isAgency ? 'Tell us about your agency' : 'Tell us about your workspace' }}</h2>
              <p class="text-sm text-gray-500">These details appear on mandates, leases and other generated documents.</p>
            </header>

            <div>
              <label class="label">{{ isAgency ? 'Registered name' : 'Workspace name' }} <span class="text-danger-400">*</span></label>
              <input v-model="form.name" type="text" class="input" required placeholder="e.g. Prestige Properties (Pty) Ltd" />
            </div>

            <div v-if="isAgency" class="grid grid-cols-2 gap-3">
              <div>
                <label class="label">Trading name (t/a)</label>
                <input v-model="form.trading_name" type="text" class="input" placeholder="e.g. Century 21 Stellenbosch" />
              </div>
              <div>
                <label class="label">CIPC registration number</label>
                <input v-model="form.registration_number" type="text" class="input" placeholder="e.g. 2024/123456/07" />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="label">Contact phone</label>
                <input v-model="form.contact_number" type="tel" class="input" placeholder="082 123 4567" />
              </div>
              <div>
                <label class="label">Contact email</label>
                <EmailInput v-model="form.email" placeholder="hello@yourbusiness.co.za" />
              </div>
            </div>

            <div>
              <label class="label">Physical address</label>
              <textarea v-model="form.physical_address" class="input min-h-[80px]" placeholder="Street, suburb, city, postal code" />
            </div>

            <div>
              <label class="label">Website</label>
              <input v-model="form.website" type="url" class="input" placeholder="https://yourbusiness.co.za" />
            </div>

            <div>
              <label class="label">Logo (optional)</label>
              <input
                ref="logoInput"
                type="file"
                accept="image/*"
                class="block w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-navy file:text-white hover:file:bg-navy/90 file:cursor-pointer"
                @change="onLogoChange"
              />
            </div>
          </section>

          <!-- ── Step 2: Trust account & compliance ── -->
          <section v-if="step === 2" class="space-y-4">
            <header class="space-y-1">
              <h2 class="text-lg font-semibold text-navy">Trust account & compliance</h2>
              <p class="text-sm text-gray-500">
                <span v-if="isAgency">All optional — but you'll need the trust details before you can issue rental mandates.</span>
                <span v-else>All optional — fill these in later under Settings if you collect rent through a trust account.</span>
              </p>
            </header>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="label">Trust account number</label>
                <input v-model="form.trust_account_number" type="text" class="input" placeholder="Account number" />
              </div>
              <div>
                <label class="label">Trust bank</label>
                <input v-model="form.trust_bank_name" type="text" class="input" placeholder="e.g. FNB" />
              </div>
              <div>
                <label class="label">Branch code</label>
                <input v-model="form.trust_branch_code" type="text" class="input" placeholder="e.g. 250655" />
              </div>
              <div v-if="isAgency">
                <label class="label">PPRA FFC number</label>
                <input v-model="form.eaab_ffc_number" type="text" class="input" placeholder="e.g. 2024/FFC/12345" />
              </div>
            </div>

            <template v-if="isAgency">
              <div>
                <label class="label">Information Officer email</label>
                <EmailInput v-model="form.information_officer_email" placeholder="popi@yourbusiness.co.za" />
                <p class="text-micro text-gray-400 mt-1">POPIA s55 — required if you process personal information.</p>
              </div>

              <label class="flex items-start gap-2.5 cursor-pointer">
                <input
                  v-model="form.fica_registered"
                  type="checkbox"
                  class="mt-0.5 h-4 w-4 rounded border-gray-300 text-navy accent-navy"
                />
                <span class="text-sm text-gray-600">
                  We're registered as an Accountable Institution with the FIC.
                </span>
              </label>
            </template>
          </section>

          <!-- ── Step 3: Invite teammates (agency only) ── -->
          <section v-if="step === 3 && isAgency" class="space-y-4">
            <header class="space-y-1">
              <h2 class="text-lg font-semibold text-navy">Invite teammates</h2>
              <p class="text-sm text-gray-500">Add the people who'll work with you in Klikk. You can skip this and invite them later from Settings → Users.</p>
            </header>

            <div v-for="(invite, i) in invites" :key="i" class="grid grid-cols-12 gap-2 items-end">
              <div class="col-span-7">
                <label v-if="i === 0" class="label">Email</label>
                <EmailInput v-model="invite.email" placeholder="teammate@yourbusiness.co.za" />
              </div>
              <div class="col-span-4">
                <label v-if="i === 0" class="label">Role</label>
                <select v-model="invite.role" class="input">
                  <option value="agent">Agent</option>
                  <option value="managing_agent">Managing agent</option>
                  <option value="estate_agent">Estate agent</option>
                  <option value="agency_admin">Agency admin</option>
                </select>
              </div>
              <button
                type="button"
                class="col-span-1 h-10 flex items-center justify-center text-gray-400 hover:text-danger-500"
                aria-label="Remove invite row"
                @click="removeInvite(i)"
              >
                <X :size="16" />
              </button>
            </div>

            <button
              type="button"
              class="text-sm text-navy hover:underline flex items-center gap-1"
              @click="addInvite"
            >
              <Plus :size="14" /> Add another
            </button>
          </section>

          <!-- Error -->
          <div v-if="error" class="flex items-center gap-2 p-3 bg-danger-50 border border-danger-100 rounded-lg text-danger-700 text-sm">
            <AlertCircle :size="15" />
            {{ error }}
          </div>

          <!-- Actions -->
          <div class="flex items-center justify-between pt-3">
            <button
              v-if="step > 1"
              type="button"
              class="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
              @click="step -= 1"
            >
              <ChevronLeft :size="14" /> Back
            </button>
            <span v-else />

            <div class="flex items-center gap-2">
              <button
                v-if="canSkip"
                type="button"
                class="text-sm text-gray-500 hover:text-gray-700 px-3 py-2"
                :disabled="loading"
                @click="onSkipOrFinish"
              >
                {{ isLastStep ? 'Skip & finish' : 'Skip' }}
              </button>

              <button
                type="submit"
                class="btn-primary px-5 py-2.5"
                :disabled="loading || !canContinue"
                data-testid="next-btn"
              >
                <Loader2 v-if="loading" :size="15" class="animate-spin" />
                {{ loading ? 'Saving...' : isLastStep ? 'Finish setup' : 'Continue' }}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import api from '../../api'
import { AlertCircle, ChevronLeft, ChevronRight, Loader2, Plus, X } from 'lucide-vue-next'
import EmailInput from '../../components/EmailInput.vue'

const router = useRouter()
const auth = useAuthStore()

const step = ref(1)
const loading = ref(false)
const error = ref('')
const logoInput = ref<HTMLInputElement | null>(null)
const logoFile = ref<File | null>(null)

interface Invite { email: string; role: string }
const invites = reactive<Invite[]>([{ email: '', role: 'agent' }])

const form = reactive({
  name: '',
  trading_name: '',
  registration_number: '',
  contact_number: '',
  email: '',
  physical_address: '',
  website: '',
  trust_account_number: '',
  trust_bank_name: '',
  trust_branch_code: '',
  eaab_ffc_number: '',
  information_officer_email: '',
  fica_registered: false,
})

const isAgency = computed(() => auth.agency?.account_type === 'agency')

// Individuals skip the team-invite step entirely (they are the team).
const totalSteps = computed(() => (isAgency.value ? 3 : 2))
const stepLabels = computed(() =>
  isAgency.value
    ? ['Identity', 'Trust & compliance', 'Team']
    : ['Identity', 'Trust account'],
)
const isLastStep = computed(() => step.value === totalSteps.value)
// Steps 2 and 3 are skip-able (everything optional). Step 1 requires `name`.
const canSkip = computed(() => step.value >= 2)
const canContinue = computed(() => step.value !== 1 || form.name.trim().length > 0)

onMounted(async () => {
  // Pre-fill from existing agency record (name was set at signup).
  if (!auth.agency) {
    try { await auth.fetchAgency() } catch { /* noop */ }
  }
  if (auth.agency) {
    form.name = auth.agency.name || ''
    form.trading_name = auth.agency.trading_name || ''
    form.registration_number = auth.agency.registration_number || ''
    form.contact_number = auth.agency.contact_number || ''
    form.email = auth.agency.email || ''
    form.physical_address = auth.agency.physical_address || ''
    form.website = auth.agency.website || ''
    form.trust_account_number = auth.agency.trust_account_number || ''
    form.trust_bank_name = auth.agency.trust_bank_name || ''
    form.trust_branch_code = auth.agency.trust_branch_code || ''
    form.eaab_ffc_number = auth.agency.eaab_ffc_number || ''
    form.information_officer_email = auth.agency.information_officer_email || ''
    form.fica_registered = !!auth.agency.fica_registered
  }
})

function onLogoChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0] ?? null
  logoFile.value = file
}

function addInvite() { invites.push({ email: '', role: 'agent' }) }
function removeInvite(i: number) {
  if (invites.length === 1) {
    invites[0] = { email: '', role: 'agent' }
  } else {
    invites.splice(i, 1)
  }
}

async function persistAgency() {
  // Use multipart so the optional logo upload travels with the rest.
  const fd = new FormData()
  for (const [k, v] of Object.entries(form)) {
    if (v === null || v === undefined) continue
    fd.append(k, typeof v === 'boolean' ? (v ? 'true' : 'false') : String(v))
  }
  if (logoFile.value) fd.append('logo', logoFile.value)
  await api.put('/auth/agency/', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
}

async function sendInvites() {
  const valid = invites.filter((i) => i.email.trim().length > 0)
  for (const inv of valid) {
    try {
      await api.post('/auth/users/invite/', { email: inv.email.trim(), role: inv.role })
    } catch {
      // Best-effort — surface the first failure but don't block onboarding.
      error.value = `Invite for ${inv.email} failed — you can re-send from Settings → Users.`
    }
  }
}

async function completeOnboarding() {
  await api.post('/auth/agency/onboarding/complete/')
  await auth.fetchAgency()
}

async function onNext() {
  error.value = ''
  if (step.value === 1 && !form.name.trim()) {
    error.value = 'Please enter a name to continue.'
    return
  }

  loading.value = true
  try {
    if (step.value === 1) {
      await persistAgency()
      step.value = 2
      return
    }
    if (step.value === 2) {
      await persistAgency()
      if (totalSteps.value === 2) {
        // Individual flow finishes here.
        await completeOnboarding()
        router.push('/')
        return
      }
      step.value = 3
      return
    }
    // step 3 — agency invites
    await sendInvites()
    await completeOnboarding()
    router.push('/')
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Could not save your setup. Please try again.'
  } finally {
    loading.value = false
  }
}

async function onSkipOrFinish() {
  error.value = ''
  loading.value = true
  try {
    if (isLastStep.value) {
      await completeOnboarding()
      router.push('/')
      return
    }
    step.value += 1
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Could not finish onboarding.'
  } finally {
    loading.value = false
  }
}
</script>
