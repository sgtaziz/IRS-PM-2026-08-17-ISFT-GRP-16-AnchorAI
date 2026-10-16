<script setup lang="ts">
import Card from 'primevue/card'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AssistantChat from '../components/AssistantChat.vue'

const route = useRoute()
const memberId = computed(() => (typeof route.query.member === 'string' ? route.query.member : null))
</script>

<template>
  <div class="page-head">
    <h2>Assistant</h2>
    <span class="sub">Answers only from AnchorAI's data, and says so when it doesn't know</span>
  </div>
  <Card class="assistant">
    <template #content>
      <AssistantChat :member-id="memberId" />
    </template>
  </Card>
</template>

<style scoped>
.assistant { max-width: 860px; }
</style>
