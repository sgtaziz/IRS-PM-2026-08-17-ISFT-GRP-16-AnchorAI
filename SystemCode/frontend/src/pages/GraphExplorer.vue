<script setup lang="ts">
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { AffectedMember, EgoGraph as EgoGraphData, EventType, GraphEntities, Simulation } from '../api/types'
import DataTableX from '../components/DataTableX.vue'
import EgoGraph from '../components/EgoGraph.vue'
import KpiTile from '../components/KpiTile.vue'
import PageState from '../components/PageState.vue'
import RiskBadge from '../components/RiskBadge.vue'
import { useAsync } from '../composables/useAsync'
import { pct } from '../format'

const entities = useAsync(() => api<GraphEntities>('/graph/entities'))
const sim = useAsync((event_type: EventType, entity_id: string) =>
  api<Simulation>('/graph/simulate', { method: 'POST', body: JSON.stringify({ event_type, entity_id }) }),
)
const ego = useAsync((id: string) => api<EgoGraphData>(`/graph/ego/${id}`))

const target = ref<string | null>(null)
const memberId = ref('')
onMounted(entities.run)

const options = computed(() => {
  const e = entities.data.value
  if (!e) return []
  const mark = (has: boolean) => (has ? ' (already happened)' : '')
  return [
    {
      label: 'Instructor leaves',
      items: e.instructors.map((i) => ({ label: `${i.name} · ${i.club_id}${mark(i.has_event)}`, value: `instructor_left:${i.id}` })),
    },
    {
      label: 'Class cancelled',
      items: e.classes.map((c) => ({ label: `${c.name} ${c.detail} · ${c.club_id}${mark(c.has_event)}`, value: `class_cancelled:${c.id}` })),
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
  ego.run(id)
}

function offers(m: AffectedMember) {
  return m.allowed.map((p) => p.offer_id).join(', ') || '—'
}

function onSelect(type: string, id: string) {
  if (type === 'Member' && id !== memberId.value) showMember(id)
}
</script>

<template>
  <div class="page-head">
    <h2>Knowledge graph</h2>
    <span class="sub">Simulate an instructor leaving or a class closing; nothing in the data changes</span>
  </div>
  <div class="grid layout-graph">
    <Card>
      <template #title>Simulate an event</template>
      <template #content>
        <PageState :loading="entities.loading.value" :error="entities.error.value" @retry="entities.run">
          <form class="toolbar" @submit.prevent="simulate">
            <label class="field grow">
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
            <Button type="submit" label="Simulate" :disabled="!target" :loading="sim.loading.value" />
          </form>
          <PageState :loading="sim.loading.value" :error="sim.error.value" :empty="!sim.data.value" empty-text="Pick an event to see who it would affect and which rules they would trigger.">
            <template v-if="sim.data.value">
              <h3 class="label">If {{ sim.data.value.label }}</h3>
              <div class="grid kpis">
                <KpiTile label="Members affected" :value="sim.data.value.affected.toLocaleString()" />
                <KpiTile label="High risk" :value="sim.data.value.high_risk.toLocaleString()" />
                <KpiTile label="Newly trigger rules" :value="sim.data.value.newly_flagged.toLocaleString()" />
              </div>
              <DataTableX :value="sim.data.value.members" data-key="member_id" export-name="affected-members" :rows="10" :global-filter-fields="['member_id', 'risk_band']">
                <Column field="member_id" header="Member" sortable>
                  <template #body="{ data }">
                    <Button :label="data.member_id" link size="small" @click="showMember(data.member_id)" />
                  </template>
                </Column>
                <Column field="churn_prob" header="Risk" sortable>
                  <template #body="{ data }"><RiskBadge :band="data.risk_band" :prob="data.churn_prob" /></template>
                </Column>
                <Column v-if="sim.data.value.event_type === 'instructor_left'" field="share" header="Visits with them" sortable>
                  <template #body="{ data }">{{ pct(data.share) }}</template>
                </Column>
                <Column header="New rules">
                  <template #body="{ data }">
                    <span v-if="!data.new_rules.length" class="muted">none</span>
                    <Tag v-for="r in data.new_rules" :key="r" :value="r" severity="info" class="tag" />
                  </template>
                </Column>
                <Column header="Allowed offers">
                  <template #body="{ data }">{{ offers(data) }}</template>
                </Column>
              </DataTableX>
            </template>
          </PageState>
        </PageState>
      </template>
    </Card>

    <Card>
      <template #title>Member neighbourhood</template>
      <template #content>
        <form class="toolbar" @submit.prevent="showMember(memberId.trim().toUpperCase())">
          <label class="field">
            <span>Member id</span>
            <InputText v-model="memberId" placeholder="M0155" size="small" />
          </label>
          <Button type="submit" label="Show" size="small" :disabled="!memberId.trim()" />
        </form>
        <PageState :loading="ego.loading.value" :error="ego.error.value" :empty="!ego.data.value" empty-text="Pick a member from the table, or type an id.">
          <EgoGraph v-if="ego.data.value" :graph="ego.data.value" @select="onSelect" />
          <RouterLink v-if="ego.data.value" :to="`/members/${memberId}`" class="open">Open Member 360</RouterLink>
        </PageState>
      </template>
    </Card>
  </div>
</template>

<style scoped>
.layout-graph { grid-template-columns: minmax(0, 3fr) minmax(320px, 2fr); align-items: start; }
@media (max-width: 1100px) { .layout-graph { grid-template-columns: 1fr; } }
.grow { flex: 1; min-width: 240px; }
.label { margin: 0 0 0.75rem; font-size: 1rem; }
.tag { margin: 0 0.25rem 0.25rem 0; }
.open { display: inline-block; margin-top: 0.5rem; }
</style>
