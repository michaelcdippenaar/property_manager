<template>
  <!-- POPIA-compliant session recording consent banner.
       Shown only on first visit when VITE_ENABLE_CLARITY=true.
       Dismissed permanently once the user makes a choice (stored in localStorage). -->
  <Transition name="consent-slide">
    <div
      v-if="visible"
      role="dialog"
      aria-live="polite"
      aria-label="Session recording consent"
      class="consent-banner"
    >
      <div class="consent-banner__inner">
        <div class="consent-banner__text">
          <p class="consent-banner__body">
            We record this session to improve Klikk. We capture clicks, mouse
            movement, and screen content — sensitive fields (passwords, ID
            numbers, bank details) are automatically hidden.
            <a
              href="/privacy"
              target="_blank"
              rel="noopener"
              class="consent-banner__link"
            >Privacy policy</a>.
          </p>
        </div>
        <div class="consent-banner__actions">
          <button
            class="consent-banner__btn consent-banner__btn--decline"
            @click="decline"
          >
            No thanks
          </button>
          <button
            class="consent-banner__btn consent-banner__btn--accept"
            @click="accept"
          >
            Allow recording
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useClarity } from '../composables/useClarity'

const { isEnabled, hasClarityDecision, setClarityConsent } = useClarity()

const visible = ref(false)

onMounted(() => {
  // Only show when Clarity is active AND the user has not yet decided
  if (isEnabled && !hasClarityDecision()) {
    visible.value = true
  }
})

function accept() {
  setClarityConsent(true)
  visible.value = false
}

function decline() {
  setClarityConsent(false)
  visible.value = false
}
</script>

<style scoped>
.consent-banner {
  position: fixed;
  bottom: 1.5rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  width: min(calc(100vw - 2rem), 640px);
  background: #ffffff;
  border: 1px solid #e2e5eb;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(43, 45, 110, 0.12);
  padding: 1rem 1.25rem;
}

.consent-banner__inner {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

@media (min-width: 480px) {
  .consent-banner__inner {
    flex-direction: row;
    align-items: center;
    gap: 1.25rem;
  }
}

.consent-banner__text {
  flex: 1;
}

.consent-banner__body {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: #3d3f5a;
}

.consent-banner__link {
  color: #2b2d6e;
  text-decoration: underline;
}

.consent-banner__actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.consent-banner__btn {
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  border: none;
  transition: background 0.15s;
}

.consent-banner__btn--decline {
  background: #f3f4f6;
  color: #6b7280;
}

.consent-banner__btn--decline:hover {
  background: #e5e7eb;
}

.consent-banner__btn--accept {
  background: #2b2d6e;
  color: #ffffff;
}

.consent-banner__btn--accept:hover {
  background: #1e1f50;
}

/* Slide-up transition */
.consent-slide-enter-active,
.consent-slide-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.consent-slide-enter-from,
.consent-slide-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(1rem);
}
</style>
