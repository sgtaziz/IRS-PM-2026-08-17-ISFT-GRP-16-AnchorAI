<script setup lang="ts">
import { CalendarCheck } from 'lucide-vue-next'
import ComingSoon from '../components/ComingSoon.vue'
import PageHeader from '../components/PageHeader.vue'

const FEATURES = [
  'Set the week, budget, staff hours and solver, then run it as a background job with progress',
  'Results per member: offer, channel, expected value and a one-line reason, with a "why" drawer',
  'Override with a reason while guardrails are re-checked live, then approve and lock the plan',
  'Auto-assign approved calls to staff by hours and skills, and print call sheets',
]
</script>

<template>
  <div class="page">
    <PageHeader title="Weekly plan" subtitle="Build, review and approve this week's retention contacts within budget and staff hours." />
    <ComingSoon
      :icon="CalendarCheck"
      title="The plan builder is on its way"
      text="Generate this week's contact plan with the genetic algorithm or the exact solver, explain every pick, and send approved calls to staff."
      :features="FEATURES"
      owner="Stream B · W14–W16"
    />
  </div>
</template>
