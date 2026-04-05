import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './assets/main.css'
import App from './App.vue'
import router from './router'
import { CSS_CUSTOM_PROPERTIES } from './config/tiptapSettings'

// Inject shared TipTap CSS custom properties on :root
Object.entries(CSS_CUSTOM_PROPERTIES).forEach(([key, value]) => {
  document.documentElement.style.setProperty(key, value)
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
