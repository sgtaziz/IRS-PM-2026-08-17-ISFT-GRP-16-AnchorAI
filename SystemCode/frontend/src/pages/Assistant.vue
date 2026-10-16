<script setup lang="ts">
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
  <section class="assistant">
    <AssistantChat :member-id="memberId" />
  </section>
</template>

<style scoped>
.assistant {
  display: flex;
  flex-direction: column;
  max-width: 860px;
  height: calc(100vh - 8.5rem);
  min-height: 420px;
  padding: 1rem;
  box-sizing: border-box;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
}
@media (max-width: 960px) {
  .assistant { height: calc(100vh - 10rem); }
}
</style>
