<template>
  <q-layout view="hHh lpR fFf">
    <q-header :elevated="!isIos" :class="headerClass">
      <q-toolbar>
        <q-btn flat round :icon="backIcon" :color="isIos ? 'primary' : 'white'" @click="$router.back()" />
        <q-toolbar-title :class="isIos ? 'text-primary text-weight-semibold' : 'text-white text-weight-medium'">
          Report a Repair
        </q-toolbar-title>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <q-page class="page-container">
        <div class="column q-gutter-md">

          <!-- Title -->
          <q-input
            v-model="form.title"
            label="Title"
            outlined
            placeholder="e.g. Leaking tap in bathroom"
          />

          <!-- Category -->
          <q-select
            v-model="form.category"
            label="Category"
            outlined
            :options="categories"
            emit-value
            map-options
          />

          <!-- Priority -->
          <q-select
            v-model="form.priority"
            label="Priority"
            outlined
            :options="priorities"
            emit-value
            map-options
          />

          <!-- Description -->
          <q-input
            v-model="form.description"
            label="Description"
            outlined
            type="textarea"
            rows="4"
            placeholder="Describe the issue in detail…"
          />

          <!-- Error -->
          <div v-if="errorMsg" class="text-negative text-center text-caption">{{ errorMsg }}</div>

          <!-- Submit -->
          <q-btn
            label="Submit Repair Request"
            color="primary"
            size="lg"
            no-caps
            :loading="loading"
            @click="submit"
          />

        </div>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { usePlatform } from '../composables/usePlatform'
import * as tenantApi from '../services/api'

const router = useRouter()
const route  = useRoute()
const $q     = useQuasar()
const { isIos, backIcon, headerClass } = usePlatform()

const form = ref({
  title: '',
  category: '',
  priority: 'medium',
  description: '',
})

const loading  = ref(false)
const errorMsg = ref('')

const categories = [
  'Plumbing', 'Electrical', 'HVAC', 'Appliance',
  'Structural', 'Pest Control', 'Cleaning', 'Other',
]

const priorities = [
  { label: 'Low',    value: 'low' },
  { label: 'Medium', value: 'medium' },
  { label: 'High',   value: 'high' },
  { label: 'Urgent', value: 'urgent' },
]

// Pre-fill from AI chat draft (query params)
onMounted(() => {
  if (route.query.title) form.value.title = route.query.title as string
  if (route.query.description) form.value.description = route.query.description as string
})

async function submit() {
  if (!form.value.title.trim() || !form.value.description.trim()) {
    errorMsg.value = 'Please fill in the title and description.'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await tenantApi.createIssue(form.value)
    $q.notify({ type: 'positive', message: 'Repair request submitted!' })
    router.replace(`/repairs/${res.data.id}`)
  } catch (e: unknown) {
    const axiosErr = e as { response?: { data?: { detail?: string } } }
    errorMsg.value = axiosErr.response?.data?.detail ?? 'Failed to submit. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>
