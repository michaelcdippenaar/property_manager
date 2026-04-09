<template>
  <q-page v-if="property" class="q-pa-md">

    <q-form ref="leaseForm" class="column q-gutter-md" @submit.prevent="submit">

      <!-- Property header (read-only context) -->
      <q-card flat class="context-card">
        <q-item>
          <q-item-section avatar>
            <q-avatar color="primary" text-color="white" size="42px">
              <q-icon name="home_work" size="22px" />
            </q-avatar>
          </q-item-section>
          <q-item-section>
            <q-item-label class="text-weight-semibold">{{ property.name }}</q-item-label>
            <q-item-label caption>{{ property.address }}, {{ property.city }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-card>

      <!-- ── Section: Unit ─────────────────────────────────────────────────── -->
      <div>
        <div class="form-section-label">Unit</div>
        <q-select
          v-model="form.unit"
          :options="unitOptions"
          option-value="id"
          option-label="label"
          emit-value
          map-options
          label="Select unit *"
          outlined
          :rounded="isIos"
          :rules="[v => !!v || 'Select a unit']"
          @update:model-value="onUnitChange"
        >
          <template #prepend><q-icon name="door_front" color="primary" /></template>
        </q-select>
      </div>

      <!-- ── Section: Tenant ───────────────────────────────────────────────── -->
      <div>
        <div class="form-section-label">Tenant</div>

        <!-- Search existing person -->
        <q-select
          v-model="selectedPerson"
          :options="personOptions"
          option-value="id"
          option-label="full_name"
          emit-value
          map-options
          label="Search existing tenant"
          outlined
          :rounded="isIos"
          use-input
          input-debounce="400"
          clearable
          @filter="searchPersons"
          @update:model-value="onPersonSelected"
        >
          <template #prepend><q-icon name="search" color="primary" /></template>
          <template #no-option>
            <q-item>
              <q-item-section class="text-grey-5 text-caption">No matches — fill in below</q-item-section>
            </q-item>
          </template>
        </q-select>

        <div class="text-caption text-grey-5 text-center q-my-xs">— or enter new tenant details —</div>

        <div class="row q-col-gutter-sm">
          <div class="col-6">
            <q-input v-model="tenant.first_name" label="First name *" outlined :rounded="isIos"
              :rules="[v => !!v || 'Required']" />
          </div>
          <div class="col-6">
            <q-input v-model="tenant.last_name" label="Last name *" outlined :rounded="isIos"
              :rules="[v => !!v || 'Required']" />
          </div>
        </div>

        <q-input v-model="tenant.phone" label="Mobile number *" type="tel" outlined :rounded="isIos"
          :rules="[v => !!v || 'Required']">
          <template #prepend><q-icon name="phone" color="primary" /></template>
        </q-input>

        <q-input v-model="tenant.email" label="Email address" type="email" outlined :rounded="isIos">
          <template #prepend><q-icon name="mail" color="primary" /></template>
        </q-input>

        <q-input v-model="tenant.id_number" label="SA ID / Passport" outlined :rounded="isIos" maxlength="20">
          <template #prepend><q-icon name="badge" color="primary" /></template>
        </q-input>
      </div>

      <!-- ── Section: Lease terms ──────────────────────────────────────────── -->
      <div>
        <div class="form-section-label">Lease Terms</div>

        <!-- Start date -->
        <q-input v-model="form.start_date" label="Start date *" outlined :rounded="isIos"
          :rules="[v => !!v || 'Required']" readonly>
          <template #prepend><q-icon name="calendar_today" color="primary" /></template>
          <template #append>
            <q-icon name="event" class="cursor-pointer">
              <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                <q-date v-model="form.start_date" mask="YYYY-MM-DD">
                  <div class="row items-center justify-end">
                    <q-btn v-close-popup label="Close" color="primary" flat />
                  </div>
                </q-date>
              </q-popup-proxy>
            </q-icon>
          </template>
        </q-input>

        <!-- End date -->
        <q-input v-model="form.end_date" label="End date *" outlined :rounded="isIos"
          :rules="[v => !!v || 'Required']" readonly>
          <template #prepend><q-icon name="event_busy" color="primary" /></template>
          <template #append>
            <q-icon name="event" class="cursor-pointer">
              <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                <q-date v-model="form.end_date" mask="YYYY-MM-DD" :options="afterStartDate">
                  <div class="row items-center justify-end">
                    <q-btn v-close-popup label="Close" color="primary" flat />
                  </div>
                </q-date>
              </q-popup-proxy>
            </q-icon>
          </template>
        </q-input>

        <!-- Duration helper -->
        <div v-if="leaseDuration" class="text-caption text-grey-6 q-mt-xs q-ml-xs">
          <q-icon name="info" size="13px" /> {{ leaseDuration }}
        </div>

        <!-- Monthly rent -->
        <q-input v-model="form.monthly_rent" label="Monthly rent (ZAR) *" type="number" outlined
          :rounded="isIos" prefix="R" class="q-mt-sm"
          :rules="[v => !!v && Number(v) > 0 || 'Enter a valid amount']">
          <template #prepend><q-icon name="payments" color="primary" /></template>
        </q-input>

        <!-- Deposit -->
        <q-input v-model="form.deposit" label="Security deposit (ZAR) *" type="number" outlined
          :rounded="isIos" prefix="R"
          :hint="form.monthly_rent ? `Typically 1–2 months (R${oneMonthRent}–R${twoMonthsRent})` : ''"
          :rules="[v => !!v && Number(v) > 0 || 'Enter a valid amount']">
          <template #prepend><q-icon name="account_balance" color="primary" /></template>
        </q-input>

        <!-- Rent due day -->
        <q-select v-model="form.rent_due_day" :options="dueDayOptions" label="Rent due day"
          emit-value map-options outlined :rounded="isIos">
          <template #prepend><q-icon name="schedule" color="primary" /></template>
        </q-select>
      </div>

      <!-- Error -->
      <q-banner v-if="submitError" rounded class="bg-negative text-white text-caption">
        {{ submitError }}
      </q-banner>

      <!-- Submit -->
      <q-btn
        type="submit"
        color="primary"
        label="Create Lease"
        icon="description"
        :rounded="isIos"
        unelevated
        :loading="submitting"
        class="full-width"
        size="md"
      />

    </q-form>

  </q-page>

  <q-page v-else class="row justify-center items-center">
    <q-spinner-dots color="primary" size="40px" />
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import {
  getProperty, searchPersons as apiSearchPersons, createPerson,
  createLeaseDirect, type Property, type Person,
} from '../services/api'
import { usePlatform } from '../composables/usePlatform'

const props = defineProps<{ propertyId: number }>()
const router   = useRouter()
const $q       = useQuasar()
const { isIos } = usePlatform()

// ── State ─────────────────────────────────────────────────────────────────────
const property     = ref<Property | null>(null)
const submitting   = ref(false)
const submitError  = ref('')
const leaseForm    = ref()
const personOptions = ref<Person[]>([])
const selectedPerson = ref<number | null>(null)

// ── Form data ─────────────────────────────────────────────────────────────────
const nextMonth = new Date()
nextMonth.setMonth(nextMonth.getMonth() + 1)
nextMonth.setDate(1)
const endDate = new Date(nextMonth)
endDate.setFullYear(endDate.getFullYear() + 1)
endDate.setDate(endDate.getDate() - 1)

const form = ref({
  unit:         null as number | null,
  start_date:   nextMonth.toISOString().slice(0, 10),
  end_date:     endDate.toISOString().slice(0, 10),
  monthly_rent: '',
  deposit:      '',
  rent_due_day: 1,
})

const tenant = ref({
  first_name: '',
  last_name:  '',
  phone:      '',
  email:      '',
  id_number:  '',
})

// ── Options ───────────────────────────────────────────────────────────────────
const unitOptions = computed(() =>
  (property.value?.units ?? []).map((u) => ({
    id:    u.id,
    label: `Unit ${u.unit_number} — R${Number(u.rent_amount).toLocaleString('en-ZA')}/mo (${u.status})`,
  })),
)

const dueDayOptions = Array.from({ length: 28 }, (_, i) => ({
  label: `${i + 1}${['st','nd','rd'][i] ?? 'th'} of the month`,
  value: i + 1,
}))

const oneMonthRent  = computed(() => Number(form.value.monthly_rent).toLocaleString('en-ZA'))
const twoMonthsRent = computed(() => (Number(form.value.monthly_rent) * 2).toLocaleString('en-ZA'))

const leaseDuration = computed(() => {
  if (!form.value.start_date || !form.value.end_date) return ''
  const months = Math.round(
    (new Date(form.value.end_date).getTime() - new Date(form.value.start_date).getTime()) /
    (1000 * 60 * 60 * 24 * 30.44),
  )
  return months > 0 ? `${months} month${months !== 1 ? 's' : ''}` : ''
})

function afterStartDate(d: string) {
  return !form.value.start_date || d > form.value.start_date
}

// ── Person search / pre-fill ──────────────────────────────────────────────────
async function searchPersons(val: string, update: (fn: () => void) => void) {
  if (!val || val.length < 2) { update(() => { personOptions.value = [] }); return }
  const resp = await apiSearchPersons(val).catch(() => null)
  update(() => { personOptions.value = resp?.results ?? [] })
}

function onPersonSelected(personId: number | null) {
  if (!personId) return
  const p = personOptions.value.find((x) => x.id === personId)
  if (!p) return
  const parts = (p.full_name || '').split(' ')
  tenant.value.first_name = parts[0] ?? ''
  tenant.value.last_name  = parts.slice(1).join(' ')
  tenant.value.phone      = p.phone ?? ''
  tenant.value.email      = p.email ?? ''
  tenant.value.id_number  = p.id_number ?? ''
}

// ── Auto-fill rent from selected unit ────────────────────────────────────────
function onUnitChange(unitId: number | null) {
  if (!unitId || !property.value) return
  const unit = property.value.units.find((u) => u.id === unitId)
  if (unit && unit.rent_amount) {
    form.value.monthly_rent = unit.rent_amount
    form.value.deposit = String(Number(unit.rent_amount) * 2)
  }
}

// ── Submit ────────────────────────────────────────────────────────────────────
async function submit() {
  const valid = await leaseForm.value?.validate()
  if (!valid) return

  submitting.value  = true
  submitError.value = ''

  try {
    // 1. Resolve or create tenant person
    let personId = selectedPerson.value
    if (!personId) {
      const person = await createPerson({
        full_name: `${tenant.value.first_name} ${tenant.value.last_name}`.trim(),
        phone:     tenant.value.phone,
        email:     tenant.value.email,
        id_number: tenant.value.id_number,
      })
      personId = person.id
    }

    // 2. Create the lease
    const lease = await createLeaseDirect({
      unit:          form.value.unit!,
      primary_tenant: personId,
      start_date:    form.value.start_date,
      end_date:      form.value.end_date,
      monthly_rent:  form.value.monthly_rent,
      deposit:       form.value.deposit,
      rent_due_day:  form.value.rent_due_day,
    })

    $q.notify({ type: 'positive', message: 'Lease created successfully', icon: 'check_circle' })
    void router.replace(`/properties/${props.propertyId}`)
  } catch (err: unknown) {
    const axiosErr = err as { response?: { data?: Record<string, unknown> } }
    const data = axiosErr.response?.data
    submitError.value = data
      ? Object.values(data).flat().join(' ')
      : 'Failed to create lease. Please try again.'
  } finally {
    submitting.value = false
  }
}

// ── Load property ─────────────────────────────────────────────────────────────
onMounted(async () => {
  property.value = await getProperty(props.propertyId)

  // Pre-select first available unit if only one
  const available = property.value?.units.filter((u) => u.status === 'available') ?? []
  if (available.length === 1) {
    form.value.unit = available[0].id
    onUnitChange(available[0].id)
  }
})
</script>

<style scoped lang="scss">
.context-card {
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.form-section-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #9e9e9e;
  margin-bottom: 8px;
  margin-left: 2px;
}
</style>
