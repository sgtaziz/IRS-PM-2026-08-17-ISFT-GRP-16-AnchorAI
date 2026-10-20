<script setup lang="ts">
import { Check, ClipboardList, MessageSquareText, Network, Scale, StickyNote } from 'lucide-vue-next'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import ProgressBar from 'primevue/progressbar'
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { MyContact, OutcomeCode } from '../api/types'
import EmptyState from '../components/EmptyState.vue'
import MessageDraftDialog from '../components/MessageDraftDialog.vue'
import PageHeader from '../components/PageHeader.vue'
import PageState from '../components/PageState.vue'
import { errorMessage, useAsync } from '../composables/useAsync'
import { date } from '../format'
import { channelLabel } from '../labels'
import { useGlossaryStore } from '../stores/glossary'

// W20 + W21: the signed-in user's contacts in the latest approved plan, and one-tap outcome logging.
const OUTCOMES: { code: OutcomeCode; label: string; severity: 'success' | 'danger' | 'secondary' | 'warn' | 'info' }[] = [
  { code: 'accepted', label: 'Accepted', severity: 'success' },
  { code: 'declined', label: 'Declined', severity: 'danger' },
  { code: 'reached', label: 'Reached', severity: 'info' },
  { code: 'follow_up', label: 'Follow-up', severity: 'warn' },
  { code: 'no_answer', label: 'No answer', severity: 'secondary' },
]
const label = (code: OutcomeCode | null) => OUTCOMES.find((o) => o.code === code)?.label ?? ''

const list = useAsync(() => api<MyContact[]>('/assignments/mine'))
// A deep ref, so logging an outcome on a card re-renders it.
const contacts = ref<MyContact[]>([])
// C's message-draft dialog names offers through the shared glossary.
const glossary = useGlossaryStore()
onMounted(glossary.load)

async function load() {
  contacts.value = (await list.run()) ?? []
}
onMounted(load)
const logged = computed(() => contacts.value.filter((c) => c.outcome).length)

const saving = ref<number | null>(null)
const errors = ref<Record<number, string>>({})
const notes = ref<Record<number, string>>({})
const noteOpen = ref<Record<number, boolean>>({})

async function log(c: MyContact, outcome: OutcomeCode) {
  saving.value = c.plan_item_id
  delete errors.value[c.plan_item_id]
  const note = (notes.value[c.plan_item_id] ?? c.note ?? '').trim() || null
  try {
    await api('/outcomes', { method: 'POST', body: JSON.stringify({ plan_item_id: c.plan_item_id, outcome, note }) })
    c.outcome = outcome
    c.note = note
    noteOpen.value[c.plan_item_id] = false
  } catch (e) {
    errors.value[c.plan_item_id] = errorMessage(e)
  } finally {
    saving.value = null
  }
}

const drafting = ref<MyContact | null>(null)
const draftOpen = computed({
  get: () => drafting.value !== null,
  set: (open) => {
    if (!open) drafting.value = null
  },
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="My contacts"
      :subtitle="contacts.length ? `Week of ${date(contacts[0].week_start)} · highest priority first` : 'Your assigned members, highest priority first.'"
    />
    <PageState :loading="list.loading.value" :error="list.error.value" :empty="!contacts.length" @retry="load">
      <template #empty>
        <EmptyState :icon="ClipboardList" title="No contacts for you yet" text="Once a manager approves this week's plan and assigns it, your members appear here." />
      </template>

      <div class="mb-5 flex flex-col gap-1.5">
        <span class="text-sm text-ink-600">{{ logged }} of {{ contacts.length }} logged</span>
        <ProgressBar :value="Math.round((100 * logged) / contacts.length)" :show-value="false" style="height: 0.5rem" />
      </div>

      <ol class="m-0 grid list-none gap-4 p-0 md:grid-cols-2">
        <li
          v-for="c in contacts"
          :key="c.plan_item_id"
          class="flex flex-col gap-3 rounded-card border bg-card p-4 shadow-card"
          :class="c.outcome ? 'border-ink-200 opacity-80' : 'border-ink-200'"
        >
          <header class="flex items-start justify-between gap-3">
            <div class="flex items-center gap-3">
              <span class="grid size-8 shrink-0 place-items-center rounded-full bg-brand-50 text-sm font-semibold text-brand-700">{{ c.priority }}</span>
              <div>
                <RouterLink :to="`/members/${c.member_id}`" class="member-link text-base font-semibold">{{ c.member_id }}</RouterLink>
                <p class="m-0 text-sm text-ink-700">{{ c.offer_name }} · {{ channelLabel(c.channel) }}</p>
              </div>
            </div>
            <span v-if="c.outcome" class="flex items-center gap-1 rounded-full bg-success-soft px-2 py-0.5 text-xs font-medium text-success-ink">
              <Check :size="12" /> {{ label(c.outcome) }}
            </span>
          </header>

          <p class="m-0 text-sm leading-relaxed text-ink-700">{{ c.summary }}</p>
          <div v-if="c.drivers.length" class="flex flex-wrap gap-1.5">
            <span v-for="d in c.drivers" :key="d" class="rounded-full bg-ink-100 px-2 py-0.5 text-xs text-ink-700">{{ d }}</span>
          </div>
          <p v-if="c.rule" class="m-0 flex items-start gap-1.5 text-xs text-ink-500"><Scale :size="13" class="mt-0.5 shrink-0" /> {{ c.rule }}</p>
          <p v-for="s in c.graph_signals" :key="s" class="m-0 flex items-start gap-1.5 text-xs text-ink-500">
            <Network :size="13" class="mt-0.5 shrink-0" /> {{ s }}
          </p>

          <div class="flex flex-wrap gap-2" role="group" :aria-label="`Outcome for ${c.member_id}`">
            <Button
              v-for="o in OUTCOMES"
              :key="o.code"
              :label="o.label"
              size="small"
              :severity="o.severity"
              :outlined="c.outcome !== o.code"
              :disabled="saving === c.plan_item_id"
              @click="log(c, o.code)"
            />
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <Button label="Draft message" size="small" text @click="drafting = c">
              <template #icon><MessageSquareText :size="14" /></template>
            </Button>
            <Button :label="c.note ? 'Edit note' : 'Add note'" size="small" text severity="secondary" @click="noteOpen[c.plan_item_id] = !noteOpen[c.plan_item_id]">
              <template #icon><StickyNote :size="14" /></template>
            </Button>
            <span v-if="c.note && !noteOpen[c.plan_item_id]" class="text-xs text-ink-500">“{{ c.note }}”</span>
          </div>
          <InputText
            v-if="noteOpen[c.plan_item_id]"
            :model-value="notes[c.plan_item_id] ?? c.note ?? ''"
            placeholder="Optional note, saved with the next outcome you tap"
            maxlength="500"
            size="small"
            fluid
            @update:model-value="notes[c.plan_item_id] = $event ?? ''"
          />
          <p v-if="errors[c.plan_item_id]" class="m-0 text-sm text-danger">{{ errors[c.plan_item_id] }}</p>
        </li>
      </ol>
    </PageState>

    <MessageDraftDialog
      v-if="drafting"
      v-model:visible="draftOpen"
      :member-id="drafting.member_id"
      :offer-id="drafting.offer_id"
      :channel="drafting.channel"
    />
  </div>
</template>
