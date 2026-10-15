<script setup lang="ts">
import AutoComplete, { type AutoCompleteOptionSelectEvent } from 'primevue/autocomplete'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, query } from '../api/client'
import type { MemberHit } from '../api/types'
import RiskBadge from './RiskBadge.vue'

const router = useRouter()
const open = ref(false)
const text = ref('')
const hits = ref<MemberHit[]>([])
const failed = ref(false)

async function complete(e: { query: string }) {
  failed.value = false
  try {
    hits.value = await api<MemberHit[]>(`/members/search${query({ q: e.query, limit: 10 })}`)
  } catch {
    hits.value = []
    failed.value = true
  }
}

function select(e: AutoCompleteOptionSelectEvent) {
  const hit = e.value as MemberHit
  open.value = false
  text.value = ''
  router.push(`/members/${hit.member_id}`)
}

function onKey(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    open.value = true
  }
}

onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Button
    class="search-trigger"
    label="Search members (Ctrl+K)"
    size="small"
    severity="secondary"
    @click="open = true"
  />
  <Dialog v-model:visible="open" header="Find a member" modal :style="{ width: 'min(520px, 92vw)' }">
    <label for="member-search" class="sr-only">Member ID</label>
    <AutoComplete
      v-model="text"
      input-id="member-search"
      :suggestions="hits"
      option-label="member_id"
      placeholder="Type a member ID, e.g. M0042"
      fluid
      auto-option-focus
      :delay="200"
      @complete="complete"
      @option-select="select"
    >
      <template #option="{ option }">
        <div class="hit">
          <strong>{{ option.member_id }}</strong>
          <span>{{ option.segment }}</span>
          <RiskBadge :band="option.risk_band" :prob="option.churn_prob" />
        </div>
      </template>
      <template #empty>{{ failed ? 'Search is unavailable right now.' : 'No members match.' }}</template>
    </AutoComplete>
  </Dialog>
</template>

<style scoped>
.hit {
  display: grid;
  grid-template-columns: 5rem 1fr auto;
  gap: 0.75rem;
  align-items: center;
}
.search-trigger {
  width: 100%;
  justify-content: flex-start;
}
</style>
