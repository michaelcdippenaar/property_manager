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
      color="secondary"
      label="Create Lease"
      icon="description"
      :rounded="isIos"
      unelevated
      :loading="submitting"
      class="full-width q-py-sm"
      size="lg"
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
import { getViewing, convertViewingToLease, type PropertyViewing } from '../services/api'
import { usePlatform } from '../composables/usePlatform'

const props  = defineProps<{ viewingId: number }>()
const router = useRouter()
const $q     = useQuasar()
const { isIos } = usePlatform()

const viewing     = ref<PropertyViewing | null>(null)
const leaseForm   = ref()
const submitting  = ref(false)
const submitError = ref('')

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
})

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
    const lease = await convertViewingToLease(props.viewingId, {
      start_date:   form.value.start_date,
      end_date:     form.value.end_date,
      monthly_rent: form.value.monthly_rent,
      deposit:      form.value.deposit,
    })

    $q.notify({
      type:    'positive',
      message: `Lease created — ${viewing.value?.prospect_name} @ ${viewing.value?.property_name}`,
      icon:    'description',
      timeout: 4000,
    })

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

  // Confirm viewing can be converted
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
  if (!viewing.value.unit) {
    $q.notify({ type: 'warning', message: 'A unit must be selected before creating a lease.' })
    void router.back()
    return
  }

  // Pre-fill rent from unit if available (viewing comes with unit data via viewing detail)
})
</script>

<style scoped lang="scss">
.section-card {
  border-radius: 12px;
  border: 1px solid rgba(0,0,0,0.08);
  overflow: hidden;
}
</style>
