<script setup lang="ts">
import { RefreshCw, TriangleAlert } from 'lucide-vue-next'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import EmptyState from './EmptyState.vue'

withDefaults(
  defineProps<{
    loading?: boolean
    error?: string | null
    empty?: boolean
    emptyText?: string
  }>(),
  { loading: false, error: null, empty: false, emptyText: 'Nothing to show yet.' },
)
defineEmits<{ retry: [] }>()
</script>

<template>
  <div v-if="loading && !error" class="flex items-center justify-center gap-3 px-4 py-12 text-sm text-ink-500" role="status" aria-live="polite">
    <ProgressSpinner style="width: 1.75rem; height: 1.75rem" stroke-width="5" aria-hidden="true" />
    <span>Loading…</span>
  </div>
  <div v-else-if="error" class="flex flex-col items-center gap-3 px-4 py-10 text-center" role="alert">
    <span class="grid size-11 place-items-center rounded-2xl bg-danger-soft text-danger">
      <TriangleAlert :size="22" aria-hidden="true" />
    </span>
    <p class="m-0 font-semibold text-ink-800">Couldn't load this</p>
    <p class="m-0 max-w-md text-sm text-ink-500">{{ error }}</p>
    <Button label="Try again" size="small" severity="secondary" outlined @click="$emit('retry')">
      <template #icon><RefreshCw :size="14" /></template>
    </Button>
  </div>
  <div v-else-if="empty">
    <slot name="empty"><EmptyState :text="emptyText" compact /></slot>
  </div>
  <slot v-else />
</template>
