<script setup lang="ts">
import { ClipboardList } from 'lucide-vue-next'
import ComingSoon from '../components/ComingSoon.vue'
import PageHeader from '../components/PageHeader.vue'

const FEATURES = [
  'One card per assigned member, with the offer, channel and talking points',
  'Talking points drawn from the churn drivers and the rule trace',
  'Log an outcome in two taps: reached, no answer, accepted, declined or follow-up',
  'An editable message draft, never sent automatically',
]
</script>

<template>
  <div class="page">
    <PageHeader title="My contacts" subtitle="Today's assigned members, in priority order." />
    <ComingSoon
      :icon="ClipboardList"
      title="Your contact list is on its way"
      text="Once a manager approves this week's plan, the members assigned to you appear here, ready for a call or a message."
      :features="FEATURES"
      owner="Stream B · W20–W22"
    />
  </div>
</template>
