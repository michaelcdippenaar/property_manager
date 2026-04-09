<template>
  <q-page class="q-pa-md">
    <q-pull-to-refresh @refresh="loadProperties">

      <div v-if="loading" class="row justify-center q-py-xl">
        <q-spinner-dots color="primary" size="40px" />
      </div>

      <template v-else-if="properties.length === 0">
        <div class="text-center q-py-xl">
          <q-icon name="home_work" size="64px" color="grey-4" />
          <div class="text-body2 text-grey-5 q-mt-sm">No properties yet</div>
        </div>
      </template>

      <template v-else>
        <!-- Search -->
        <q-input
          v-model="search"
          placeholder="Search properties..."
          outlined
          :rounded="isIos"
          dense
          clearable
          class="q-mb-md"
        >
          <template #prepend>
            <q-icon name="search" color="grey-6" />
          </template>
        </q-input>

        <!-- Property cards -->
        <div class="column q-gutter-sm">
          <q-card
            v-for="prop in filteredProperties"
            :key="prop.id"
            flat
            class="property-card"
            clickable
            v-ripple
            @click="$router.push(`/properties/${prop.id}`)"
          >
            <!-- Cover photo -->
            <q-img
              v-if="prop.cover_photo"
              :src="prop.cover_photo"
              fit="cover"
              class="property-photo"
            />

            <div v-else class="property-placeholder row items-center justify-center">
              <q-icon name="home" size="48px" color="grey-4" />
            </div>

            <q-card-section class="q-pt-md q-pb-md">
              <div class="row items-start justify-between no-wrap">
                <div class="col">
                  <div class="text-subtitle1 text-weight-semibold text-primary ellipsis">{{ prop.name }}</div>
                  <div class="text-caption text-grey-6 ellipsis">{{ prop.address }}</div>
                </div>
                <q-icon name="chevron_right" color="grey-4" class="q-ml-sm" />
              </div>

              <!-- Unit summary badges -->
              <div class="row q-gutter-xs q-mt-sm">
                <q-badge outline color="primary" :label="`${prop.unit_count} unit${prop.unit_count !== 1 ? 's' : ''}`" />
                <q-badge
                  outline
                  color="positive"
                  :label="`${availableUnits(prop)} available`"
                />
              </div>
            </q-card-section>
          </q-card>
        </div>
      </template>

    </q-pull-to-refresh>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { listProperties, type Property } from '../services/api'
import { usePlatform } from '../composables/usePlatform'

const { isIos } = usePlatform()

const loading    = ref(true)
const properties = ref<Property[]>([])
const search     = ref('')

const filteredProperties = computed(() => {
  if (!search.value) return properties.value
  const q = search.value.toLowerCase()
  return properties.value.filter(
    (p) => p.name.toLowerCase().includes(q) || p.city.toLowerCase().includes(q),
  )
})

function availableUnits(prop: Property) {
  return prop.units?.filter((u) => u.status === 'available').length ?? 0
}

async function loadProperties(done?: () => void) {
  try {
    const resp = await listProperties()
    properties.value = resp.results
  } finally {
    loading.value = false
    done?.()
  }
}

onMounted(() => void loadProperties())
</script>

<style scoped lang="scss">
.property-card {
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  overflow: hidden;
  cursor: pointer;
}

.property-photo {
  display: block;
  width: 100%;
  height: 180px;
}

.property-placeholder {
  display: block;
  width: 100%;
  height: 120px;
  background: #f5f5f8;
}
</style>
