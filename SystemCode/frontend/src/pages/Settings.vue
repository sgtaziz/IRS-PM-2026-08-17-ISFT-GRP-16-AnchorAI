<script setup lang="ts">
import { Settings as SettingsIcon } from 'lucide-vue-next'
import ComingSoon from '../components/ComingSoon.vue'
import PageHeader from '../components/PageHeader.vue'

const FEATURES = [
  'The active LLM endpoint and model, with the key masked, and a connection test',
  'Neo4j knowledge-graph status',
  'Model versions and data freshness',
  'The current database migration revision',
]
</script>

<template>
  <div class="page">
    <PageHeader title="Settings" subtitle="System health and configuration." />
    <ComingSoon
      :icon="SettingsIcon"
      title="Settings and health are on their way"
      text="See at a glance whether the language model, the knowledge graph and the data are healthy and current."
      :features="FEATURES"
      owner="Stream B · W45"
    />
  </div>
</template>
