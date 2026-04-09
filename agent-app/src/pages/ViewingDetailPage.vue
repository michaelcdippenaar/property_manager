<template>
  <q-page class="q-pa-md" v-if="viewing">

    <!-- Status banner -->
    <q-banner
      rounded
      class="q-mb-md status-banner"
      :class="`status-banner--${viewing.status}`"
    >
      <template #avatar>
        <q-icon :name="statusIcon(viewing.status)" />
      </template>
      <span class="text-weight-semibold text-capitalize">{{ viewing.status }}</span>
      <span class="text-caption q-ml-sm">— {{ formatDateTime(viewing.scheduled_at) }}</span>
    </q-banner>

    <!-- Prospect card -->
    <q-card flat class="section-card q-mb-md">
      <q-card-section class="q-pb-xs">
        <div class="row items-center q-gutter-sm">
          <q-avatar color="primary" text-color="white" size="52px">
            <q-icon name="person" size="28px" />
          </q-avatar>
          <div>
            <div class="text-subtitle1 text-weight-bold text-primary">{{ viewing.prospect_name }}</div>
            <div class="text-caption text-grey-6">Prospective tenant</div>
          </div>
        </div>
      </q-card-section>
      <q-separator />
      <q-list dense>
        <q-item v-if="p.phone">
          <q-item-section avatar><q-icon name="phone" color="grey-6" size="20px" /></q-item-section>
          <q-item-section>{{ p.phone }}</q-item-section>
          <q-item-section side><q-btn flat round dense icon="call" color="primary" :href="`tel:${p.phone}`" tag="a" /></q-item-section>
        </q-item>
        <q-item v-if="p.email">
          <q-item-section avatar><q-icon name="mail" color="grey-6" size="20px" /></q-item-section>
          <q-item-section>{{ p.email }}</q-item-section>
        </q-item>
        <q-item v-if="p.id_number">
          <q-item-section avatar><q-icon name="badge" color="grey-6" size="20px" /></q-item-section>
          <q-item-section>{{ p.id_number }}</q-item-section>
        </q-item>
        <q-item v-if="p.employer">
          <q-item-section avatar><q-icon name="business" color="grey-6" size="20px" /></q-item-section>
          <q-item-section>{{ p.employer }}<span v-if="p.occupation"> · {{ p.occupation }}</span></q-item-section>
        </q-item>
        <q-item v-if="p.monthly_income">
          <q-item-section avatar><q-icon name="payments" color="grey-6" size="20px" /></q-item-section>
          <q-item-section>R{{ Number(p.monthly_income).toLocaleString('en-ZA') }} / month</q-item-section>
        </q-item>
        <q-item v-if="p.address">
          <q-item-section avatar><q-icon name="home" color="grey-6" size="20px" /></q-item-section>
          <q-item-section class="text-caption">{{ p.address }}</q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <!-- Viewing details card -->
    <q-card flat class="section-card q-mb-md">
      <q-card-section class="text-subtitle2 text-weight-semibold text-grey-8 q-pb-xs">
        Viewing Details
      </q-card-section>
      <q-separator />
      <q-list dense>
        <q-item>
          <q-item-section avatar><q-icon name="home_work" color="grey-6" size="20px" /></q-item-section>
          <q-item-section>
            <q-item-label>{{ viewing.property_name }}</q-item-label>
            <q-item-label caption v-if="viewing.unit_number">Unit {{ viewing.unit_number }}</q-item-label>
          </q-item-section>
        </q-item>
        <q-item>
          <q-item-section avatar><q-icon name="event" color="grey-6" size="20px" /></q-item-section>
          <q-item-section>{{ formatDateTime(viewing.scheduled_at) }}</q-item-section>
        </q-item>
        <q-item>
          <q-item-section avatar><q-icon name="timer" color="grey-6" size="20px" /></q-item-section>
          <q-item-section>{{ viewing.duration_minutes }} minutes</q-item-section>
        </q-item>
        <q-item v-if="viewing.notes">
          <q-item-section avatar><q-icon name="notes" color="grey-6" size="20px" /></q-item-section>
          <q-item-section class="text-caption">{{ viewing.notes }}</q-item-section>
        </q-item>
        <q-item v-if="viewing.converted_to_lease">
          <q-item-section avatar><q-icon name="description" color="positive" size="20px" /></q-item-section>
          <q-item-section class="text-positive text-weight-medium">Converted to Lease #{{ viewing.converted_to_lease }}</q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <!-- Actions -->
    <div v-if="isActive" class="column q-gutter-sm q-mt-md">

      <!-- Complete -->
      <q-btn
        v-if="viewing.status !== 'completed'"
        unelevated
        :rounded="isIos"
        color="positive"
        label="Mark as Completed"
        icon="check_circle"
        class="full-width"
        :loading="updating"
        @click="markCompleted"
      />

      <!-- Convert to lease -->
      <q-btn
        v-if="viewing.status === 'completed'"
        unelevated
        :rounded="isIos"
        color="secondary"
        label="Convert to Lease"
        icon="description"
        class="full-width"
        @click="goConvert"
      />

      <!-- Cancel -->
      <q-btn
        outline
        :rounded="isIos"
        color="negative"
        label="Cancel Viewing"
        icon="cancel"
        class="full-width"
        :loading="updating"
        @click="confirmCancel"
      />
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
import { getViewing, updateViewing, type PropertyViewing, type Person } from '../services/api'
import { usePlatform } from '../composables/usePlatform'

const props  = defineProps<{ id: number }>()
const router = useRouter()
const $q     = useQuasar()
const { isIos } = usePlatform()

const viewing  = ref<PropertyViewing | null>(null)
const updating = ref(false)

const p = computed<Partial<Person>>(() => viewing.value?.prospect_detail ?? {})

const isActive = computed(() =>
  viewing.value && !['cancelled', 'converted'].includes(viewing.value.status),
)

function statusIcon(status: string) {
  const m: Record<string, string> = {
    scheduled: 'event', confirmed: 'event_available', completed: 'check_circle',
    cancelled: 'cancel', converted: 'description',
  }
  return m[status] || 'info'
}

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString('en-ZA', {
    weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit',
  })
}

async function markCompleted() {
  if (!viewing.value) return
  updating.value = true
  try {
    viewing.value = await updateViewing(viewing.value.id, { status: 'completed' })
    $q.notify({ type: 'positive', message: 'Viewing marked as completed', icon: 'check_circle' })
  } finally {
    updating.value = false
  }
}

function confirmCancel() {
  $q.dialog({
    title: 'Cancel Viewing',
    message: `Cancel viewing with ${viewing.value?.prospect_name}?`,
    cancel: true,
    ok: { label: 'Yes, Cancel', color: 'negative', flat: true },
  }).onOk(async () => {
    updating.value = true
    try {
      viewing.value = await updateViewing(viewing.value!.id, { status: 'cancelled' })
      $q.notify({ type: 'warning', message: 'Viewing cancelled', icon: 'cancel' })
    } finally {
      updating.value = false
    }
  })
}

function goConvert() {
  void router.push(`/viewings/${props.id}/lease`)
}

onMounted(async () => {
  viewing.value = await getViewing(props.id)
})
</script>

<style scoped lang="scss">
.section-card {
  border-radius: 12px;
  border: 1px solid rgba(0,0,0,0.08);
  overflow: hidden;
}

.status-banner {
  &--scheduled  { background: rgba(49,204,236,0.12); color: #1a9fb5; }
  &--confirmed  { background: rgba(43,45,110,0.1);  color: #2B2D6E; }
  &--completed  { background: rgba(33,186,69,0.12); color: #1a8c3d; }
  &--cancelled  { background: rgba(219,40,40,0.1);  color: #b91c1c; }
  &--converted  { background: rgba(255,61,127,0.1); color: #d62d6e; }
}
</style>
