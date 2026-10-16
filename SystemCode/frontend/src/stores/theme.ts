import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { DARK_CLASS } from '../theme'

export type ThemeMode = 'light' | 'dark' | 'system'

// index.html reads the same key before the app loads, so the first paint already has the right theme.
const KEY = 'anchorai.theme'
const media = window.matchMedia('(prefers-color-scheme: dark)')

function readMode(): ThemeMode {
  try {
    const v = localStorage.getItem(KEY)
    return v === 'light' || v === 'dark' ? v : 'system'
  } catch {
    return 'system'
  }
}

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>(readMode())
  const systemDark = ref(media.matches)
  media.addEventListener('change', (e) => (systemDark.value = e.matches))

  const isDark = computed(() => (mode.value === 'system' ? systemDark.value : mode.value === 'dark'))

  watch(isDark, (dark) => document.documentElement.classList.toggle(DARK_CLASS, dark), { immediate: true })

  function setMode(next: ThemeMode) {
    mode.value = next
    try {
      if (next === 'system') localStorage.removeItem(KEY)
      else localStorage.setItem(KEY, next)
    } catch {
      // Without storage the choice lasts until the page is reloaded.
    }
  }

  return { mode, isDark, setMode }
})
