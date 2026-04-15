<template>
  <BaseDrawer :open="open" size="xl" @close="$emit('close')">
    <template #header>
      <div>
        <div class="font-semibold text-gray-900 text-sm">{{ landlord?.name }}</div>
        <div class="text-xs text-gray-500">{{ landlord?.email || 'No email' }}</div>
      </div>
    </template>

    <div class="p-5 space-y-6">
      <form @submit.prevent="saveLandlord" class="space-y-6">
        <!-- Basic info -->
        <div class="space-y-3">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy">Details</div>
          <div class="grid grid-cols-2 gap-3">
            <div class="col-span-2">
              <label class="label">Legal name</label>
              <input v-model="local.name" class="input" />
            </div>
            <div>
              <label class="label">Type</label>
              <select v-model="local.landlord_type" class="input">
                <option value="individual">Individual</option>
                <option value="company">Company (Pty Ltd / NPC)</option>
                <option value="trust">Trust</option>
                <option value="cc">Close Corporation (CC)</option>
                <option value="partnership">Partnership</option>
              </select>
            </div>
            <div v-if="local.landlord_type === 'company' || local.landlord_type === 'cc'" class="col-span-2">
              <label class="flex items-center gap-2 cursor-pointer select-none">
                <input type="checkbox" v-model="local.owned_by_trust" class="rounded text-navy" />
                <span class="text-sm text-gray-700">This entity is wholly or partly owned by a Trust</span>
              </label>
              <p class="text-xs text-gray-400 mt-1 ml-5">Enables FICA trust document requirements for beneficial ownership tracing.</p>
            </div>
            <div>
              <label class="label">{{ local.landlord_type === 'individual' ? 'SA ID / Passport' : 'Registration no.' }}</label>
              <input v-model="local.registration_number" class="input font-mono" />
            </div>
            <div>
              <label class="label">Email</label>
              <input v-model="local.email" type="email" class="input" />
            </div>
            <div>
              <label class="label">Phone</label>
              <input v-model="local.phone" class="input" />
            </div>
            <div v-if="local.landlord_type !== 'individual'">
              <label class="label">VAT number</label>
              <input v-model="local.vat_number" class="input font-mono" />
            </div>
          </div>
        </div>

        <!-- Representative -->
        <div class="space-y-3">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy">Representative (signs leases)</div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="label">Name</label>
              <input v-model="local.representative_name" class="input" />
            </div>
            <div>
              <label class="label">ID number</label>
              <input v-model="local.representative_id_number" class="input font-mono" />
            </div>
            <div>
              <label class="label">Email</label>
              <input v-model="local.representative_email" type="email" class="input" />
            </div>
            <div>
              <label class="label">Phone</label>
              <input v-model="local.representative_phone" class="input" />
            </div>
          </div>
        </div>

        <!-- Address -->
        <div class="space-y-3">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy">Address (Domicilium)</div>
          <div>
            <label class="label">Search address</label>
            <AddressAutocomplete input-class="input" @select="onAddressSelect" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="col-span-2">
              <label class="label">Street</label>
              <input v-model="local.address.street" class="input" />
            </div>
            <div>
              <label class="label">City</label>
              <input v-model="local.address.city" class="input" />
            </div>
            <div>
              <label class="label">Province</label>
              <input v-model="local.address.province" class="input" />
            </div>
            <div>
              <label class="label">Postal code</label>
              <input v-model="local.address.postal_code" class="input" />
            </div>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <button type="submit" class="btn-primary text-xs" :disabled="saving">
            <Loader2 v-if="saving" :size="12" class="animate-spin mr-1" />
            Save Changes
          </button>
          <button type="button" class="btn-ghost text-xs text-danger-500 hover:bg-danger-50" @click="confirmDelete">Delete</button>
        </div>
      </form>

      <!-- Properties -->
      <div class="space-y-2">
        <div class="text-xs font-semibold uppercase tracking-wide text-navy">Properties</div>
        <div v-if="local.properties?.length" class="flex flex-wrap gap-2">
          <span
            v-for="p in local.properties"
            :key="p.id"
            class="text-xs px-2.5 py-1 rounded-lg bg-gray-50 border border-gray-200 text-gray-700"
          >
            {{ p.name }}
          </span>
        </div>
        <p v-else class="text-xs text-gray-400">No properties linked. Link this landlord from a property's Landlord tab.</p>
      </div>

      <!-- Bank accounts -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <div class="text-xs font-semibold uppercase tracking-wide text-navy">Bank Accounts</div>
          <button type="button" class="text-xs text-navy hover:underline flex items-center gap-1" @click="addBankAccount">
            <Plus :size="11" /> Add account
          </button>
        </div>

        <div v-if="!local.bank_accounts?.length" class="text-xs text-gray-400 py-2">No bank accounts added.</div>

        <div v-for="(ba, idx) in local.bank_accounts" :key="ba.id ?? `new-${idx}`" class="border border-gray-200 rounded-lg p-3 space-y-2">
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="label">Bank</label>
              <input v-model="ba.bank_name" class="input input-sm" />
            </div>
            <div>
              <label class="label">Account holder</label>
              <input v-model="ba.account_holder" class="input input-sm" />
            </div>
            <div>
              <label class="label">Account no.</label>
              <input v-model="ba.account_number" class="input input-sm font-mono" />
            </div>
            <div>
              <label class="label">Branch code</label>
              <input v-model="ba.branch_code" class="input input-sm font-mono" />
            </div>
            <div>
              <label class="label">Type</label>
              <input v-model="ba.account_type" class="input input-sm" placeholder="e.g. Cheque, Savings" />
            </div>
            <div>
              <label class="label">Label</label>
              <input v-model="ba.label" class="input input-sm" placeholder="e.g. Main rental account" />
            </div>
          </div>
          <div class="flex items-center justify-between">
            <label class="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer">
              <input type="checkbox" v-model="ba.is_default" class="rounded text-navy" />
              Default account
            </label>
            <div class="flex items-center gap-2">
              <button type="button" class="btn-primary text-xs !py-1 !px-3" @click="saveBankAccount(ba)" :disabled="saving">
                <Loader2 v-if="saving" :size="12" class="animate-spin mr-1" />
                {{ ba.id ? 'Update' : 'Save Account' }}
              </button>
              <button v-if="ba.id" type="button" class="text-xs text-danger-500 hover:underline" @click="deleteBankAccount(ba)">Remove</button>
              <button v-else type="button" class="text-xs text-gray-400 hover:underline" @click="local.bank_accounts.splice(idx, 1)">Cancel</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :open="deleteOpen"
      title="Delete landlord?"
      :description="`Delete landlord '${local.name ?? ''}'? This cannot be undone.`"
      confirm-label="Delete"
      :loading="deleteBusy"
      @confirm="doDeleteLandlord"
      @cancel="deleteOpen = false"
    />
  </BaseDrawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Loader2, Plus } from 'lucide-vue-next'
import BaseDrawer from '../../components/BaseDrawer.vue'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import AddressAutocomplete, { type AddressResult } from '../../components/AddressAutocomplete.vue'
import { useToast } from '../../composables/useToast'
import { extractApiError } from '../../utils/api-errors'
import { useLandlordsStore } from '../../stores/landlords'
import type { BankAccount, Landlord } from '../../types/landlord'

const props = defineProps<{
  open: boolean
  landlord: Landlord | null
}>()

const emit = defineEmits<{ close: []; saved: [] }>()

const toast = useToast()
const landlordsStore = useLandlordsStore()
const saving = ref(false)
const local = ref<any>({})

const deleteOpen = ref(false)
const deleteBusy = ref(false)

watch(() => props.landlord, (ll) => {
  if (ll) {
    local.value = {
      ...JSON.parse(JSON.stringify(ll)),
      address: ll.address && typeof ll.address === 'object' ? { ...ll.address } : {},
    }
  }
}, { immediate: true })

function onAddressSelect(result: AddressResult) {
  if (!local.value.address) local.value.address = {}
  local.value.address.street = result.street || result.formatted
  local.value.address.city = result.city
  local.value.address.province = result.province
  local.value.address.postal_code = result.postal_code
}

async function saveLandlord() {
  saving.value = true
  try {
    // Persist the landlord patch (the store strips read-only fields).
    await landlordsStore.update(local.value.id, local.value)
    // Save any locally-added bank accounts that haven't been persisted yet.
    const unsaved = (local.value.bank_accounts as BankAccount[] | undefined)?.filter(
      (ba) => !ba.id && ba.bank_name,
    ) ?? []
    for (const ba of unsaved) {
      await landlordsStore.saveBankAccount(local.value.id, ba)
    }
    toast.success('Landlord saved')
    emit('saved')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to save landlord'))
  } finally {
    saving.value = false
  }
}

function confirmDelete() {
  deleteOpen.value = true
}

async function doDeleteLandlord() {
  deleteBusy.value = true
  try {
    await landlordsStore.remove(local.value.id)
    deleteOpen.value = false
    toast.success('Landlord deleted')
    emit('saved')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to delete landlord'))
  } finally {
    deleteBusy.value = false
  }
}

function addBankAccount() {
  if (!local.value.bank_accounts) local.value.bank_accounts = []
  local.value.bank_accounts.push({
    landlord: local.value.id,
    bank_name: '', branch_code: '', account_number: '',
    account_type: '', account_holder: '', label: '', is_default: false,
  })
}

async function saveBankAccount(ba: BankAccount) {
  saving.value = true
  try {
    await landlordsStore.saveBankAccount(local.value.id, ba)
    toast.success('Bank account saved')
    emit('saved')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to save bank account'))
  } finally {
    saving.value = false
  }
}

async function deleteBankAccount(ba: BankAccount) {
  if (!ba.id) return
  try {
    await landlordsStore.deleteBankAccount(local.value.id, ba.id)
    toast.success('Bank account removed')
    emit('saved')
  } catch (err) {
    toast.error(extractApiError(err, 'Failed to remove bank account'))
  }
}
</script>
