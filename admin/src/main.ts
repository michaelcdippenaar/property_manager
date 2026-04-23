import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './assets/main.css'
import './styles/klikk-components.css'
import App from './App.vue'
import router from './router'
import { CSS_CUSTOM_PROPERTIES } from './config/tiptapSettings'
import { initSentry } from './plugins/sentry'
import { initPlausible, setupPlausibleRouterHook } from './plugins/plausible'

// Inject shared TipTap CSS custom properties on :root
Object.entries(CSS_CUSTOM_PROPERTIES).forEach(([key, value]) => {
  document.documentElement.style.setProperty(key, value)
})

// Plausible: inject script + stub queue early so events buffered during
// app boot are not lost. Must run before app.mount() so that conversion
// events fired in component setup() are queued correctly.
initPlausible()

const app = createApp(App)
app.use(createPinia())
app.use(router)

// Sentry must be initialised after router is registered (needs router ref for tracing)
initSentry(app, router)

// Plausible: wire router hook so each SPA navigation fires a pageview.
// Must run after app.use(router) so router is fully configured.
setupPlausibleRouterHook(router)

app.mount('#app')
