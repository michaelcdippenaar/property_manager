<template>
  <div class="login-page column items-center justify-center q-pa-lg">

    <!-- Logo / branding -->
    <div class="login-logo column items-center q-mb-xl">
      <div class="logo-mark">
        <span>K</span>
      </div>
      <div class="text-h5 text-weight-bold text-primary q-mt-sm">Klikk Agent</div>
      <div class="text-caption text-grey-6">Property Management</div>
    </div>

    <!-- Login form -->
    <q-card class="login-card" flat bordered>
      <q-card-section class="q-pb-none">
        <div class="text-h6 text-weight-semibold text-primary">Sign in</div>
        <div class="text-caption text-grey-6 q-mt-xs">Access your agent dashboard</div>
      </q-card-section>

      <q-card-section>
        <q-form @submit.prevent="handleLogin" class="column q-gutter-md">

          <q-input
            v-model="email"
            label="Email address"
            type="email"
            outlined
            :rounded="isIos"
            autocomplete="username"
            :rules="[val => !!val || 'Email is required', val => /\S+@\S+\.\S+/.test(val) || 'Invalid email']"
          >
            <template #prepend>
              <q-icon name="mail" color="primary" />
            </template>
          </q-input>

          <q-input
            v-model="password"
            label="Password"
            :type="showPassword ? 'text' : 'password'"
            outlined
            :rounded="isIos"
            autocomplete="current-password"
            :rules="[val => !!val || 'Password is required']"
          >
            <template #prepend>
              <q-icon name="lock" color="primary" />
            </template>
            <template #append>
              <q-icon
                :name="showPassword ? 'visibility_off' : 'visibility'"
                class="cursor-pointer"
                color="grey-6"
                @click="showPassword = !showPassword"
              />
            </template>
          </q-input>

          <q-banner v-if="error" rounded class="bg-negative text-white text-caption">
            <template #avatar>
              <q-icon name="error_outline" />
            </template>
            {{ error }}
          </q-banner>

          <q-btn
            type="submit"
            label="Sign In"
            color="primary"
            class="full-width q-py-sm text-weight-semibold"
            :loading="loading"
            :rounded="isIos"
            unelevated
            size="lg"
          />

        </q-form>
      </q-card-section>
    </q-card>

    <div class="text-caption text-grey-5 q-mt-xl">
      Klikk Property Management &copy; {{ new Date().getFullYear() }}
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { usePlatform } from '../composables/usePlatform'

const router = useRouter()
const auth   = useAuthStore()
const { isIos } = usePlatform()

const email        = ref('')
const password     = ref('')
const showPassword = ref(false)
const loading      = ref(false)
const error        = ref('')

async function handleLogin() {
  error.value   = ''
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    await router.replace(auth.homeRoute)
  } catch (err: unknown) {
    const axiosErr = err as { response?: { data?: { detail?: string } } }
    error.value =
      axiosErr.response?.data?.detail ||
      'Invalid credentials. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.login-page {
  min-height: 100vh;
  background: linear-gradient(160deg, #f0f1f9 0%, #fdf0f5 100%);
}

.logo-mark {
  width: 72px;
  height: 72px;
  border-radius: 20px;
  background: #2B2D6E;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(43, 45, 110, 0.3);

  span {
    font-size: 36px;
    font-weight: 800;
    color: white;
    line-height: 1;
  }
}

.login-card {
  width: 100%;
  max-width: 380px;
  border-radius: 16px !important;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08) !important;
  border: 1px solid rgba(0, 0, 0, 0.06) !important;
}
</style>
