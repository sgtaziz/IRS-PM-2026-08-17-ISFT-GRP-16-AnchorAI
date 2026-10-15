<script setup lang="ts">
import Tag from 'primevue/tag'
import { computed } from 'vue'
import type { RiskBand } from '../api/types'

const props = defineProps<{ band: RiskBand; prob?: number }>()

const severity = computed(() => ({ high: 'danger', medium: 'warn', low: 'success' })[props.band])
const text = computed(() => {
  const label = `${props.band[0].toUpperCase()}${props.band.slice(1)} risk`
  return props.prob === undefined ? label : `${label} · ${Math.round(props.prob * 100)}%`
})
</script>

<template>
  <Tag :severity="severity" :value="text" :aria-label="text" />
</template>
