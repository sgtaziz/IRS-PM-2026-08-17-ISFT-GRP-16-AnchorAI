<script setup lang="ts">
import { ArrowRight, CalendarX2, Database, GraduationCap, Plus, RefreshCw, UserMinus, UserPlus, Users } from 'lucide-vue-next'
import Button from 'primevue/button'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { EventType, KgStatus, Roster, RosterClass, RosterEdit, RosterInstructor } from '../api/types'
import { errorMessage, useAsync } from '../composables/useAsync'
import { date, dateTime } from '../format'
import ConfirmAction from '../components/ConfirmAction.vue'
import DataTableX from '../components/DataTableX.vue'
import PageHeader from '../components/PageHeader.vue'
import PageState from '../components/PageState.vue'
import SectionCard from '../components/SectionCard.vue'

const toast = useToast()
const roster = useAsync(() => api<Roster>('/admin/gym'))
const kg = useAsync(() => api<KgStatus>('/admin/kg/status'))
onMounted(() => {
  roster.run()
  kg.run()
})

const tab = ref('instructors')
const reloading = ref(false)

const SOURCE_STYLE = { generated: 'bg-ink-100 text-ink-600', added: 'bg-brand-50 text-brand-700' }
const sourceLabel = (s: string) => (s === 'added' ? 'Added here' : 'Generated')

const instructorName = computed(() => new Map((roster.data.value?.instructors ?? []).map((i) => [i.id, i.name])))
const clubOptions = computed(() => (roster.data.value?.clubs ?? []).map((c) => ({ value: c, label: `Club ${c}` })))

function instructorOptions(club: string, except?: string) {
  return (roster.data.value?.instructors ?? [])
    .filter((i) => i.club_id === club && i.status === 'active' && i.id !== except)
    .map((i) => ({ value: i.id, label: i.name }))
}

async function changed(edit: RosterEdit, summary: string) {
  if (edit.kg.stale) {
    toast.add({ severity: 'warn', summary: `${summary}, but the knowledge graph is not updated`, detail: `${edit.kg.error}. Reload it once Neo4j is back.`, life: 7000 })
  } else {
    toast.add({ severity: 'success', summary, life: 3000 })
  }
  await Promise.all([roster.run(), kg.run()])
}

async function reloadGraph() {
  reloading.value = true
  try {
    await api<KgStatus>('/admin/kg/reload', { method: 'POST' })
    toast.add({ severity: 'success', summary: 'Knowledge graph reloaded', life: 3000 })
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Could not reload the knowledge graph', detail: errorMessage(e), life: 7000 })
  } finally {
    reloading.value = false
    kg.run()
  }
}

async function revoke(eventId: string, summary: string) {
  try {
    await changed(await api<RosterEdit>(`/admin/gym/events/${eventId}`, { method: 'DELETE' }), summary)
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Could not save the change', detail: errorMessage(e), life: 6000 })
  }
}

type Mode =
  | { kind: 'instructor' }
  | { kind: 'class' }
  | { kind: 'reassign'; target: RosterClass }
  | { kind: 'event'; type: EventType; id: string; name: string }
const mode = ref<Mode | null>(null)
const form = ref({ name: '', club_id: '', instructor_id: '', week_start: '', note: '' })
const formError = ref<string | null>(null)
const busy = ref(false)

function monday() {
  const d = new Date()
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7))
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function open(m: Mode) {
  mode.value = m
  formError.value = null
  const club = roster.data.value?.clubs[0] ?? ''
  form.value = { name: '', club_id: m.kind === 'reassign' ? m.target.club_id : club, instructor_id: '', week_start: monday(), note: '' }
}

const eventOf = (i: RosterInstructor) => (i.status === 'left' ? i.event : null)

async function submit() {
  const m = mode.value
  const f = form.value
  if (!m) return
  if ((m.kind === 'instructor' || m.kind === 'class') && !f.name.trim()) return (formError.value = 'Enter a name.')
  if ((m.kind === 'class' || m.kind === 'reassign') && !f.instructor_id) return (formError.value = 'Pick an instructor.')
  busy.value = true
  const json = (body: object, method = 'POST') => ({ method, body: JSON.stringify(body) })
  try {
    if (m.kind === 'instructor') {
      await changed(await api<RosterEdit>('/admin/gym/instructors', json({ name: f.name, club_id: f.club_id })), `Added ${f.name.trim()}`)
    } else if (m.kind === 'class') {
      await changed(await api<RosterEdit>('/admin/gym/classes', json({ name: f.name, club_id: f.club_id, instructor_id: f.instructor_id })), `Added ${f.name.trim()}`)
    } else if (m.kind === 'reassign') {
      const to = instructorName.value.get(f.instructor_id) ?? f.instructor_id
      await changed(await api<RosterEdit>(`/admin/gym/classes/${m.target.id}/instructor`, json({ instructor_id: f.instructor_id }, 'PUT')), `${m.target.name} now taught by ${to}`)
    } else {
      const body = { event_type: m.type, entity_id: m.id, week_start: f.week_start || null, note: f.note }
      await changed(await api<RosterEdit>('/admin/gym/events', json(body)), m.type === 'instructor_left' ? `${m.name} marked as left` : `${m.name} cancelled`)
    }
    mode.value = null
  } catch (e) {
    formError.value = errorMessage(e)
    // The edit may have landed before the error; show the real state before anyone retries.
    roster.run()
  } finally {
    busy.value = false
  }
}

const dialogTitle = computed(() => {
  const m = mode.value
  if (!m) return ''
  if (m.kind === 'instructor') return 'Add an instructor'
  if (m.kind === 'class') return 'Add a class'
  if (m.kind === 'reassign') return `Change instructor for ${m.target.name}`
  return m.type === 'instructor_left' ? `Mark ${m.name} as left` : `Cancel ${m.name}`
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="Events & roster"
      subtitle="Record who has left and which classes are cancelled. The knowledge graph is rebuilt after each change."
    >
      <template #actions>
        <RouterLink to="/graph" class="inline-flex items-center gap-1.5 text-sm font-semibold no-underline">
          See who an event affects <ArrowRight :size="15" aria-hidden="true" />
        </RouterLink>
      </template>
    </PageHeader>
    <SectionCard title="Instructors and classes" subtitle="Add people and classes, reassign teaching, or record an event" :icon="CalendarX2">
    <div class="mb-4 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
      <span class="text-xs text-ink-500">
        {{ kg.data.value?.last_reloaded_at ? `Graph reloaded ${dateTime(kg.data.value.last_reloaded_at)}` : 'Graph not reloaded since the server started' }}
      </span>
      <Button label="Reload knowledge graph" size="small" severity="secondary" outlined :loading="reloading" @click="reloadGraph">
        <template #icon><RefreshCw :size="14" /></template>
      </Button>
    </div>
    <Message v-if="kg.data.value?.stale" severity="warn" :closable="false" class="mb-4">
      Edits are saved, but the knowledge graph has not been rebuilt from them ({{ kg.data.value.error }}). Reload it once Neo4j is running.
    </Message>
    <Message severity="secondary" :closable="false" class="mb-4">
      Churn scores do not change when an event is recorded; events feed the graph signals and rules only. Added classes have no attendance until the data is rebuilt.
    </Message>
    <PageState :loading="roster.loading.value && !roster.data.value" :error="roster.error.value" @retry="roster.run">
      <Tabs v-if="roster.data.value" v-model:value="tab">
        <TabList>
          <Tab value="instructors"><span class="tab-label"><Users :size="15" aria-hidden="true" />Instructors ({{ roster.data.value.instructors.length }})</span></Tab>
          <Tab value="classes"><span class="tab-label"><GraduationCap :size="15" aria-hidden="true" />Classes ({{ roster.data.value.classes.length }})</span></Tab>
        </TabList>
        <TabPanels>
          <TabPanel value="instructors">
            <DataTableX :value="roster.data.value.instructors" :rows="10" :global-filter-fields="['name', 'id', 'club_id']" export-name="instructors">
              <template #toolbar>
                <Button label="Add instructor" size="small" @click="open({ kind: 'instructor' })">
                  <template #icon><UserPlus :size="15" /></template>
                </Button>
              </template>
              <Column field="name" header="Instructor" sortable>
                <template #body="{ data }">
                  <span class="font-semibold text-ink-800">{{ data.name }}</span> <span class="id-chip ml-1">{{ data.id }}</span>
                </template>
              </Column>
              <Column field="club_id" header="Club" sortable>
                <template #body="{ data }">Club {{ data.club_id }}</template>
              </Column>
              <Column field="classes" header="Classes" sortable />
              <Column field="status" header="Status" sortable>
                <template #body="{ data }">
                  <span class="rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="data.status === 'left' ? 'bg-warn-soft text-warn-ink' : 'bg-success-soft text-success-ink'">
                    {{ data.status === 'left' ? `Left ${date(eventOf(data)?.week_start)}` : 'Active' }}
                  </span>
                </template>
              </Column>
              <Column field="source" header="Source" sortable>
                <template #body="{ data }">
                  <span class="rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="SOURCE_STYLE[data.source as 'added']">{{ sourceLabel(data.source) }}</span>
                </template>
              </Column>
              <Column header="Actions">
                <template #body="{ data }">
                  <ConfirmAction
                    v-if="data.event"
                    label="Reinstate"
                    header="Reinstate instructor"
                    severity="secondary"
                    :message="`Mark ${data.name} as back? Their classes count as taught again once the graph is rebuilt.`"
                    @confirm="revoke(data.event.event_id, `${data.name} reinstated`)"
                  />
                  <Button v-else label="Mark as left" size="small" severity="danger" text @click="open({ kind: 'event', type: 'instructor_left', id: data.id, name: data.name })">
                    <template #icon><UserMinus :size="14" /></template>
                  </Button>
                </template>
              </Column>
            </DataTableX>
          </TabPanel>
          <TabPanel value="classes">
            <DataTableX :value="roster.data.value.classes" :rows="10" :global-filter-fields="['name', 'id', 'club_id', 'instructor_name']" export-name="classes">
              <template #toolbar>
                <Button label="Add class" size="small" @click="open({ kind: 'class' })">
                  <template #icon><Plus :size="15" /></template>
                </Button>
              </template>
              <Column field="name" header="Class" sortable>
                <template #body="{ data }">
                  <span class="font-semibold text-ink-800">{{ data.name }}</span> <span class="id-chip ml-1">{{ data.id }}</span>
                </template>
              </Column>
              <Column field="club_id" header="Club" sortable>
                <template #body="{ data }">Club {{ data.club_id }}</template>
              </Column>
              <Column field="instructor_name" header="Instructor" sortable>
                <template #body="{ data }">
                  {{ data.instructor_name }}
                  <span v-if="roster.data.value.instructors.find((i: RosterInstructor) => i.id === data.instructor_id)?.status === 'left'" class="ml-1 text-xs font-semibold text-warn-ink">(left)</span>
                </template>
              </Column>
              <Column field="status" header="Status" sortable>
                <template #body="{ data }">
                  <span class="rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="data.status === 'cancelled' ? 'bg-danger-soft text-danger' : 'bg-success-soft text-success-ink'">
                    {{ data.status === 'cancelled' ? `Cancelled ${date(data.event?.week_start)}` : 'Active' }}
                  </span>
                </template>
              </Column>
              <Column field="source" header="Source" sortable>
                <template #body="{ data }">
                  <span class="rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="SOURCE_STYLE[data.source as 'added']">{{ sourceLabel(data.source) }}</span>
                </template>
              </Column>
              <Column header="Actions">
                <template #body="{ data }">
                  <div class="flex gap-1">
                    <ConfirmAction
                      v-if="data.event"
                      label="Reinstate"
                      header="Reinstate class"
                      severity="secondary"
                      :message="`Run ${data.name} again? Its members stop counting as affected once the graph is rebuilt.`"
                      @confirm="revoke(data.event.event_id, `${data.name} reinstated`)"
                    />
                    <Button v-else label="Cancel class" size="small" severity="danger" text @click="open({ kind: 'event', type: 'class_cancelled', id: data.id, name: data.name })">
                      <template #icon><CalendarX2 :size="14" /></template>
                    </Button>
                    <Button label="Change instructor" size="small" severity="secondary" text @click="open({ kind: 'reassign', target: data })" />
                  </div>
                </template>
              </Column>
            </DataTableX>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </PageState>
    <p v-if="kg.data.value?.counts" class="m-0 mt-4 flex items-center gap-1.5 text-xs text-ink-500">
      <Database :size="13" aria-hidden="true" />
      Graph holds {{ kg.data.value.counts.instructors }} instructors, {{ kg.data.value.counts.classes }} classes and {{ kg.data.value.counts.events }} events.
    </p>
  </SectionCard>
  </div>

  <Dialog :visible="mode !== null" :header="dialogTitle" modal :style="{ width: 'min(480px, 94vw)' }" @update:visible="(v: boolean) => !v && (mode = null)">
    <form v-if="mode" class="flex flex-col gap-4" @submit.prevent="submit">
      <Message v-if="formError" severity="error" :closable="false">{{ formError }}</Message>
      <template v-if="mode.kind === 'event'">
        <p class="m-0 text-sm text-ink-600">
          {{ mode.type === 'instructor_left' ? 'Their classes lose this instructor in the graph, and members who mostly attended them get flagged.' : 'Members who attend this class get flagged in the graph.' }}
        </p>
        <label class="field"><span>Week starting</span><InputText v-model="form.week_start" type="date" fluid /></label>
        <label class="field"><span>Note (optional)</span><InputText v-model="form.note" maxlength="200" fluid /></label>
      </template>
      <template v-else>
        <label v-if="mode.kind !== 'reassign'" class="field"><span>Name</span><InputText v-model="form.name" maxlength="80" fluid autocomplete="off" /></label>
        <label v-if="mode.kind !== 'reassign'" class="field">
          <span>Club</span>
          <Select v-model="form.club_id" :options="clubOptions" option-label="label" option-value="value" fluid @change="form.instructor_id = ''" />
        </label>
        <label v-if="mode.kind !== 'instructor'" class="field">
          <span>Instructor</span>
          <Select
            v-model="form.instructor_id"
            :options="instructorOptions(form.club_id, mode.kind === 'reassign' ? mode.target.instructor_id : undefined)"
            option-label="label"
            option-value="value"
            placeholder="Pick an instructor at this club"
            fluid
          />
          <small class="text-ink-500">Only instructors still at the club are listed.</small>
        </label>
      </template>
      <div class="flex justify-end gap-2">
        <Button label="Cancel" severity="secondary" text @click="mode = null" />
        <Button
          type="submit"
          :label="mode.kind === 'event' ? (mode.type === 'instructor_left' ? 'Mark as left' : 'Cancel class') : mode.kind === 'reassign' ? 'Change instructor' : 'Add'"
          :severity="mode.kind === 'event' ? 'danger' : undefined"
          :loading="busy"
        />
      </div>
    </form>
  </Dialog>
</template>
