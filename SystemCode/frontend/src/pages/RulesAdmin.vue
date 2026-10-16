<script setup lang="ts">
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { Rule, RuleOutcome, RuleSet } from '../api/types'
import DataTableX from '../components/DataTableX.vue'
import PageState from '../components/PageState.vue'
import RuleTrace from '../components/RuleTrace.vue'
import { useAsync } from '../composables/useAsync'

const KIND_SEVERITY = { derive: 'info', playbook: 'success', guardrail: 'danger' } as const

const rules = useAsync(() => api<RuleSet>('/rules'))
const trace = useAsync((id: string) => api<RuleOutcome>(`/rules/trace/${encodeURIComponent(id)}`))
const memberId = ref('M0155')
onMounted(rules.run)

function action(r: Rule) {
  const t = r.then
  if (t.propose) return `propose ${t.propose.offer_id} via ${t.propose.channel}`
  if (t.block) return `block ${t.block === 'all' ? 'all offers' : t.block.join(', ')}`
  return `assert ${Object.entries(t.assert ?? {}).map(([k, v]) => `${k} = ${v}`).join(', ')}`
}

function test() {
  const id = memberId.value.trim().toUpperCase()
  if (id) trace.run(id)
}
</script>

<template>
  <div class="page-head">
    <h2>Rules</h2>
    <span class="sub">
      Forward-chaining rule base{{ rules.data.value?.version ? ` · version ${rules.data.value.version}` : '' }};
      guardrails fire first, then higher salience, then more specific rules
    </span>
  </div>
  <PageState :loading="rules.loading.value" :error="rules.error.value" :empty="rules.data.value?.rules.length === 0" @retry="rules.run">
    <template v-if="rules.data.value">
      <Message v-if="!rules.data.value.issues.length" severity="success" :closable="false">
        Validation: no unknown facts, contradictions or unreachable rules.
      </Message>
      <Message v-for="(i, n) in rules.data.value.issues" v-else :key="n" :severity="i.severity === 'error' ? 'error' : 'warn'" :closable="false">
        <strong>{{ i.rule_id }}</strong>: {{ i.message }}
      </Message>

      <div class="grid layout-rules">
        <DataTableX
          :value="rules.data.value.rules"
          data-key="id"
          export-name="rules"
          :global-filter-fields="['id', 'description', 'source', 'kind']"
          :rows="50"
          sort-field="salience"
          :sort-order="-1"
        >
          <Column field="id" header="Rule" sortable />
          <Column field="kind" header="Kind" sortable>
            <template #body="{ data }"><Tag :value="data.kind" :severity="KIND_SEVERITY[data.kind as Rule['kind']]" /></template>
          </Column>
          <Column field="salience" header="Salience" sortable />
          <Column header="When">
            <template #body="{ data }">
              <code v-for="c in (data as Rule).when" :key="c" class="cond">{{ c }}</code>
            </template>
          </Column>
          <Column header="Then"><template #body="{ data }">{{ action(data) }}</template></Column>
          <Column field="description" header="Description" />
          <Column field="source" header="Source" />
        </DataTableX>

        <Card>
          <template #title>Test on a member</template>
          <template #content>
            <form class="toolbar" @submit.prevent="test">
              <label class="field">
                <span>Member id</span>
                <InputText v-model="memberId" placeholder="M0155" size="small" />
              </label>
              <Button type="submit" label="Run rules" size="small" :loading="trace.loading.value" />
            </form>
            <PageState :loading="trace.loading.value" :error="trace.error.value" :empty="!trace.data.value" empty-text="Run the rule base on a member to see the firing trace.">
              <RuleTrace v-if="trace.data.value" :outcome="trace.data.value" />
            </PageState>
          </template>
        </Card>
      </div>
    </template>
  </PageState>
</template>

<style scoped>
.layout-rules { grid-template-columns: minmax(0, 2fr) minmax(300px, 1fr); align-items: start; margin-top: 1rem; }
@media (max-width: 1100px) { .layout-rules { grid-template-columns: 1fr; } }
.cond { display: block; font-size: 0.8rem; white-space: nowrap; }
</style>
