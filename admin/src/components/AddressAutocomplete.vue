<template>
  <div ref="wrapperEl" class="relative address-autocomplete">
    <input
      ref="inputEl"
      :value="displayValue"
      :class="inputClass || 'input'"
      :placeholder="placeholder"
      autocomplete="off"
      @input="onInput"
    />
    <MapPin v-if="showIcon" :size="14" class="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { MapPin } from 'lucide-vue-next'

export interface AddressResult {
  formatted: string
  street: string
  city: string
  province: string
  postal_code: string
  country: string
  lat: number
  lng: number
  place_id: string
}

const props = withDefaults(defineProps<{
  modelValue?: AddressResult | null
  placeholder?: string
  inputClass?: string
  showIcon?: boolean
  country?: string
}>(), {
  modelValue: null,
  placeholder: 'Start typing an address…',
  showIcon: true,
  country: 'za',
})

const emit = defineEmits<{
  'update:modelValue': [value: AddressResult | null]
  select: [value: AddressResult]
  // Raw input string — fires on every keystroke. Parents that need
  // the form to work without Google Places (broken key / blocked CSP /
  // ad-blocker) can listen for this to keep their `address` field in
  // sync as the user types. `select` still only fires on a real
  // place_changed and carries the full structured AddressResult.
  text: [value: string]
}>()

const inputEl = ref<HTMLInputElement | null>(null)
const wrapperEl = ref<HTMLElement | null>(null)
const displayValue = ref(props.modelValue?.formatted ?? '')
let autocompleteEl: any = null

// Sync display from parent
watch(() => props.modelValue, (v) => {
  if (v) displayValue.value = v.formatted
})

function onInput(e: Event) {
  const v = (e.target as HTMLInputElement).value
  displayValue.value = v
  emit('text', v)
}

// Load Google Maps script once
function loadGoogleMaps(): Promise<void> {
  return new Promise((resolve, reject) => {
    if ((window as any).google?.maps?.places) {
      resolve()
      return
    }
    if (document.querySelector('script[data-gm-autocomplete]')) {
      const check = setInterval(() => {
        if ((window as any).google?.maps?.places) {
          clearInterval(check)
          resolve()
        }
      }, 100)
      return
    }
    const key = import.meta.env.VITE_GOOGLE_MAPS_KEY
    if (!key) {
      reject(new Error('VITE_GOOGLE_MAPS_KEY not set'))
      return
    }
    const script = document.createElement('script')
    script.setAttribute('data-gm-autocomplete', '1')
    script.src = `https://maps.googleapis.com/maps/api/js?key=${key}&libraries=places&loading=async`
    script.async = true
    script.onload = () => {
      // Wait for places library to be ready
      const check = setInterval(() => {
        if ((window as any).google?.maps?.places) {
          clearInterval(check)
          resolve()
        }
      }, 50)
    }
    script.onerror = () => reject(new Error('Failed to load Google Maps'))
    document.head.appendChild(script)
  })
}

function parseAddressComponents(place: any): AddressResult {
  const components = place.addressComponents ?? place.address_components ?? []
  const get = (type: string) => {
    for (const c of components) {
      const types = c.types ?? []
      if (types.includes(type)) return c.longText ?? c.long_name ?? ''
    }
    return ''
  }
  const getShort = (type: string) => {
    for (const c of components) {
      const types = c.types ?? []
      if (types.includes(type)) return c.shortText ?? c.short_name ?? ''
    }
    return ''
  }

  const streetNumber = get('street_number')
  const route = get('route')
  const street = [streetNumber, route].filter(Boolean).join(' ')
  const loc = place.location ?? place.geometry?.location

  return {
    formatted: place.formattedAddress ?? place.formatted_address ?? '',
    street,
    city: get('locality') || get('sublocality') || get('administrative_area_level_2'),
    province: get('administrative_area_level_1'),
    postal_code: get('postal_code'),
    country: getShort('country'),
    lat: typeof loc?.lat === 'function' ? loc.lat() : (loc?.lat ?? 0),
    lng: typeof loc?.lng === 'function' ? loc.lng() : (loc?.lng ?? 0),
    place_id: place.id ?? place.place_id ?? '',
  }
}

async function initAutocomplete() {
  try {
    await loadGoogleMaps()
    if (!inputEl.value) return

    const g = (window as any).google

    // Always use legacy Autocomplete — attaches directly to the input element
    const autocomplete = new g.maps.places.Autocomplete(inputEl.value, {
      types: ['address'],
      componentRestrictions: { country: props.country },
      fields: ['address_components', 'formatted_address', 'geometry', 'place_id'],
    })

    autocomplete.addListener('place_changed', () => {
      const place = autocomplete.getPlace()
      if (!place.geometry) return
      const result = parseAddressComponents(place)
      displayValue.value = result.formatted
      emit('update:modelValue', result)
      emit('select', result)
    })

    autocompleteEl = autocomplete
  } catch {
    // Silently degrade — input still works as plain text
  }
}

onMounted(initAutocomplete)

onBeforeUnmount(() => {
  if (autocompleteEl) {
    try {
      const g = (window as any).google
      if (g?.maps?.event?.clearInstanceListeners) {
        g.maps.event.clearInstanceListeners(autocompleteEl)
      }
    } catch { /* ignore */ }
    autocompleteEl = null
  }
})
</script>

<style scoped>
/* Ensure Google's dropdown renders above modals */
.address-autocomplete :deep(.pac-container) {
  z-index: 10000 !important;
}
</style>
