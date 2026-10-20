<script setup lang="ts">
import { Bot, CalendarCheck, Database, Network, PlugZap, Sigma } from 'lucide-vue-next'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { HealthDetails, LlmTest } from '../api/types'
import PageHeader from '../components/PageHeader.vue'
import PageState from '../components/PageState.vue'
import SectionCard from '../components/SectionCard.vue'
import { errorMessage, useAsync } from '../composables/useAsync'
import { dateTime, num } from '../format'
import { humanize } from '../labels'

// W45: is everything the planner and assistant depend on healthy and current?
const health = useAsync(() => api<HealthDetails>('/health/details'))
onMounted(health.run)

const testing = ref(false)
const llmResult = ref<LlmTest | null>(null)
const llmError = ref<string | null>(null)
async function testLlm() {
  testing.value = true
  llmResult.value = llmError.value = null
  try {
    llmResult.value = await api<LlmTest>('/health/llm-test', { method: 'POST' })
  } catch (e) {
    llmError.value = errorMessage(e)
  } finally {
    testing.value = false
  }
}

const TONE = { good: 'bg-success-soft text-success-ink', bad: 'bg-danger-soft text-danger-ink', warn: 'bg-warn-soft text-warn-ink' }
</script>

<template>
  <div class="page">
    <PageHeader title="Settings" subtitle="System health and configuration." />
    <PageState :loading="health.loading.value" :error="health.error.value" @retry="health.run">
      <div v-if="health.data.value" class="grid gap-6 lg:grid-cols-2">
        <SectionCard title="Language model" :icon="Bot" subtitle="Used by the assistant and message drafts. Set in .env (LLM_BASE_URL, LLM_MODEL, LLM_API_KEY).">
          <dl class="settings-list">
            <dt>Endpoint</dt>
            <dd class="font-mono text-xs">{{ health.data.value.llm.base_url }}</dd>
            <dt>Model</dt>
            <dd>{{ health.data.value.llm.model }}</dd>
            <dt>API key</dt>
            <dd>{{ health.data.value.llm.api_key ?? 'not set' }}</dd>
            <dt>Tool calling</dt>
            <dd>{{ health.data.value.llm.tool_calling ? 'on' : 'off (intent router picks the tool)' }}</dd>
          </dl>
          <div class="flex flex-col gap-3 px-5 pb-5">
            <Button label="Test connection" size="small" severity="secondary" outlined :loading="testing" class="self-start" @click="testLlm">
              <template #icon><PlugZap :size="15" /></template>
            </Button>
            <Message v-if="llmResult?.ok" severity="success">Connected in {{ llmResult.seconds }} s. The model replied “{{ llmResult.reply }}”.</Message>
            <Message v-else-if="llmResult" severity="error">
              Not reachable after {{ llmResult.seconds }} s: {{ llmResult.error?.replace(/\.$/, '') }}. The assistant falls back to grounded templates.
            </Message>
            <Message v-if="llmError" severity="error">{{ llmError }}</Message>
          </div>
        </SectionCard>

        <SectionCard title="Knowledge graph" :icon="Network" subtitle="Neo4j, loaded from the data tables and gym edits.">
          <dl class="settings-list">
            <dt>Neo4j</dt>
            <dd>
              <span class="chip" :class="health.data.value.knowledge_graph.reachable ? TONE.good : TONE.bad">
                {{ health.data.value.knowledge_graph.reachable ? 'Reachable' : 'Not reachable' }}
              </span>
              <span class="ml-2 font-mono text-xs text-ink-500">{{ health.data.value.knowledge_graph.uri }}</span>
            </dd>
            <dt>Graph facts</dt>
            <dd>
              <span class="chip" :class="health.data.value.knowledge_graph.stale ? TONE.warn : TONE.good">
                {{ health.data.value.knowledge_graph.stale ? 'Stale' : 'Current' }}
              </span>
              <span v-if="health.data.value.knowledge_graph.problem" class="ml-2 text-ink-600">{{ health.data.value.knowledge_graph.problem }}</span>
            </dd>
            <template v-if="health.data.value.knowledge_graph.last_reloaded_at">
              <dt>Last reload</dt>
              <dd>{{ dateTime(health.data.value.knowledge_graph.last_reloaded_at) }}</dd>
            </template>
            <template v-if="health.data.value.knowledge_graph.counts">
              <dt>Loaded</dt>
              <dd>
                {{ Object.entries(health.data.value.knowledge_graph.counts).map(([k, v]) => `${v.toLocaleString()} ${humanize(k).toLowerCase()}`).join(' · ') }}
              </dd>
            </template>
          </dl>
        </SectionCard>

        <SectionCard title="Models and data" :icon="Sigma" subtitle="Built by anchorai setup or data build (Stream A).">
          <dl v-if="health.data.value.models.built" class="settings-list">
            <dt>Built</dt>
            <dd>{{ dateTime(health.data.value.models.built_at) }} · seed {{ health.data.value.models.seed }}</dd>
            <dt>Members</dt>
            <dd>{{ health.data.value.models.members?.toLocaleString() }}</dd>
            <dt>Churn model</dt>
            <dd>{{ health.data.value.models.churn_model }}</dd>
            <dt>Test scores</dt>
            <dd>
              F1 {{ num(health.data.value.models.churn_test?.f1, 3) }} · PR-AUC {{ num(health.data.value.models.churn_test?.pr_auc, 3) }} · Brier
              {{ num(health.data.value.models.churn_test?.brier, 3) }}
            </dd>
            <dt>Uplift baseline</dt>
            <dd>{{ health.data.value.models.uplift_baseline }}</dd>
          </dl>
          <Message v-else severity="warn" class="mx-5 mb-5">The data and models have not been built yet. Run <code>uv run anchorai setup</code>.</Message>
        </SectionCard>

        <SectionCard title="Database and planner" :icon="Database" subtitle="App database (SQLite, migrated by Alembic) and the weekly planner.">
          <dl class="settings-list">
            <dt>Migration</dt>
            <dd>
              <span class="chip" :class="health.data.value.database.up_to_date ? TONE.good : TONE.warn">
                {{ health.data.value.database.up_to_date ? 'Up to date' : 'Needs migrating' }}
              </span>
              <span class="ml-2 font-mono text-xs text-ink-500">{{ health.data.value.database.revision ?? 'none' }}</span>
            </dd>
            <dt>Latest plan</dt>
            <dd>
              <template v-if="health.data.value.planner.latest_plan">
                <CalendarCheck :size="14" class="inline align-[-2px]" />
                #{{ health.data.value.planner.latest_plan.id }} · {{ humanize(health.data.value.planner.latest_plan.status) }} ·
                {{ dateTime(health.data.value.planner.latest_plan.created_at) }}
              </template>
              <template v-else>None yet</template>
            </dd>
            <dt>Uplift estimates</dt>
            <dd>Case-based reasoning</dd>
            <dt>Case base</dt>
            <dd>
              {{ health.data.value.planner.case_base.randomised?.toLocaleString() ?? '—' }} randomised past interventions +
              {{ health.data.value.planner.case_base.logged.toLocaleString() }} logged outcomes
            </dd>
          </dl>
        </SectionCard>
      </div>
    </PageState>
  </div>
</template>

<style scoped>
.settings-list {
  display: grid;
  grid-template-columns: 8.5rem 1fr;
  gap: 0.6rem 1rem;
  margin: 0;
  padding: 0.75rem 1.25rem 1.25rem;
  font-size: 0.875rem;
}
.settings-list dt {
  color: var(--color-ink-500);
}
.settings-list dd {
  margin: 0;
  color: var(--color-ink-800);
  min-width: 0;
  overflow-wrap: anywhere;
}
.chip {
  display: inline-block;
  border-radius: 9999px;
  padding: 0.05rem 0.55rem;
  font-size: 0.75rem;
  font-weight: 500;
}
</style>
