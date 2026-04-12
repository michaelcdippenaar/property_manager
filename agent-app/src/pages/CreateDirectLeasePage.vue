<template>
  <q-page v-if="property" class="q-pa-md">

    <q-form ref="leaseForm" @submit.prevent="submit">

      <!-- ── Property & Unit ──────────────────────────────────────────────── -->
      <q-card flat class="form-card q-mb-md">
        <q-item class="q-py-md">
          <q-item-section avatar>
            <q-avatar color="primary" text-color="white" size="40px">
              <q-icon name="home_work" size="20px" />
            </q-avatar>
          </q-item-section>
          <q-item-section>
            <q-item-label class="text-weight-semibold text-body1">{{ property.name }}</q-item-label>
            <q-item-label caption>{{ property.address }}, {{ property.city }}</q-item-label>
          </q-item-section>
        </q-item>
        <q-separator />
        <div class="q-pa-md">
          <q-select
            v-model="form.unit"
            :options="unitOptions"
            option-value="id"
            option-label="label"
            emit-value
            map-options
            label="Select unit *"
            outlined
            dense
            hide-bottom-space
            :rules="[RULES.requiredSelect]"
            @update:model-value="onUnitChange"
          >
            <template #prepend><q-icon name="door_front" size="20px" /></template>
          </q-select>
        </div>
      </q-card>

      <!-- ── Tenant ───────────────────────────────────────────────────────── -->
      <q-card flat class="form-card q-mb-md">
        <div class="form-card-header">
          <q-icon name="person" size="18px" color="primary" />
          <span>Tenant</span>
        </div>
        <q-separator />
        <div class="q-pa-md">
          <q-select
            v-model="selectedPerson"
            :options="personOptions"
            option-value="id"
            option-label="full_name"
            emit-value
            map-options
            label="Search existing tenant"
            outlined
            dense
            use-input
            input-debounce="400"
            clearable
            @filter="searchPersons"
            @update:model-value="onPersonSelected"
          >
            <template #prepend><q-icon name="search" size="20px" /></template>
            <template #no-option>
              <q-item>
                <q-item-section class="text-grey-5 text-caption">No matches — enter details below</q-item-section>
              </q-item>
            </template>
          </q-select>

          <div class="form-divider">
            <span>or new tenant</span>
          </div>

          <div class="tenant-fields">
            <div class="row q-col-gutter-sm">
              <div class="col-6">
                <q-input v-model="tenant.first_name" label="First name *" outlined dense
                  hide-bottom-space :rules="[RULES.required]" />
              </div>
              <div class="col-6">
                <q-input v-model="tenant.last_name" label="Last name *" outlined dense
                  hide-bottom-space :rules="[RULES.required]" />
              </div>
            </div>

            <q-input v-model="tenant.phone" label="Mobile number *" type="tel" outlined dense
              hide-bottom-space :rules="[RULES.required]">
              <template #prepend><q-icon name="phone" size="20px" /></template>
            </q-input>

            <q-input v-model="tenant.email" label="Email address" type="email" outlined dense>
              <template #prepend><q-icon name="mail" size="20px" /></template>
            </q-input>

            <q-input v-model="tenant.id_number" label="SA ID / Passport" outlined dense maxlength="20">
              <template #prepend><q-icon name="badge" size="20px" /></template>
            </q-input>
          </div>
        </div>
      </q-card>

      <!-- ── Lease Terms ──────────────────────────────────────────────────── -->
      <q-card flat class="form-card q-mb-md">
        <div class="form-card-header">
          <q-icon name="description" size="18px" color="primary" />
          <span>Lease Terms</span>
        </div>
        <q-separator />
        <div class="q-pa-md">

          <!-- Date row -->
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-6">
              <q-input v-model="form.start_date" label="Start date *" outlined dense
                hide-bottom-space :rules="[RULES.required]" readonly>
                <template #append>
                  <q-icon name="event" size="20px" class="cursor-pointer">
                    <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                      <q-date v-model="form.start_date" mask="YYYY-MM-DD">
                        <div class="row items-center justify-end">
                          <q-btn v-close-popup label="Done" color="primary" flat />
                        </div>
                      </q-date>
                    </q-popup-proxy>
                  </q-icon>
                </template>
              </q-input>
            </div>
            <div class="col-6">
              <q-input v-model="form.end_date" label="End date *" outlined dense
                hide-bottom-space :rules="[RULES.required]" readonly>
                <template #append>
                  <q-icon name="event" size="20px" class="cursor-pointer">
                    <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                      <q-date v-model="form.end_date" mask="YYYY-MM-DD" :options="afterStartDate">
                        <div class="row items-center justify-end">
                          <q-btn v-close-popup label="Done" color="primary" flat />
                        </div>
                      </q-date>
                    </q-popup-proxy>
                  </q-icon>
                </template>
              </q-input>
            </div>
          </div>

          <div v-if="leaseDuration" class="text-caption text-grey-6 q-mb-md" style="margin-top:-4px">
            <q-icon name="schedule" size="13px" /> {{ leaseDuration }} lease
          </div>

          <!-- Money row -->
          <div class="row q-col-gutter-sm q-mb-sm">
            <div class="col-6">
              <q-input v-model="form.monthly_rent" label="Monthly rent *" type="number" outlined
                dense prefix="R" hide-bottom-space
                :rules="[RULES.positiveNumber]" />
            </div>
            <div class="col-6">
              <q-input v-model="form.deposit" label="Deposit *" type="number" outlined
                dense prefix="R" hide-bottom-space
                :rules="[RULES.positiveNumber]" />
            </div>
          </div>

          <div v-if="form.monthly_rent" class="text-caption text-grey-6 q-mb-md" style="margin-top:-4px">
            <q-icon name="info_outline" size="13px" /> Deposit typically 1–2× rent (R{{ oneMonthRent }}–R{{ twoMonthsRent }})
          </div>

          <q-select v-model="form.rent_due_day" :options="dueDayOptions" label="Rent due day"
            emit-value map-options outlined dense>
            <template #prepend><q-icon name="today" size="20px" /></template>
          </q-select>
        </div>
      </q-card>

      <!-- Error -->
      <q-banner v-if="submitError" rounded class="bg-negative text-white text-caption q-mb-md">
        {{ submitError }}
      </q-banner>

      <!-- Submit -->
      <q-btn
        type="submit"
        color="primary"
        label="Create Lease"
        icon="description"
        unelevated
        no-caps
        :loading="submitting"
        class="full-width submit-btn q-mb-lg"
        size="md"
      />

    </q-form>

  </q-page>

  <q-page v-else class="row justify-center items-center">
    <q-spinner-dots color="primary" :size="SPINNER_SIZE_PAGE" />
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
import { SPINNER_SIZE_PAGE, AVATAR_LIST, RULES, formatZAR } from '../utils/designTokens'

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
    label: `Unit ${u.unit_number} — R${formatZAR(u.rent_amount)}/mo (${u.status})`,
  })),
)

const dueDayOptions = Array.from({ length: 28 }, (_, i) => ({
  label: `${i + 1}${['st','nd','rd'][i] ?? 'th'} of the month`,
  value: i + 1,
}))

const oneMonthRent  = computed(() => formatZAR(form.value.monthly_rent))
const twoMonthsRent = computed(() => formatZAR(Number(form.value.monthly_rent) * 2))

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
  try {
    property.value = await getProperty(props.propertyId)
  } catch {
    $q.notify({ type: 'negative', message: 'Failed to load property details.', icon: 'error' })
    return
  }

  // Pre-select first available unit if only one
  const available = property.value?.units.filter((u) => u.status === 'available') ?? []
  if (available.length === 1) {
    form.value.unit = available[0].id
    onUnitChange(available[0].id)
  }
})
</script>

<style scoped lang="scss">
.form-card {
  border-radius: var(--klikk-radius-card);
  border: 1px solid var(--klikk-border);
  overflow: hidden;
  background: white;
}

.form-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.form-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0;
  font-size: 12px;
  color: #bbb;

  &::before, &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--klikk-border);
  }
}

.tenant-fields {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.submit-btn {
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.02em;
  min-height: 48px;
}
</style>
