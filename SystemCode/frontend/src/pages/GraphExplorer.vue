<script setup lang="ts">
import { ArrowRight, Network, Search, TriangleAlert, Users, Zap } from 'lucide-vue-next'
import Button from 'primevue/button'
import Column from 'primevue/column'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import vTooltip from 'primevue/tooltip'
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { AffectedMember, EgoGraph as EgoGraphData, EventType, GraphEntities, Simulation } from '../api/types'
import DataTableX from '../components/DataTableX.vue'
import EgoGraph from '../components/EgoGraph.vue'
import EmptyState from '../components/EmptyState.vue'
import KpiTile from '../components/KpiTile.vue'
import PageHeader from '../components/PageHeader.vue'
import PageState from '../components/PageState.vue'
import RiskBadge from '../components/RiskBadge.vue'
import SectionCard from '../components/SectionCard.vue'
import { useAsync } from '../composables/useAsync'
import { pct } from '../format'
import { ruleCode } from '../labels'
import { useGlossaryStore } from '../stores/glossary'

const entities = useAsync(() => api<GraphEntities>('/graph/entities'))
const sim = useAsync((event_type: EventType, entity_id: string) =>
  api<Simulation>('/graph/simulate', { method: 'POST', body: JSON.stringify({ event_type, entity_id }) }),
)
const ego = useAsync((id: string) => api<EgoGraphData>(`/graph/ego/${encodeURIComponent(id)}`))

const glossary = useGlossaryStore()
const target = ref<string | null>(null)
const memberId = ref('')
// The member whose graph is shown; the input can be edited without changing the link.
const shown = ref('')
onMounted(() => {
  entities.run()
  glossary.load()
})

const options = computed(() => {
  const e = entities.data.value
  if (!e) return []
  const mark = (has: boolean) => (has ? ' (already happened)' : '')
  return [
    {
      label: 'Instructor leaves',
      items: e.instructors.map((i) => ({ label: `${i.name} · Club ${i.club_id}${mark(i.has_event)}`, value: `instructor_left:${i.id}` })),
    },
    {
      label: 'Class cancelled',
      items: e.classes.map((c) => ({ label: `${c.name} ${c.detail} · Club ${c.club_id}${mark(c.has_event)}`, value: `class_cancelled:${c.id}` })),
    },
  ]
})

function simulate() {
  if (!target.value) return
  const [type, id] = target.value.split(':')
  sim.run(type as EventType, id)
}

function showMember(id: string) {
  memberId.value = id
  shown.value = id
  ego.run(id)
}

function offers(m: AffectedMember) {
  return m.allowed.map((p) => glossary.offer(p.offer_id)).join(', ') || '—'
}

function onSelect(type: string, id: string) {
  if (type === 'Member' && id !== shown.value) showMember(id)
}
</script>

<template>
  <div class="page">
    <PageHeader
      title="Knowledge graph"
      subtitle="Simulate an instructor leaving or a class closing to see who it would affect. Nothing in the data changes."
    />
    <div class="grid items-start gap-5 xl:grid-cols-[minmax(0,1.6fr)_minmax(22rem,1fr)]">
      <SectionCard title="Simulate an event" subtitle="Pick an instructor or class; affected members and the rules they newly trigger appear below" :icon="Zap">
        <PageState :loading="entities.loading.value" :error="entities.error.value" @retry="entities.run">
          <form class="toolbar mb-5" @submit.prevent="simulate">
            <label class="field min-w-60 flex-1">
              <span>Event</span>
              <Select
                v-model="target"
                :options="options"
                option-group-label="label"
                option-group-children="items"
                option-label="label"
                option-value="value"
                placeholder="Pick an instructor or class"
                filter
                fluid
              />
            </label>
            <Button type="submit" label="Run simulation" :disabled="!target" :loading="sim.loading.value">
              <template #icon><Zap :size="16" /></template>
            </Button>
          </form>
          <PageState :loading="sim.loading.value" :error="sim.error.value" :empty="!sim.data.value">
            <template #empty>
              <EmptyState :icon="Network" title="No simulation yet" text="Pick an event to see who it would affect and which rules they would trigger." />
            </template>
            <template v-if="sim.data.value">
              <p class="m-0 mb-4 flex items-center gap-2 rounded-lg bg-warn-soft px-3.5 py-2.5 text-sm font-medium text-warn-ink">
                <TriangleAlert :size="16" class="shrink-0" aria-hidden="true" /> If {{ sim.data.value.label }}
              </p>
              <div class="mb-5 grid gap-3 sm:grid-cols-3">
                <KpiTile label="Members affected" :value="sim.data.value.affected.toLocaleString()" :icon="Users" />
                <KpiTile label="High risk" :value="sim.data.value.high_risk.toLocaleString()" tone="warn" :icon="TriangleAlert" />
                <KpiTile label="Newly trigger rules" :value="sim.data.value.newly_flagged.toLocaleString()" :icon="Zap" />
              </div>
              <DataTableX :value="sim.data.value.members" data-key="member_id" export-name="affected-members" :rows="10" :global-filter-fields="['member_id', 'risk_band']">
                <Column field="member_id" header="Member" sortable>
                  <template #body="{ data }">
                    <button type="button" class="member-link cursor-pointer border-0 bg-transparent p-0 font-[inherit]" @click="showMember(data.member_id)">
                      {{ data.member_id }}
                    </button>
                  </template>
                </Column>
                <Column field="churn_prob" header="Risk" sortable>
                  <template #body="{ data }"><RiskBadge :band="data.risk_band" :prob="data.churn_prob" /></template>
                </Column>
                <Column v-if="sim.data.value.event_type === 'instructor_left'" field="share" header="Visits with them" sortable>
                  <template #body="{ data }"><span class="tabular-nums">{{ pct(data.share) }}</span></template>
                </Column>
                <Column header="New rules">
                  <template #body="{ data }">
                    <span v-if="!data.new_rules.length" class="text-ink-400">None</span>
                    <span class="flex flex-wrap gap-1">
                      <span
                        v-for="r in data.new_rules"
                        :key="r"
                        v-tooltip.top="glossary.rule(r)"
                        class="inline-flex max-w-64 items-center gap-1.5 rounded-md bg-brand-50 px-2 py-0.5 text-xs text-brand-800"
                        tabindex="0"
                        :aria-label="glossary.rule(r)"
                      >
                        <span class="truncate">{{ glossary.rule(r) }}</span>
                        <span class="font-mono text-[0.65rem] opacity-70">{{ ruleCode(r) }}</span>
                      </span>
                    </span>
                  </template>
                </Column>
                <Column header="Allowed offers">
                  <template #body="{ data }"><span class="whitespace-normal">{{ offers(data) }}</span></template>
                </Column>
              </DataTableX>
            </template>
          </PageState>
        </PageState>
      </SectionCard>

      <SectionCard title="Member neighbourhood" subtitle="Classes, instructors, club and events linked to one member" :icon="Network" class="xl:sticky xl:top-[calc(var(--topbar-h)+1.5rem)]">
        <form class="toolbar mb-4" @submit.prevent="showMember(memberId.trim().toUpperCase())">
          <label class="field min-w-40 flex-1">
            <span>Member ID</span>
            <IconField>
              <InputIcon><Search :size="15" /></InputIcon>
              <InputText v-model="memberId" placeholder="M0155" fluid />
            </IconField>
          </label>
          <Button type="submit" label="Show" severity="secondary" outlined :disabled="!memberId.trim()" />
        </form>
        <PageState :loading="ego.loading.value" :error="ego.error.value" :empty="!ego.data.value">
          <template #empty>
            <EmptyState :icon="Users" compact text="Pick a member from the table, or type an ID." />
          </template>
          <EgoGraph v-if="ego.data.value" :graph="ego.data.value" height="480px" @select="onSelect" />
          <RouterLink v-if="ego.data.value" :to="`/members/${encodeURIComponent(shown)}`" class="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold no-underline">
            Open {{ shown }} in Member 360 <ArrowRight :size="15" aria-hidden="true" />
          </RouterLink>
        </PageState>
      </SectionCard>
    </div>
  </div>
</template>

