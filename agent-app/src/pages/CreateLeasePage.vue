<template>
  <q-page class="q-pa-md" v-if="viewing">

    <!-- Summary card — pre-filled from viewing -->
    <q-card flat class="section-card q-mb-md">
      <q-card-section class="q-pb-xs">
        <div class="text-subtitle2 text-weight-semibold text-grey-8">From Viewing</div>
      </q-card-section>
      <q-separator />
      <q-list dense>
        <q-item>
          <q-item-section avatar><q-icon name="person" color="primary" size="20px" /></q-item-section>
          <q-item-section>
            <q-item-label class="text-weight-medium">{{ viewing.prospect_name }}</q-item-label>
            <q-item-label caption>Primary tenant</q-item-label>
          </q-item-section>
        </q-item>
        <q-item>
          <q-item-section avatar><q-icon name="home_work" color="primary" size="20px" /></q-item-section>
          <q-item-section>
            <q-item-label>{{ viewing.property_name }}</q-item-label>
            <q-item-label caption v-if="viewing.unit_number">Unit {{ viewing.unit_number }}</q-item-label>
            <q-item-label caption v-else-if="units.length > 1" class="text-warning">Select a unit below</q-item-label>
            <q-item-label caption v-else-if="units.length === 1">Unit {{ units[0].unit_number }}</q-item-label>
            <q-item-label caption v-else-if="!loadingUnits">Whole property</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <!-- Lease form -->
    <q-card flat class="section-card q-mb-md">
      <q-card-section class="q-pb-xs">
        <div class="text-subtitle2 text-weight-semibold text-grey-8">Lease Terms</div>
      </q-card-section>
      <q-separator />
      <q-card-section>
        <q-form ref="leaseForm" class="column q-gutter-md">

          <!-- Start date -->
          <q-input
            v-model="form.start_date"
            label="Lease start date *"
            outlined
            :rounded="isIos"
            :rules="[v => !!v || 'Required']"
            readonly
          >
            <template #prepend><q-icon name="calendar_today" color="primary" /></template>
            <template #append>
              <q-icon name="event" class="cursor-pointer">
                <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                  <q-date v-model="form.start_date" mask="YYYY-MM-DD">
                    <div class="row justify-end">
                      <q-btn v-close-popup label="Close" color="primary" flat />
                    </div>
                  </q-date>
                </q-popup-proxy>
              </q-icon>
            </template>
          </q-input>

          <!-- End date -->
          <q-input
            v-model="form.end_date"
            label="Lease end date *"
            outlined
            :rounded="isIos"
            :rules="[v => !!v || 'Required', v => v > form.start_date || 'Must be after start date']"
            readonly
          >
            <template #prepend><q-icon name="event_busy" color="primary" /></template>
            <template #append>
              <q-icon name="event" class="cursor-pointer">
                <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                  <q-date v-model="form.end_date" mask="YYYY-MM-DD" :options="d => d >= form.start_date">
                    <div class="row justify-end">
                      <q-btn v-close-popup label="Close" color="primary" flat />
                    </div>
                  </q-date>
                </q-popup-proxy>
              </q-icon>
            </template>
          </q-input>

          <!-- Monthly rent -->
          <q-input
            v-model="form.monthly_rent"
            label="Monthly rent (ZAR) *"
            type="number"
            outlined
            :rounded="isIos"
            prefix="R"
            :rules="[v => !!v && Number(v) > 0 || 'Enter a valid amount']"
          >
            <template #prepend><q-icon name="payments" color="primary" /></template>
          </q-input>

          <!-- Deposit -->
          <q-input
            v-model="form.deposit"
            label="Security deposit (ZAR) *"
            type="number"
            outlined
            :rounded="isIos"
            prefix="R"
            :rules="[v => !!v && Number(v) > 0 || 'Enter a valid amount']"
            :hint="`Typically 1-2 months rent (R${oneMonthRent})`"
          >
            <template #prepend><q-icon name="account_balance" color="primary" /></template>
          </q-input>

          <!-- Unit selector (only when viewing has no unit AND the property has
               more than one unit). Single-unit or unit-less properties skip this
               step — the backend will auto-create a default unit if needed. -->
          <q-select
            v-if="!viewing.unit && units.length > 1"
            v-model="form.unit"
            :options="unitOptions"
            option-value="id"
            option-label="label"
            emit-value
            map-options
            label="Select unit *"
            outlined
            :rounded="isIos"
            :loading="loadingUnits"
            :rules="[v => !!v || 'Please select a unit']"
          >
            <template #prepend><q-icon name="door_front" color="primary" /></template>
          </q-select>

          <!-- Lease duration helper -->
          <div v-if="form.start_date && form.end_date" class="text-caption text-grey-6">
            <q-icon name="info" size="14px" />
            Lease duration: {{ leaseDuration }}
          </div>

        </q-form>
      </q-card-section>
    </q-card>

    <!-- Error -->
    <q-banner v-if="submitError" rounded class="bg-negative text-white text-caption q-mb-md">
      {{ submitError }}
    </q-banner>

    <!-- Submit -->
    <q-btn
      @click="createLease"
      color="primary"
      label="Create Lease"
      icon="description"
      :rounded="isIos"
      unelevated
      :loading="submitting"
      class="full-width"
      size="md"
    />

    <div class="text-caption text-grey-5 text-center q-mt-sm">
      This will mark the viewing as converted and create a pending lease.
    </div>

  </q-page>

  <q-page v-else class="row justify-center items-center">
    <q-spinner-dots color="primary" size="40px" />
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { getViewing, convertViewingToLease, listUnits, type PropertyViewing, type Unit } from '../services/api'
import { usePlatform } from '../composables/usePlatform'

const props  = defineProps<{ viewingId: number }>()
const router = useRouter()
const $q     = useQuasar()
const { isIos } = usePlatform()

const viewing      = ref<PropertyViewing | null>(null)
const leaseForm    = ref()
const submitting   = ref(false)
const submitError  = ref('')
const loadingUnits = ref(false)
const units        = ref<Unit[]>([])

// Default lease: starts next month, 12-month term
const nextMonth  = new Date(new Date().setDate(1))
nextMonth.setMonth(nextMonth.getMonth() + 1)
const endDate    = new Date(nextMonth)
endDate.setFullYear(endDate.getFullYear() + 1)
endDate.setDate(endDate.getDate() - 1)

const form = ref({
  start_date:   nextMonth.toISOString().slice(0, 10),
  end_date:     endDate.toISOString().slice(0, 10),
  monthly_rent: '',
  deposit:      '',
  unit:         null as number | null,
})

const unitOptions = computed(() =>
  units.value.map((u) => ({
    id:    u.id,
    label: `Unit ${u.unit_number}${u.rent_amount ? ` — R${Number(u.rent_amount).toLocaleString('en-ZA')}` : ''}`,
  })),
)

const oneMonthRent = computed(() =>
  form.value.monthly_rent
    ? Number(form.value.monthly_rent).toLocaleString('en-ZA')
    : '—',
)

const leaseDuration = computed(() => {
  if (!form.value.start_date || !form.value.end_date) return ''
  const start = new Date(form.value.start_date)
  const end   = new Date(form.value.end_date)
  const months = (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth())
  return months === 12 ? '12 months (1 year)' : `${months} month${months !== 1 ? 's' : ''}`
})

async function createLease() {
  const valid = await leaseForm.value?.validate()
  if (!valid) return

  submitting.value  = true
  submitError.value = ''

  try {
    const payload: Parameters<typeof convertViewingToLease>[1] = {
      start_date:   form.value.start_date,
      end_date:     form.value.end_date,
      monthly_rent: form.value.monthly_rent,
      deposit:      form.value.deposit,
    }
    if (!viewing.value?.unit && form.value.unit) {
      payload.unit = form.value.unit
    }
    const result = await convertViewingToLease(props.viewingId, payload)

    $q.notify({
      type:    'positive',
      message: `Lease created — ${viewing.value?.prospect_name} @ ${viewing.value?.property_name}`,
      icon:    'description',
      timeout: 4000,
    })

    if (result.auto_created_unit) {
      $q.notify({
        type:    'info',
        message: result.message
          ?? `Default unit '${result.auto_created_unit.unit_number}' was auto-created for this property.`,
        icon:    'info',
        timeout: 6000,
      })
    }

    await router.replace('/dashboard')
  } catch (err: unknown) {
    const axiosErr = err as { response?: { data?: { detail?: string } } }
    submitError.value =
      axiosErr.response?.data?.detail || 'Failed to create lease. Please try again.'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  viewing.value = await getViewing(props.viewingId)

  if (viewing.value.status === 'converted') {
    $q.notify({ type: 'warning', message: 'This viewing is already converted to a lease.' })
    void router.back()
    return
  }
  if (viewing.value.status === 'cancelled') {
    $q.notify({ type: 'negative', message: 'Cannot convert a cancelled viewing.' })
    void router.back()
    return
  }

  // If no unit on the viewing, load the property's units for selection.
  // Auto-select when there's exactly one unit; skip selection entirely when
  // the property has none (backend will auto-create a default unit).
  if (!viewing.value.unit) {
    loadingUnits.value = true
    try {
      const resp = await listUnits(viewing.value.property)
      const available = resp.results.filter((u) => u.status === 'available')
      units.value = available.length ? available : resp.results
      if (units.value.length === 1) {
        form.value.unit = units.value[0].id
      }
    } finally {
      loadingUnits.value = false
    }
  }
})
</script>

<style scoped lang="scss">
.section-card {
  border-radius: 12px;
  border: 1px solid rgba(0,0,0,0.08);
  overflow: hidden;
}
</style>
