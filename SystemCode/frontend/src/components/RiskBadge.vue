<script setup lang="ts">
import { computed } from 'vue'
import type { RiskBand } from '../api/types'
import { probability } from '../format'

const props = defineProps<{ band: RiskBand; prob?: number }>()

const TONES: Record<RiskBand, string> = {
  high: 'bg-danger-soft text-danger-ink ring-danger-line',
  medium: 'bg-warn-soft text-warn-ink ring-warn-line',
  low: 'bg-success-soft text-success-ink ring-success-line',
}
const DOTS: Record<RiskBand, string> = { high: 'bg-risk-high', medium: 'bg-risk-medium', low: 'bg-risk-low' }

const label = computed(() => `${props.band[0].toUpperCase()}${props.band.slice(1)} risk`)
const text = computed(() => (props.prob === undefined ? label.value : `${label.value} · ${probability(props.prob)}`))
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap ring-1 ring-inset"
    :class="TONES[band]"
    :aria-label="text"
  >
    <span class="size-1.5 rounded-full" :class="DOTS[band]" aria-hidden="true" />
    {{ label }}<template v-if="prob !== undefined"><span class="font-medium opacity-80">· {{ probability(prob) }}</span></template>
  </span>
</template>
