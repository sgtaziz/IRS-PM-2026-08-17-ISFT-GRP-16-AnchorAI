<script setup lang="ts">
import { Check, Monitor, Moon, Sun } from 'lucide-vue-next'
import Menu from 'primevue/menu'
import vTooltip from 'primevue/tooltip'
import { computed, ref } from 'vue'
import { useThemeStore, type ThemeMode } from '../stores/theme'

const store = useThemeStore()
const menu = ref<InstanceType<typeof Menu> | null>(null)
const open = ref(false)

const OPTIONS: { mode: ThemeMode; label: string; glyph: typeof Sun }[] = [
  { mode: 'light', label: 'Light', glyph: Sun },
  { mode: 'dark', label: 'Dark', glyph: Moon },
  { mode: 'system', label: 'System', glyph: Monitor },
]
const items = computed(() => OPTIONS.map((o) => ({ ...o, command: () => store.setMode(o.mode) })))
const current = computed(() => OPTIONS.find((o) => o.mode === store.mode) ?? OPTIONS[2])
</script>

<template>
  <button
    v-tooltip.bottom="'Theme'"
    type="button"
    class="grid size-9 place-items-center rounded-lg border-0 bg-transparent text-ink-500 transition hover:bg-ink-100 hover:text-ink-800"
    :aria-label="`Theme: ${current.label}`"
    aria-haspopup="menu"
    :aria-expanded="open"
    :aria-controls="open ? 'theme-menu' : undefined"
    @click="menu?.toggle($event)"
  >
    <component :is="store.isDark ? Moon : Sun" :size="18" aria-hidden="true" />
  </button>
  <Menu id="theme-menu" ref="menu" :model="items" popup class="min-w-40" @show="open = true" @hide="open = false">
    <template #item="{ item, props }">
      <a v-bind="props.action" class="flex items-center gap-2.5">
        <component :is="item.glyph" :size="15" class="text-ink-500" aria-hidden="true" />
        <span class="flex-1">{{ item.label }}<span v-if="item.mode === store.mode" class="sr-only"> (selected)</span></span>
        <Check v-if="item.mode === store.mode" :size="15" class="text-brand-600" aria-hidden="true" />
      </a>
    </template>
  </Menu>
</template>
