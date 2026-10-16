import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import { createApp } from 'vue'
import { START_LOCATION } from 'vue-router'
import App from './App.vue'
import { setUnauthorizedHandler } from './api/client'
import { router } from './router'
import { useAuthStore } from './stores/auth'
import { useThemeStore } from './stores/theme'
import './style.css'
import { AnchorPreset, DARK_CLASS } from './theme'

const app = createApp(App)
  .use(createPinia())
  .use(router)
  .use(PrimeVue, {
    theme: {
      preset: AnchorPreset,
      options: { darkModeSelector: `.${DARK_CLASS}`, cssLayer: { name: 'primevue', order: 'theme, base, primevue, components, utilities' } },
    },
  })
  .use(ToastService)
  .use(ConfirmationService)

useThemeStore()

setUnauthorizedHandler(() => {
  useAuthStore().logout()
  const current = router.currentRoute.value
  // During the first navigation the route guard does the redirect, keeping the deep link.
  if (current === START_LOCATION || current.meta.public) return
  router.push({ name: 'Login', query: { redirect: current.fullPath } })
})

app.mount('#app')
