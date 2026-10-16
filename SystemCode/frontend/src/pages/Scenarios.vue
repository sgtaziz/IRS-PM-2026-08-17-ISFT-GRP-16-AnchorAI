<script setup lang="ts">
import { SlidersHorizontal } from 'lucide-vue-next'
import ComingSoon from '../components/ComingSoon.vue'
import PageHeader from '../components/PageHeader.vue'

const FEATURES = [
  'Budget and staff-hour sliders',
  'Contact-all, risk top-k, greedy uplift, GA and exact solver side by side',
  'Expected members retained, cost and retained per dollar',
  'GA convergence chart, and saving named scenarios',
]
</script>

<template>
  <div class="page">
    <PageHeader title="Scenarios" subtitle="Compare planning strategies under different budgets and staff hours." />
    <ComingSoon
      :icon="SlidersHorizontal"
      title="Scenario comparison is on its way"
      text="Try what-if budgets and see how each strategy would spend them, before committing to a plan."
      :features="FEATURES"
      owner="Stream B · W17"
    />
  </div>
</template>
