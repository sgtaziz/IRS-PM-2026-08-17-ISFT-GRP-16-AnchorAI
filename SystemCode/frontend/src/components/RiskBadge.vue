<script setup lang="ts">
import Tag from 'primevue/tag'
import { computed } from 'vue'
import type { RiskBand } from '../api/types'
import { probability } from '../format'

const props = defineProps<{ band: RiskBand; prob?: number }>()

const severity = computed(() => ({ high: 'danger', medium: 'warn', low: 'success' })[props.band])
const text = computed(() => {
  const label = `${props.band[0].toUpperCase()}${props.band.slice(1)} risk`
  return props.prob === undefined ? label : `${label} · ${probability(props.prob)}`
})
</script>

<template>
  <Tag :severity="severity" :value="text" :aria-label="text" />
</template>
