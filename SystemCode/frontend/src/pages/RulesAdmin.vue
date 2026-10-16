<script setup lang="ts">
import { CircleCheck, FlaskConical, Play, ScrollText, TriangleAlert } from 'lucide-vue-next'
import Button from 'primevue/button'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import vTooltip from 'primevue/tooltip'
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { Rule, RuleOutcome, RuleSet } from '../api/types'
import DataTableX from '../components/DataTableX.vue'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import PageState from '../components/PageState.vue'
import RuleTrace from '../components/RuleTrace.vue'
import SectionCard from '../components/SectionCard.vue'
import { useAsync } from '../composables/useAsync'
import { channelLabel, humanize, RULE_KIND_LABELS, ruleCode } from '../labels'
import { useGlossaryStore } from '../stores/glossary'

const KIND_STYLE = {
  derive: 'bg-violet-soft text-violet-ink',
  playbook: 'bg-success-soft text-success-ink',
  guardrail: 'bg-danger-soft text-danger-ink',
} as const

const rules = useAsync(() => api<RuleSet>('/rules'))
const trace = useAsync((id: string) => api<RuleOutcome>(`/rules/trace/${encodeURIComponent(id)}`))
const memberId = ref('M0155')
const glossary = useGlossaryStore()
onMounted(() => {
  rules.run()
  glossary.load()
})

function action(r: Rule) {
  const t = r.then
  if (t.propose) return `Propose ${glossary.offer(t.propose.offer_id)} by ${channelLabel(t.propose.channel)}`
  if (t.block) return `Block ${t.block === 'all' ? 'all offers' : t.block.map(glossary.offer).join(', ')}`
  return `Conclude ${Object.entries(t.assert ?? {}).map(([k, v]) => (v === true ? humanize(k) : `${humanize(k)} = ${v}`)).join(', ')}`
}

function test() {
  const id = memberId.value.trim().toUpperCase()
  if (id) trace.run(id)
}
</script>

<template>
  <div class="page">
    <PageHeader title="Rules" subtitle="Forward-chaining rule base. Guardrails fire first, then higher salience, then more specific rules.">
      <template #actions>
        <span v-if="rules.data.value?.version" class="rounded-full bg-card px-3 py-1.5 text-sm font-medium text-ink-600 ring-1 ring-ink-200">
          Version {{ rules.data.value.version }}
        </span>
      </template>
    </PageHeader>
    <PageState :loading="rules.loading.value" :error="rules.error.value" :empty="rules.data.value?.rules.length === 0" @retry="rules.run">
      <template v-if="rules.data.value">
        <div v-if="!rules.data.value.issues.length" class="banner ok">
          <CircleCheck :size="18" class="shrink-0" aria-hidden="true" />
          <span><strong>Validation passed.</strong> No unknown facts, contradictions or unreachable rules.</span>
        </div>
        <div v-for="(i, n) in rules.data.value.issues" v-else :key="n" class="banner" :class="i.severity === 'error' ? 'error' : 'warn'">
          <TriangleAlert :size="18" class="shrink-0" aria-hidden="true" />
          <span><strong>{{ glossary.rule(i.rule_id) }}</strong> <span class="id-chip">{{ ruleCode(i.rule_id) }}</span>: {{ i.message }}</span>
        </div>

        <div class="mt-5 grid items-start gap-5 2xl:grid-cols-[minmax(0,2fr)_minmax(24rem,1fr)]">
          <SectionCard :title="`${rules.data.value.rules.length} rules`" subtitle="Sorted by salience" :icon="ScrollText">
            <DataTableX
              :value="rules.data.value.rules"
              data-key="id"
              export-name="rules"
              :global-filter-fields="['id', 'description', 'source', 'kind']"
              :rows="50"
              sort-field="salience"
              :sort-order="-1"
            >
              <Column field="description" header="Rule" sortable>
                <template #body="{ data }">
                  <div class="flex min-w-80 flex-col gap-1 whitespace-normal">
                    <span class="font-medium text-ink-800">{{ data.description }}</span>
                    <span class="flex flex-wrap items-baseline gap-x-2 text-xs text-ink-500">
                      <span v-tooltip.top="data.id" class="id-chip">{{ ruleCode(data.id) }}</span>
                      <span>Source: {{ data.source }}</span>
                    </span>
                  </div>
                </template>
              </Column>
              <Column field="kind" header="Kind" sortable>
                <template #body="{ data }">
                  <span class="rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="KIND_STYLE[data.kind as Rule['kind']]">
                    {{ RULE_KIND_LABELS[data.kind as Rule['kind']] }}
                  </span>
                </template>
              </Column>
              <Column field="salience" header="Salience" sortable>
                <template #body="{ data }"><span class="tabular-nums">{{ data.salience }}</span></template>
              </Column>
              <Column header="When">
                <template #body="{ data }">
                  <div class="flex flex-col items-start gap-1">
                    <code v-for="c in (data as Rule).when" :key="c" class="cond">{{ c }}</code>
                  </div>
                </template>
              </Column>
              <Column header="Then">
                <template #body="{ data }"><span class="block min-w-48 whitespace-normal">{{ action(data) }}</span></template>
              </Column>
            </DataTableX>
          </SectionCard>

          <SectionCard title="Test on a member" subtitle="Run the rule base and see the firing trace" :icon="FlaskConical" class="2xl:sticky 2xl:top-[calc(var(--topbar-h)+1.5rem)]">
            <form class="toolbar mb-5" @submit.prevent="test">
              <label class="field min-w-40 flex-1">
                <span>Member ID</span>
                <InputText v-model="memberId" placeholder="M0155" fluid />
              </label>
              <Button type="submit" label="Run rules" :loading="trace.loading.value">
                <template #icon><Play :size="15" /></template>
              </Button>
            </form>
            <PageState :loading="trace.loading.value" :error="trace.error.value" :empty="!trace.data.value">
              <template #empty>
                <EmptyState :icon="FlaskConical" compact text="Run the rule base on a member to see the firing trace." />
              </template>
              <RuleTrace v-if="trace.data.value" :outcome="trace.data.value" />
            </PageState>
          </SectionCard>
        </div>
      </template>
    </PageState>
  </div>
</template>

<style scoped>
.banner { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.5rem; padding: 0.75rem 1rem; border-radius: 0.75rem; font-size: 0.875rem; border: 1px solid; }
.banner.ok { background: var(--color-success-soft); border-color: var(--color-success-line); color: var(--color-success-ink); }
.banner.warn { background: var(--color-warn-soft); border-color: var(--color-warn-line); color: var(--color-warn-ink); }
.banner.error { background: var(--color-danger-soft); border-color: var(--color-danger-line); color: var(--color-danger-ink); }
.cond { padding: 0.1rem 0.4rem; border-radius: 5px; font-size: 0.75rem; white-space: nowrap; color: var(--color-ink-700); background: var(--color-ink-100); }
</style>
