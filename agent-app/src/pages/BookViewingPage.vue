<template>
  <q-page class="q-pa-md">

    <q-stepper
      v-model="step"
      ref="stepperRef"
      color="primary"
      animated
      flat
      bordered
    >
      <!-- ── Step 1: Viewing Details ───────────────────────────────────────── -->
      <q-step :name="1" title="Viewing Details" icon="event" :done="step > 1">

        <q-form ref="form1" class="column q-gutter-md">

          <!-- Property selector -->
          <q-select
            v-model="form.property"
            :options="propertyOptions"
            label="Property *"
            option-value="id"
            option-label="name"
            emit-value
            map-options
            outlined
            :rounded="isIos"
            :loading="loadingProps"
            :rules="[v => !!v || 'Select a property']"
            @update:model-value="onPropertyChange"
          >
            <template #prepend>
              <q-icon name="home" color="primary" />
            </template>
          </q-select>

          <!-- Unit selector -->
          <q-select
            v-model="form.unit"
            :options="unitOptions"
            label="Unit (optional)"
            option-value="id"
            option-label="label"
            emit-value
            map-options
            outlined
            :rounded="isIos"
            clearable
            :disable="!form.property || unitOptions.length === 0"
          >
            <template #prepend>
              <q-icon name="door_front" color="primary" />
            </template>
            <template #hint>
              <span v-if="form.property && unitOptions.length === 0" class="text-negative">
                No available units for this property
              </span>
            </template>
          </q-select>

          <!-- Date -->
          <q-input
            v-model="form.date"
            label="Viewing date *"
            outlined
            :rounded="isIos"
            :rules="[v => !!v || 'Select a date']"
            readonly
          >
            <template #prepend>
              <q-icon name="calendar_today" color="primary" />
            </template>
            <template #append>
              <q-icon name="event" class="cursor-pointer">
                <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                  <q-date v-model="form.date" mask="YYYY-MM-DD" :options="futureDatesOnly">
                    <div class="row items-center justify-end">
                      <q-btn v-close-popup label="Close" color="primary" flat />
                    </div>
                  </q-date>
                </q-popup-proxy>
              </q-icon>
            </template>
          </q-input>

          <!-- Time -->
          <q-input
            v-model="form.time"
            label="Viewing time *"
            outlined
            :rounded="isIos"
            :rules="[v => !!v || 'Select a time']"
            readonly
          >
            <template #prepend>
              <q-icon name="schedule" color="primary" />
            </template>
            <template #append>
              <q-icon name="access_time" class="cursor-pointer">
                <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                  <q-time v-model="form.time" format24h>
                    <div class="row items-center justify-end">
                      <q-btn v-close-popup label="Close" color="primary" flat />
                    </div>
                  </q-time>
                </q-popup-proxy>
              </q-icon>
            </template>
          </q-input>

          <!-- Duration -->
          <q-select
            v-model="form.duration"
            :options="durationOptions"
            label="Duration"
            outlined
            :rounded="isIos"
            emit-value
            map-options
          >
            <template #prepend>
              <q-icon name="timer" color="primary" />
            </template>
          </q-select>

          <!-- Notes -->
          <q-input
            v-model="form.notes"
            label="Notes (optional)"
            type="textarea"
            outlined
            :rounded="isIos"
            rows="3"
            autogrow
          >
            <template #prepend>
              <q-icon name="notes" color="primary" />
            </template>
          </q-input>

        </q-form>

        <q-stepper-navigation class="q-pt-md">
          <q-btn
            @click="goToStep2"
            color="primary"
            label="Next: Prospect Details"
            :rounded="isIos"
            unelevated
            class="full-width"
          />
        </q-stepper-navigation>
      </q-step>

      <!-- ── Step 2: Prospect Capture ──────────────────────────────────────── -->
      <q-step :name="2" title="Prospect Details" icon="person" :done="step > 2">

        <q-form ref="form2" class="column q-gutter-md">

          <div class="text-caption text-grey-6 q-mb-xs">
            Capture the potential tenant's details
          </div>

          <!-- Name -->
          <div class="row q-col-gutter-sm">
            <div class="col-6">
              <q-input
                v-model="prospect.first_name"
                label="First name *"
                outlined
                :rounded="isIos"
                :rules="[v => !!v || 'Required']"
              />
            </div>
            <div class="col-6">
              <q-input
                v-model="prospect.last_name"
                label="Last name *"
                outlined
                :rounded="isIos"
                :rules="[v => !!v || 'Required']"
              />
            </div>
          </div>

          <!-- Contact -->
          <q-input
            v-model="prospect.phone"
            label="Mobile number *"
            type="tel"
            outlined
            :rounded="isIos"
            :rules="[v => !!v || 'Required']"
          >
            <template #prepend><q-icon name="phone" color="primary" /></template>
          </q-input>

          <q-input
            v-model="prospect.email"
            label="Email address"
            type="email"
            outlined
            :rounded="isIos"
          >
            <template #prepend><q-icon name="mail" color="primary" /></template>
          </q-input>

          <!-- ID number -->
          <q-input
            v-model="prospect.id_number"
            label="SA ID / Passport number"
            outlined
            :rounded="isIos"
            maxlength="20"
          >
            <template #prepend><q-icon name="badge" color="primary" /></template>
          </q-input>

          <!-- Current address -->
          <q-input
            v-model="prospect.address"
            label="Current address"
            type="textarea"
            outlined
            :rounded="isIos"
            rows="2"
            autogrow
          >
            <template #prepend><q-icon name="location_on" color="primary" /></template>
          </q-input>

        </q-form>

        <q-banner v-if="submitError" rounded class="bg-negative text-white q-mt-md text-caption">
          {{ submitError }}
        </q-banner>

        <q-stepper-navigation class="q-pt-md column q-gutter-sm">
          <q-btn
            @click="submitBooking"
            color="secondary"
            label="Book Viewing"
            icon="event_available"
            :rounded="isIos"
            unelevated
            :loading="submitting"
            class="full-width"
          />
          <q-btn
            flat
            color="primary"
            label="Back"
            :rounded="isIos"
            @click="step = 1"
            class="full-width"
          />
        </q-stepper-navigation>
      </q-step>

    </q-stepper>

  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import {
  listProperties, listUnits,
  createPerson, createViewing,
  type Property, type Unit,
} from '../services/api'
import { usePlatform } from '../composables/usePlatform'
import { formatZAR } from '../utils/designTokens'

const props = defineProps<{
  prePropertyId?: number
  preUnitId?: number
}>()

const router = useRouter()
const $q     = useQuasar()
const { isIos } = usePlatform()

// ── Stepper ──────────────────────────────────────────────────────────────────
const step      = ref(1)
const stepperRef = ref()
const form1     = ref()
const form2     = ref()

// ── Form data ─────────────────────────────────────────────────────────────────
const form = ref({
  property: props.prePropertyId ?? null as number | null,
  unit:     props.preUnitId ?? null as number | null,
  date:     '',
  time:     '09:00',
  duration: 30,
  notes:    '',
})

const prospect = ref({
  first_name: '',
  last_name:  '',
  phone:      '',
  email:      '',
  id_number:  '',
  address:    '',
})

// ── Options ───────────────────────────────────────────────────────────────────
const loadingProps     = ref(false)
const properties       = ref<Property[]>([])
const units            = ref<Unit[]>([])
const submitting       = ref(false)
const submitError      = ref('')

const propertyOptions = computed(() =>
  properties.value.map((p) => ({ id: p.id, name: p.name })),
)

const unitOptions = computed(() =>
  units.value
    .filter((u) => u.status === 'available')
    .map((u) => ({
      id: u.id,
      label: `Unit ${u.unit_number} — R${formatZAR(u.rent_amount)}`,
    })),
)

const durationOptions = [
  { label: '15 minutes', value: 15 },
  { label: '30 minutes', value: 30 },
  { label: '45 minutes', value: 45 },
  { label: '1 hour',     value: 60 },
]

function futureDatesOnly(dateStr: string) {
  return dateStr >= new Date().toISOString().slice(0, 10)
}

async function onPropertyChange(propId: number | null) {
  form.value.unit = null
  units.value = []
  if (!propId) return
  const resp = await listUnits(propId)
  units.value = resp.results
}

async function goToStep2() {
  const valid = await form1.value?.validate()
  if (valid) step.value = 2
}

async function submitBooking() {
  const valid = await form2.value?.validate()
  if (!valid) return

  submitting.value = true
  submitError.value = ''

  try {
    // 1. Create or find prospect Person
    const person = await createPerson({
      full_name: `${prospect.value.first_name} ${prospect.value.last_name}`.trim(),
      id_number: prospect.value.id_number,
      phone:     prospect.value.phone,
      email:     prospect.value.email,
      address:   prospect.value.address,
    })

    // 2. Combine date + time → ISO datetime
    const scheduledAt = `${form.value.date}T${form.value.time}:00`

    // 3. Create viewing
    const viewing = await createViewing({
      property:        form.value.property!,
      unit:            form.value.unit,
      prospect:        person.id,
      scheduled_at:    scheduledAt,
      duration_minutes: form.value.duration,
      notes:           form.value.notes,
    })

    $q.notify({ type: 'positive', message: `Viewing booked for ${person.full_name}`, icon: 'event_available' })
    await router.replace(`/viewings/${viewing.id}`)
  } catch (err: unknown) {
    const axiosErr = err as { response?: { data?: Record<string, unknown> } }
    const data = axiosErr.response?.data
    submitError.value = data
      ? Object.values(data).flat().join(' ')
      : 'Failed to book viewing. Please try again.'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  loadingProps.value = true
  try {
    const resp = await listProperties()
    properties.value = resp.results
    if (form.value.property) {
      await onPropertyChange(form.value.property)
    }
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to load properties.', icon: 'error' })
  } finally {
    loadingProps.value = false
  }
})
</script>

<style scoped lang="scss">
// Quasar stepper uses flat + bordered props; wrap in section-card for consistent styling
:deep(.q-stepper) {
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-border);
  box-shadow: none;
}
</style>
