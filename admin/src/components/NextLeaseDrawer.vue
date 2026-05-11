<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex flex-col bg-white overflow-hidden">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 flex-shrink-0">
        <div class="flex items-center gap-3">
          <button
            @click="close"
            class="w-9 h-9 -ml-2 rounded-lg flex items-center justify-center text-gray-500 hover:bg-gray-100 hover:text-gray-900 transition-colors"
            aria-label="Close"
            title="Close (Esc)"
          >
            <X :size="20" />
          </button>
          <div class="w-7 h-7 rounded-lg bg-navy flex items-center justify-center">
            <FilePlus :size="14" class="text-white" />
          </div>
          <div>
            <div class="font-semibold text-gray-900 text-sm">Prepare next lease</div>
            <div class="text-xs text-gray-400">Follows {{ source?.lease_number || 'current lease' }} · Tenants left blank — fill in new occupants</div>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <button @click="close" class="btn-ghost">Cancel</button>
          <button @click="save" :disabled="saving || !canSave" class="btn-primary">
            <Loader2 v-if="saving" :size="14" class="animate-spin" />
            Save as pending
          </button>
        </div>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto">
        <div class="max-w-2xl mx-auto px-6 py-8 space-y-6">

          <div v-if="loading" class="text-sm text-gray-500 text-center py-8">Loading source lease…</div>
          <div v-else-if="loadError" class="px-4 py-3 bg-danger-50 border border-danger-100 rounded-xl text-sm text-danger-700">
            {{ loadError }}
          </div>
          <template v-else-if="source">
            <div class="px-4 py-3 bg-warning-50 border border-warning-100 rounded-xl text-xs text-warning-700 flex items-start gap-2">
              <Info :size="14" class="flex-shrink-0 mt-0.5" />
              <div>
                <strong>Renewal with new tenants.</strong> This lease will follow {{ source?.lease_number || 'the source lease' }} with empty tenants — capture the new tenants after saving. To extend with the <em>same</em> tenants, use "Extend lease" instead.
              </div>
            </div>

            <section>
              <div class="text-micro font-semibold text-gray-400 uppercase tracking-widest mb-3">Period</div>
              <div class="card p-5 grid grid-cols-2 gap-4">
                <div>
                  <label class="label">Start Date</label>
                  <input v-model="form.start_date" type="date" class="input" />
                </div>
                <div>
                  <label class="label">End Date</label>
                  <input v-model="form.end_date" type="date" class="input" />
                </div>
              </div>
            </section>

            <section>
              <div class="text-micro font-semibold text-gray-400 uppercase tracking-widest mb-3">Financial</div>
              <div class="card p-5 grid grid-cols-2 gap-4">
                <div>
                  <label class="label">Monthly Rent (R)</label>
                  <input v-model.number="form.monthly_rent" type="number" class="input" step="0.01" />
                </div>
                <div>
                  <label class="label">Deposit (R)</label>
                  <input v-model.number="form.deposit" type="number" class="input" step="0.01" />
                </div>
                <div>
                  <label class="label">Rent Due Day</label>
                  <input v-model.number="form.rent_due_day" type="number" min="1" max="28" class="input" />
                </div>
              </div>
            </section>

            <section>
              <div class="text-micro font-semibold text-gray-400 uppercase tracking-widest mb-3">Terms</div>
              <div class="card p-5 grid grid-cols-2 gap-4">
                <div>
                  <label class="label">Notice Period (days)</label>
                  <input v-model.number="form.notice_period_days" type="number" class="input" />
                </div>
                <div>
                  <label class="label">Early Termination Penalty (months)</label>
                  <input v-model.number="form.early_termination_penalty_months" type="number" class="input" />
                </div>
                <div>
                  <label class="label">Max Occupants</label>
                  <input v-model.number="form.max_occupants" type="number" class="input" />
                </div>
                <div>
                  <label class="label">Water Limit (litres)</label>
                  <input v-model.number="form.water_limit_litres" type="number" class="input" />
                </div>
              </div>
            </section>

            <section>
              <div class="text-micro font-semibold text-gray-400 uppercase tracking-widest mb-3">Property services &amp; facilities</div>
              <div class="card p-5 grid grid-cols-2 gap-4">
                <div>
                  <label class="label">Water</label>
                  <select v-model="form.water_arrangement" class="input">
                    <option value="included">Included in rent</option>
                    <option value="not_included">Not included</option>
                  </select>
                </div>
                <div>
                  <label class="label">Electricity</label>
                  <select v-model="form.electricity_arrangement" class="input">
                    <option value="prepaid">Prepaid</option>
                    <option value="eskom_direct">Direct Eskom account</option>
                    <option value="included">Included in rent</option>
                    <option value="not_included">Tenant arranges separately</option>
                  </select>
                </div>
                <div class="col-span-2 flex flex-wrap items-center gap-x-5 gap-y-2 pt-1">
                  <label class="inline-flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input v-model="form.gardening_service_included" type="checkbox" class="rounded" /> Gardening service
                  </label>
                  <label class="inline-flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input v-model="form.wifi_included" type="checkbox" class="rounded" /> Wifi included
                  </label>
                  <label class="inline-flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input v-model="form.security_service_included" type="checkbox" class="rounded" /> Armed response
                  </label>
                </div>
              </div>
            </section>

            <div v-if="saveError" class="px-4 py-3 bg-danger-50 border border-danger-100 rounded-xl text-sm text-danger-700 flex items-center gap-2">
              <AlertCircle :size="14" /> {{ saveError }}
            </div>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { FilePlus, Info, AlertCircle, Loader2, X } from 'lucide-vue-next'
import { useLeasesStore } from '../stores/leases'

const props = defineProps<{ sourceLeaseId: number }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', id: number): void
}>()

const leasesStore = useLeasesStore()
const source = ref<any | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const saving = ref(false)
const saveError = ref<string | null>(null)

const form = reactive<{
  start_date: string
  end_date: string
  monthly_rent: number | null
  deposit: number | null
  rent_due_day: number | null
  notice_period_days: number | null
  early_termination_penalty_months: number | null
  max_occupants: number | null
  water_limit_litres: number | null
  water_arrangement: 'included' | 'not_included'
  electricity_arrangement: 'prepaid' | 'eskom_direct' | 'included' | 'not_included'
  gardening_service_included: boolean
  wifi_included: boolean
  security_service_included: boolean
}>({
  start_date: '',
  end_date: '',
  monthly_rent: null,
  deposit: null,
  rent_due_day: 1,
  notice_period_days: 20,
  early_termination_penalty_months: 3,
  max_occupants: 1,
  water_limit_litres: 4000,
  water_arrangement: 'not_included',
  electricity_arrangement: 'prepaid',
  gardening_service_included: false,
  wifi_included: false,
  security_service_included: false,
})

const canSave = computed(() => !!form.start_date && !!form.end_date)

function addDays(iso: string, days: number): string {
  const d = new Date(iso)
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}
function addMonths(iso: string, months: number): string {
  const d = new Date(iso)
  d.setMonth(d.getMonth() + months)
  return d.toISOString().slice(0, 10)
}

onMounted(async () => {
  loading.value = true
  loadError.value = null
  try {
    const s = await leasesStore.fetchOne(props.sourceLeaseId, { force: true })
    source.value = s
    const start = s.end_date ? addDays(s.end_date, 1) : new Date().toISOString().slice(0, 10)
    const end = addDays(addMonths(start, 12), -1)
    form.start_date = start
    form.end_date = end
    form.monthly_rent = Number(s.monthly_rent ?? 0)
    form.deposit = Number(s.deposit ?? 0)
    form.rent_due_day = s.rent_due_day ?? 1
    form.notice_period_days = s.notice_period_days ?? 20
    form.early_termination_penalty_months = s.early_termination_penalty_months ?? 3
    form.max_occupants = s.max_occupants ?? 1
    form.water_limit_litres = s.water_limit_litres ?? 4000
    // Carry forward services from the source lease so the renewal mirrors
    // the property's current arrangement by default.
    form.water_arrangement = (s.water_arrangement as any) ?? (s.water_included ? 'included' : 'not_included')
    form.electricity_arrangement = (s.electricity_arrangement as any) ?? (s.electricity_prepaid ? 'prepaid' : 'not_included')
    form.gardening_service_included = !!s.gardening_service_included
    form.wifi_included = !!s.wifi_included
    form.security_service_included = !!s.security_service_included
  } catch (e: any) {
    loadError.value = e?.message || 'Failed to load source lease'
  } finally {
    loading.value = false
  }
})

async function save() {
  saveError.value = null
  saving.value = true
  try {
    const created = await leasesStore.createRenewal(props.sourceLeaseId, { ...form })
    emit('saved', created.id)
    emit('close')
  } catch (e: any) {
    saveError.value = e?.response?.data?.error || e?.message || 'Failed to save'
  } finally {
    saving.value = false
  }
}

function close() { emit('close') }

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') close()
}

onMounted(() => document.addEventListener('keydown', handleKeydown))
onUnmounted(() => document.removeEventListener('keydown', handleKeydown))
</script>
