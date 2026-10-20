<script setup lang="ts">
import { Download, GripVertical, Printer, TriangleAlert, UserCog, Users } from 'lucide-vue-next'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import Select from 'primevue/select'
import { computed, onMounted, ref } from 'vue'
import { api, apiText, downloadText } from '../api/client'
import type { AssignmentSummary } from '../api/types'
import { errorMessage } from '../composables/useAsync'
import { channelLabel, humanize } from '../labels'
import { useGlossaryStore } from '../stores/glossary'
import EmptyState from './EmptyState.vue'
import PageState from './PageState.vue'
import SectionCard from './SectionCard.vue'

// Stream B (W16): give an approved plan's contacts to staff by weekly hours and skills.
// The move-to boxes are actions, not state, so they always show their placeholder.
const props = defineProps<{ planId: number }>()
const glossary = useGlossaryStore()
glossary.load()

const summary = ref<AssignmentSummary | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const actionError = ref<string | null>(null)
const assigning = ref(false)

const assigned = computed(() => (summary.value?.staff ?? []).reduce((n, s) => n + s.contacts.length, 0))
const staffOptions = computed(() => (summary.value?.staff ?? []).map((s) => ({ label: s.full_name, value: s.user_id })))

async function load() {
  loading.value = true
  error.value = null
  try {
    summary.value = await api<AssignmentSummary>(`/plan/${props.planId}/assignments`)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}
onMounted(load)

async function autoAssign() {
  assigning.value = true
  actionError.value = null
  try {
    summary.value = await api<AssignmentSummary>(`/plan/${props.planId}/assign`, { method: 'POST' })
  } catch (e) {
    actionError.value = errorMessage(e)
  } finally {
    assigning.value = false
  }
}

async function move(memberId: string, staffUserId: number) {
  actionError.value = null
  try {
    summary.value = await api<AssignmentSummary>(`/plan/${props.planId}/assignments/${memberId}`, {
      method: 'PUT',
      body: JSON.stringify({ staff_user_id: staffUserId }),
    })
  } catch (e) {
    // e.g. the staff member lacks the trainer skill or has no time left
    actionError.value = errorMessage(e)
  }
}

async function callSheet(userId: number, name: string) {
  actionError.value = null
  try {
    const csv = await apiText(`/plan/${props.planId}/call-sheet.csv?staff_id=${userId}`)
    downloadText(`call-sheet-plan${props.planId}-${name.toLowerCase().replace(/\s+/g, '-')}.csv`, csv)
  } catch (e) {
    actionError.value = errorMessage(e)
  }
}

const hours = (minutes: number) => `${(minutes / 60).toFixed(1)} h`

// Drag a contact onto another staff card to reassign it; the move-to boxes do the same from the keyboard.
const dragging = ref<string | null>(null)
const dropTarget = ref<number | null>(null)
function onDrop(staffUserId: number) {
  const member = dragging.value
  dragging.value = dropTarget.value = null
  if (member) move(member, staffUserId)
}

// A clean window with only the call sheet, so "Print → Save as PDF" gives a printable sheet.
async function printSheet(userId: number, name: string) {
  actionError.value = null
  const win = window.open('', '_blank') // opened in the click, so pop-up blockers allow it
  if (!win) {
    actionError.value = 'Your browser blocked the print window. Allow pop-ups for this site and try again.'
    return
  }
  try {
    const rows = await api<{ priority: number; member_id: string; offer: string; channel: string; talking_point: string }[]>(
      `/plan/${props.planId}/call-sheet?staff_id=${userId}`,
    )
    const doc = win.document
    doc.title = `Call sheet · ${name} · plan ${props.planId}`
    const style = doc.createElement('style')
    style.textContent =
      'body{font:13px system-ui,sans-serif;margin:24px;color:#111}h1{font-size:18px;margin:0 0 4px}p{margin:0 0 16px;color:#555}' +
      'table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:6px 8px;text-align:left;vertical-align:top}' +
      'th{background:#f3f4f6}td.note{width:22%}@media print{body{margin:0}}'
    doc.head.appendChild(style)
    const h1 = doc.createElement('h1')
    h1.textContent = `Call sheet · ${name}`
    const sub = doc.createElement('p')
    sub.textContent = `AnchorAI plan #${props.planId} · ${rows.length} contacts, highest priority first. Log each outcome in My contacts.`
    const table = doc.createElement('table')
    const head = table.createTHead().insertRow()
    for (const label of ['#', 'Member', 'Offer', 'Channel', 'Talking point', 'Outcome / note']) {
      const th = doc.createElement('th')
      th.textContent = label
      head.appendChild(th)
    }
    const body = table.createTBody()
    for (const r of rows) {
      const tr = body.insertRow()
      for (const value of [String(r.priority), r.member_id, r.offer, channelLabel(r.channel), r.talking_point]) tr.insertCell().textContent = value
      tr.insertCell().className = 'note'
    }
    doc.body.replaceChildren(h1, sub, table)
    win.focus()
    win.print()
  } catch (e) {
    win.close()
    actionError.value = errorMessage(e)
  }
}
</script>

<template>
  <SectionCard class="mt-6" title="Assign to staff" :icon="UserCog" subtitle="Most valuable contacts first, each to the free staff member with the right skill (PT needs a trainer, calls need the calls skill). Drag a contact onto another card to reassign it.">
    <template #actions>
      <Button :label="assigned ? 'Re-run auto-assign' : 'Auto-assign'" size="small" :loading="assigning" @click="autoAssign">
        <template #icon><Users :size="15" /></template>
      </Button>
    </template>
    <div class="flex flex-col gap-4 px-5 pb-5 pt-3">
      <Message v-if="actionError" severity="error">{{ actionError }}</Message>
      <PageState :loading="loading" :error="error" @retry="load">
        <template v-if="summary">
          <EmptyState v-if="!assigned && !summary.unassigned.length" compact text="Nothing assigned yet. Run auto-assign to share the contacts out." />
          <Message v-if="summary.unassigned.length" severity="warn">
            <span class="flex items-start gap-2">
              <TriangleAlert :size="16" class="mt-0.5 shrink-0" />
              <span>
                {{ summary.unassigned.length }} contact{{ summary.unassigned.length === 1 ? '' : 's' }} could not be assigned: no staff
                member with the right skill has time left this week. Give them to someone below, or remove them from next week's plan.
              </span>
            </span>
          </Message>
          <div v-if="summary.unassigned.length" class="flex flex-wrap gap-2">
            <div
              v-for="m in summary.unassigned"
              :key="m"
              draggable="true"
              class="flex cursor-grab items-center gap-2 rounded-lg border border-ink-200 px-2 py-1"
              @dragstart="dragging = m"
              @dragend="dragging = dropTarget = null"
            >
              <RouterLink :to="`/members/${m}`" class="member-link">{{ m }}</RouterLink>
              <Select :model-value="null" :options="staffOptions" option-label="label" option-value="value" placeholder="Assign to" size="small" @change="move(m, $event.value)" />
            </div>
          </div>

          <div class="grid gap-4 lg:grid-cols-2">
            <section
              v-for="s in summary.staff"
              :key="s.user_id"
              class="flex flex-col gap-3 rounded-card border p-4 transition-colors"
              :class="dropTarget === s.user_id ? 'border-brand-600 bg-brand-50' : 'border-ink-200'"
              :aria-label="`${s.full_name}'s contacts`"
              @dragover.prevent="dropTarget = s.user_id"
              @dragleave="dropTarget = null"
              @drop.prevent="onDrop(s.user_id)"
            >
              <header class="flex items-start justify-between gap-3">
                <div>
                  <h3 class="m-0 text-base font-semibold text-ink-900">{{ s.full_name }}</h3>
                  <p class="m-0 text-xs text-ink-500">{{ s.skills.map(humanize).join(', ') || 'No skills recorded' }}</p>
                </div>
                <div class="flex shrink-0 gap-1">
                  <Button label="Print" size="small" text :disabled="!s.contacts.length" @click="printSheet(s.user_id, s.full_name)">
                    <template #icon><Printer :size="14" /></template>
                  </Button>
                  <Button label="CSV" size="small" text :disabled="!s.contacts.length" @click="callSheet(s.user_id, s.full_name)">
                    <template #icon><Download :size="14" /></template>
                  </Button>
                </div>
              </header>
              <div class="flex flex-col gap-1">
                <span class="text-sm text-ink-600">{{ s.contacts.length }} contacts · {{ hours(s.minutes_used) }} of {{ hours(s.minutes_capacity) }}</span>
                <ProgressBar
                  :value="s.minutes_capacity ? Math.round((100 * s.minutes_used) / s.minutes_capacity) : 0"
                  :show-value="false"
                  style="height: 0.4rem"
                />
              </div>
              <ol v-if="s.contacts.length" class="m-0 flex max-h-72 flex-col gap-1 overflow-auto pl-6 text-sm">
                <li v-for="c in s.contacts" :key="c.member_id" draggable="true" class="cursor-grab" @dragstart="dragging = c.member_id" @dragend="dragging = dropTarget = null">
                  <div class="flex items-center justify-between gap-2">
                    <span>
                      <GripVertical :size="13" class="mr-0.5 inline align-[-2px] text-ink-400" aria-hidden="true" />
                      <RouterLink :to="`/members/${c.member_id}`" class="member-link">{{ c.member_id }}</RouterLink>
                      <span class="text-ink-600"> · {{ glossary.offer(c.offer_id) }} · {{ channelLabel(c.channel) }}</span>
                    </span>
                    <Select
                      :model-value="null"
                      :options="staffOptions.filter((o) => o.value !== s.user_id)"
                      option-label="label"
                      option-value="value"
                      placeholder="Move to"
                      size="small"
                      class="shrink-0"
                      @change="move(c.member_id, $event.value)"
                    />
                  </div>
                </li>
              </ol>
            </section>
          </div>
        </template>
      </PageState>
    </div>
  </SectionCard>
</template>
