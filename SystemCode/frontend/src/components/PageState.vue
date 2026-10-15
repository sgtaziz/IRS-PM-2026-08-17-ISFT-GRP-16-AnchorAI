<script setup lang="ts">
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'

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
  <div v-if="loading && !error" class="page-state" role="status" aria-live="polite">
    <ProgressSpinner style="width: 2.5rem; height: 2.5rem" stroke-width="5" />
    <span>Loading…</span>
  </div>
  <div v-else-if="error" class="page-state">
    <Message severity="error" :closable="false">{{ error }}</Message>
    <Button label="Try again" size="small" severity="secondary" @click="$emit('retry')" />
  </div>
  <div v-else-if="empty" class="page-state empty">
    <slot name="empty">{{ emptyText }}</slot>
  </div>
  <slot v-else />
</template>

<style scoped>
.page-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 2.5rem 1rem;
  color: var(--muted);
}
.empty {
  border: 1px dashed var(--border);
  border-radius: 8px;
}
</style>
