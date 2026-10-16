<script setup lang="ts">
import vTooltip from 'primevue/tooltip'

// A readable name with its id as a small secondary chip, e.g. "Free PT session  free_pt_session".
defineProps<{ label: string; code?: string | null; title?: string }>()
</script>

<template>
  <span class="inline-flex flex-wrap items-baseline gap-x-1.5 gap-y-0.5">
    <span>{{ label }}</span>
    <span v-if="code" v-tooltip.top="title" class="id-chip">{{ code }}</span>
  </span>
</template>
