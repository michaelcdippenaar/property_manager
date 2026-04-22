import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './assets/main.css'
import './styles/klikk-components.css'
import App from './App.vue'
import router from './router'
import { CSS_CUSTOM_PROPERTIES } from './config/tiptapSettings'
import { initSentry } from './plugins/sentry'

// Inject shared TipTap CSS custom properties on :root
Object.entries(CSS_CUSTOM_PROPERTIES).forEach(([key, value]) => {
  document.documentElement.style.setProperty(key, value)
})

const app = createApp(App)
app.use(createPinia())
app.use(router)

// Sentry must be initialised after router is registered (needs router ref for tracing)
initSentry(app, router)

app.mount('#app')
