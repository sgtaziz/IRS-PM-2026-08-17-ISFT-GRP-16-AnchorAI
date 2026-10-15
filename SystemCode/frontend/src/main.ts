import Aura from '@primeuix/themes/aura'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import { createApp } from 'vue'
import { START_LOCATION } from 'vue-router'
import App from './App.vue'
import { setUnauthorizedHandler } from './api/client'
import { router } from './router'
import { useAuthStore } from './stores/auth'
import './style.css'

const app = createApp(App).use(createPinia()).use(router).use(PrimeVue, { theme: { preset: Aura } })

setUnauthorizedHandler(() => {
  useAuthStore().logout()
  const current = router.currentRoute.value
  // During the first navigation the route guard does the redirect, keeping the deep link.
  if (current === START_LOCATION || current.meta.public) return
  router.push({ name: 'Login', query: { redirect: current.fullPath } })
})

app.mount('#app')
