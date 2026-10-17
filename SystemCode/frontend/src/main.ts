import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import { createApp } from 'vue'
import { START_LOCATION } from 'vue-router'
import App from './App.vue'
import { ApiError, setForbiddenHandler, setUnauthorizedHandler, TOKEN_KEY } from './api/client'
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

function toLogin() {
  const current = router.currentRoute.value
  // During the first navigation the route guard does the redirect, keeping the deep link.
  if (current === START_LOCATION || current.meta.public) return
  router.push({ name: 'Login', query: { redirect: current.fullPath } })
}

setUnauthorizedHandler(() => {
  useAuthStore().logout()
  toLogin()
})

setForbiddenHandler(async () => {
  const auth = useAuthStore()
  if (!auth.user) return
  try {
    await auth.fetchMe()
  } catch {
    return
  }
  const roles = router.currentRoute.value.meta.roles
  if (roles && !auth.hasRole(roles)) router.replace(auth.homeRoute)
})

// Another tab logged in, out or as someone else (a cleared storage fires with a null key).
window.addEventListener('storage', async (e) => {
  if (e.key !== null && e.key !== TOKEN_KEY) return
  const auth = useAuthStore()
  const before = auth.user?.username
  try {
    await auth.syncToken()
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return
  }
  if (!auth.isAuthenticated) toLogin()
  else if (auth.user?.username !== before) router.replace(auth.homeRoute)
})

app.mount('#app')
