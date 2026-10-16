<script setup lang="ts">
import { Search } from 'lucide-vue-next'
import AutoComplete, { type AutoCompleteOptionSelectEvent } from 'primevue/autocomplete'
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

function go(memberId: string) {
  open.value = false
  text.value = ''
  router.push(`/members/${memberId}`)
}

function select(e: AutoCompleteOptionSelectEvent) {
  go((e.value as MemberHit).member_id)
}

function submitTyped() {
  const typed = typeof text.value === 'string' ? text.value.trim().toUpperCase() : ''
  const exact = hits.value.find((h) => h.member_id === typed)
  if (exact) go(exact.member_id)
}

const isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)
const shortcut = isMac ? '⌘ K' : 'Ctrl K'

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
  <button
    type="button"
    class="flex h-10 w-full items-center gap-2.5 rounded-lg border border-ink-200 bg-ink-50 px-3 text-left text-sm text-ink-500 transition hover:border-ink-300 hover:bg-white"
    :aria-keyshortcuts="isMac ? 'Meta+K' : 'Control+K'"
    @click="open = true"
  >
    <Search :size="16" class="shrink-0" aria-hidden="true" />
    <span class="flex-1 truncate">Search members…</span>
    <kbd class="hidden rounded-md border border-ink-200 bg-white px-1.5 py-0.5 font-sans text-[0.6875rem] font-semibold text-ink-500 sm:inline">{{ shortcut }}</kbd>
  </button>
  <Dialog
    v-model:visible="open"
    header="Find a member"
    modal
    dismissable-mask
    position="top"
    :style="{ width: 'min(560px, 92vw)', marginTop: '12vh' }"
  >
    <p class="m-0 mb-3 text-sm text-ink-500">Jump to any member's 360 view by their ID.</p>
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
      :pt="{ pcInputText: { root: { autofocus: true } } }"
      @keydown.enter="submitTyped"
    >
      <template #option="{ option }">
        <div class="grid w-full grid-cols-[4.5rem_1fr_auto] items-center gap-3">
          <strong class="font-semibold tabular-nums">{{ option.member_id }}</strong>
          <span class="truncate text-ink-500">{{ option.segment }}</span>
          <RiskBadge :band="option.risk_band" :prob="option.churn_prob" />
        </div>
      </template>
      <template #empty>{{ failed ? 'Search is unavailable right now.' : 'No members match.' }}</template>
    </AutoComplete>
  </Dialog>
</template>
