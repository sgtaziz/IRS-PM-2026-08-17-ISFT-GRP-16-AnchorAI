<script setup lang="ts">
defineProps<{ label: string; value: string | number; hint?: string; tone?: 'default' | 'warn' | 'good' }>()
</script>

<template>
  <div class="kpi" :class="tone ?? 'default'">
    <span class="label">{{ label }}</span>
    <strong class="value">{{ value }}</strong>
    <small v-if="hint" class="hint">{{ hint }}</small>
  </div>
</template>

<style scoped>
.kpi {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 1rem 1.1rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 4px solid var(--accent);
  border-radius: 10px;
  min-width: 0;
}
.kpi.warn {
  border-left-color: #c2475b;
}
.kpi.good {
  border-left-color: #3a9d6b;
}
.label {
  font-size: 0.85rem;
  color: var(--muted);
}
.value {
  font-size: 1.6rem;
  line-height: 1.2;
}
.hint {
  color: var(--muted);
}
</style>
