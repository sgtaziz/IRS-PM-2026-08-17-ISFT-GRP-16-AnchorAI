<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { Activity, BrainCircuit, ChartLine, Database, FileSpreadsheet, Gauge, Network, RefreshCw, Scale, Target, Upload } from 'lucide-vue-next'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import { useToast } from 'primevue/usetoast'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { BuildStatus, DataOverview, Fairness, Metrics } from '../api/types'
import ChartCard from '../components/ChartCard.vue'
import ConfirmAction from '../components/ConfirmAction.vue'
import KpiTile from '../components/KpiTile.vue'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import PageState from '../components/PageState.vue'
import SectionCard from '../components/SectionCard.vue'
import { errorMessage, useAsync } from '../composables/useAsync'
import { dateTime, num, pct } from '../format'

const POLL_MS = 2000
const toast = useToast()
const overview = useAsync(() => api<DataOverview>('/admin/data'))
const seed = ref<number | null>(null)
let timer: number | undefined

const card = computed(() => overview.data.value)
const churn = computed(() => card.value?.churn)
const build = computed<BuildStatus | undefined>(() => card.value?.build)
const running = computed(() => build.value?.state === 'running')
const built = computed(() => !!churn.value)

async function load() {
  const data = await overview.run()
  if (data && seed.value === null) seed.value = data.seed ?? 42
  schedulePoll()
}

function schedulePoll() {
  window.clearTimeout(timer)
  if (running.value) timer = window.setTimeout(poll, POLL_MS)
}

async function poll() {
  const before = build.value?.state
  const data = await overview.run()
  if (before === 'running' && data?.build.state === 'done')
    toast.add({ severity: 'success', summary: 'Rebuild finished', detail: 'Models and scores are up to date.', life: 5000 })
  if (before === 'running' && data?.build.state === 'failed')
    toast.add({ severity: 'error', summary: 'Rebuild failed', detail: data.build.error ?? '', life: 8000 })
  schedulePoll()
}

onMounted(load)
onBeforeUnmount(() => window.clearTimeout(timer))

async function rebuild() {
  try {
    await api<BuildStatus>('/admin/data/rebuild', { method: 'POST', body: JSON.stringify({ seed: seed.value }) })
    toast.add({ severity: 'info', summary: 'Rebuild started', detail: 'This takes about 20 seconds.', life: 4000 })
    await load()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Could not start rebuild', detail: errorMessage(e), life: 6000 })
  }
}

const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)

async function upload(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  uploading.value = true
  try {
    const res = await api<{ rows: number }>('/admin/data/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'text/csv' },
      body: await file.text(),
    })
    toast.add({
      severity: 'success',
      summary: `Uploaded ${res.rows.toLocaleString()} members`,
      detail: 'Rebuild to retrain on the new file.',
      life: 6000,
    })
    await load()
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Upload rejected', detail: errorMessage(e), life: 8000 })
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

const kgMessage = ref<string | null>(null)
async function rebuildKg() {
  try {
    await api<unknown>('/graph/rebuild', { method: 'POST' })
    kgMessage.value = null
    toast.add({ severity: 'success', summary: 'Knowledge graph rebuilt', life: 4000 })
  } catch {
    kgMessage.value = 'Knowledge-graph rebuild is not available yet (Stream C). Run `uv run anchorai kg load` instead.'
  }
}

const METRICS: [keyof Metrics, string][] = [
  ['f1', 'F1 (churn)'],
  ['precision', 'Precision'],
  ['recall', 'Recall'],
  ['pr_auc', 'PR-AUC'],
  ['roc_auc', 'ROC-AUC'],
  ['brier', 'Brier (lower is better)'],
]

const comparison = computed(() => {
  const c = churn.value
  if (!c) return []
  return [
    { name: 'AnchorAI ensemble (calibrated)', m: c.test },
    { name: 'Single logistic regression', m: c.baselines.single_lr },
    { name: c.baselines.visit_rule.rule, m: c.baselines.visit_rule },
    { name: 'Ensemble without suspect features', m: c.leakage.without_suspect.test },
  ]
})

const silhouetteOption = computed<EChartsOption | null>(() => {
  const s = card.value?.segmentation
  if (!s) return null
  const ks = Object.keys(s.silhouette_by_k).sort((a, b) => +a - +b)
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 16, right: 24, top: 36, bottom: 36, containLabel: true },
    xAxis: { type: 'category', name: 'k', nameLocation: 'middle', nameGap: 24, data: ks },
    yAxis: { type: 'value', name: 'Silhouette', scale: true },
    series: [
      {
        type: 'line',
        data: ks.map((k) => +s.silhouette_by_k[k].toFixed(3)),
        markLine: { symbol: 'none', data: [{ xAxis: String(s.k), name: 'chosen k' }], label: { formatter: `chosen k = ${s.k}` } },
      },
    ],
  }
})

const calibrationOption = computed<EChartsOption | null>(() => {
  const cal = churn.value?.calibration
  if (!cal) return null
  const pairs = (c: { predicted: number[]; observed: number[] }) => c.predicted.map((p, i) => [+p.toFixed(3), +c.observed[i].toFixed(3)])
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    grid: { left: 16, right: 24, top: 36, bottom: 56, containLabel: true },
    xAxis: { type: 'value', name: 'Predicted', nameLocation: 'middle', nameGap: 24, min: 0, max: 1 },
    yAxis: { type: 'value', name: 'Observed', min: 0, max: 1 },
    series: [
      { name: 'Calibrated', type: 'line', data: pairs(cal.calibrated) },
      { name: 'Before calibration', type: 'line', data: pairs(cal.uncalibrated), lineStyle: { type: 'dashed' } },
      { name: 'Perfect', type: 'line', data: [[0, 0], [1, 1]], symbol: 'none', lineStyle: { color: '#98a2b6', type: 'dotted' }, itemStyle: { color: '#98a2b6' } },
    ],
  }
})

const fairness = computed(() => {
  const f = churn.value?.fairness
  if (!f) return []
  return (Object.entries(f) as [string, Fairness][]).map(([attr, v]) => ({
    attr: attr === 'age_band' ? 'Age band' : 'Gender (coded 0/1 in source data)',
    ...v,
  }))
})

const STATE_STYLE: Record<string, { label: string; cls: string }> = {
  idle: { label: 'Idle', cls: 'bg-ink-100 text-ink-600' },
  running: { label: 'Running', cls: 'bg-brand-50 text-brand-700' },
  done: { label: 'Up to date', cls: 'bg-success-soft text-success-ink' },
  failed: { label: 'Failed', cls: 'bg-danger-soft text-danger-ink' },
}
const stateStyle = (s: string | undefined) => STATE_STYLE[s ?? 'idle'] ?? STATE_STYLE.idle
</script>

<template>
  <div class="page">
    <PageHeader
      title="Data & models"
      :subtitle="card?.built_at ? `Built ${dateTime(card.built_at)} · seed ${card.seed}` : 'Source data, rebuilds and the model card'"
    />
    <PageState :loading="overview.loading.value && !card" :error="overview.error.value" @retry="load">
      <template v-if="card">
        <div class="mb-6 grid items-start gap-5 lg:grid-cols-2">
          <SectionCard title="Source data" :icon="FileSpreadsheet">
            <dl class="kv">
              <dt>Raw file</dt>
              <dd>{{ card.raw ? `${card.raw.name} (${(card.raw.bytes / 1024).toFixed(0)} KB)` : 'Missing' }}</dd>
              <dt>Uploaded</dt>
              <dd>{{ dateTime(card.raw?.modified_at) }}</dd>
              <dt>Members</dt>
              <dd>{{ card.n_members?.toLocaleString() ?? '—' }}</dd>
              <dt>Licence</dt>
              <dd>Kaggle "Gym Customers Features and Churn", CC BY-NC-SA 4.0</dd>
            </dl>
            <label for="raw-upload" class="field mt-5">
              <span class="inline-flex items-center gap-1.5"><Upload :size="14" aria-hidden="true" /> Replace with a new Kaggle CSV</span>
              <input
                id="raw-upload"
                ref="fileInput"
                type="file"
                accept=".csv,text/csv"
                :disabled="uploading"
                class="block w-full rounded-lg border border-dashed border-ink-300 bg-ink-50 p-2 text-sm text-ink-600 file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-card file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-ink-800 file:shadow-card file:ring-1 file:ring-ink-200"
                @change="upload"
              />
            </label>
          </SectionCard>
          <SectionCard title="Rebuild" :icon="RefreshCw">
            <template #actions>
              <span class="rounded-full px-2.5 py-1 text-xs font-semibold" :class="stateStyle(build?.state).cls">{{ stateStyle(build?.state).label }}</span>
            </template>
            <p class="m-0 mb-4 text-sm text-ink-600">
              Regenerates the scenario layer, retrains segmentation and the churn model, and rescores every member.
            </p>
            <div class="toolbar">
              <label class="field">
                <span>Seed</span>
                <InputNumber v-model="seed" :min="0" :use-grouping="false" input-class="narrow" />
              </label>
              <ConfirmAction
                label="Rebuild data and models"
                severity="primary"
                :disabled="running"
                message="Rebuild all data tables and models? Other streams' results change if the seed changes."
                @confirm="rebuild"
              />
              <Button label="Rebuild knowledge graph" size="small" severity="secondary" outlined @click="rebuildKg">
                <template #icon><Network :size="15" /></template>
              </Button>
            </div>
            <p v-if="build?.finished_at" class="m-0 mt-4 text-xs text-ink-500">Last finished {{ dateTime(build.finished_at) }}</p>
            <ProgressBar v-if="running" mode="indeterminate" class="mt-3" style="height: 6px" aria-label="Rebuild in progress" />
            <Message v-if="build?.state === 'failed'" severity="error" :closable="false" class="mt-3">{{ build.error }}</Message>
            <Message v-if="kgMessage" severity="warn" :closable="false" class="mt-3">{{ kgMessage }}</Message>
          </SectionCard>
        </div>

        <PageState :empty="!built">
          <template #empty>
            <EmptyState :icon="Database" title="No models yet" text="Upload the Kaggle CSV and rebuild to train the models." />
          </template>
          <template v-if="churn">
            <div class="mb-4 flex flex-wrap items-baseline justify-between gap-2">
              <h2 class="m-0 text-lg font-semibold">Model card</h2>
              <p class="m-0 text-sm text-ink-500">Test set: {{ churn.n_test.toLocaleString() }} members never seen in training</p>
            </div>
            <section class="mb-6 grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-3 3xl:grid-cols-6">
              <KpiTile label="F1 (churn class)" :value="num(churn.test.f1, 3)" :icon="Target" />
              <KpiTile label="PR-AUC" :value="num(churn.test.pr_auc, 3)" :icon="ChartLine" />
              <KpiTile label="Brier score" :value="num(churn.test.brier, 3)" hint="Lower is better" :icon="Gauge" />
              <KpiTile label="Silhouette" :value="num(card.segmentation?.silhouette, 3)" :hint="`k = ${card.segmentation?.k}, stability ARI ${num(card.segmentation?.stability_ari, 2)}`" :icon="Activity" />
              <KpiTile label="Age recall gap" :value="pct(churn.fairness.age_band.recall_gap)" tone="warn" hint="Max − min recall across age bands" :icon="Scale" />
              <KpiTile label="Gender recall gap" :value="pct(churn.fairness.gender.recall_gap)" :icon="Scale" />
            </section>

            <SectionCard title="Model vs baselines" :subtitle="`${churn.model} · threshold ${num(churn.test.threshold, 3)}`" :icon="BrainCircuit" class="mb-6">
              <div class="table-wrap">
                <table class="plain">
                  <thead>
                    <tr>
                      <th scope="col">Model</th>
                      <th v-for="[, label] in METRICS" :key="label" scope="col" class="num">{{ label }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, i) in comparison" :key="row.name" :class="{ best: i === 0 }">
                      <td>{{ row.name }}</td>
                      <td v-for="[key] in METRICS" :key="key" class="num">{{ num(row.m[key] as number, 3) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p class="m-0 mt-4 rounded-lg bg-ink-50 p-3 text-[0.8125rem] leading-relaxed text-ink-600">
                <strong class="text-ink-800">Leakage check.</strong> The suspect features (current-month visits, months to contract end and their
                derivatives) may be measured in the same month as the churn label. The last row shows the model without them.
              </p>
            </SectionCard>

            <div class="mb-6 grid gap-5 lg:grid-cols-2">
              <ChartCard title="Calibration (test set)" subtitle="Predicted vs observed churn rate" :option="calibrationOption" height="300px" />
              <ChartCard title="Segmentation: silhouette by k" subtitle="Cluster quality for each candidate number of segments" :option="silhouetteOption" height="300px" />
            </div>

            <SectionCard title="Fairness (test set)" subtitle="Recall and false-positive rates by group" :icon="Scale">
              <div class="grid gap-6 2xl:grid-cols-2">
                <div v-for="f in fairness" :key="f.attr">
                  <h3 class="m-0 mb-2 flex flex-wrap items-baseline gap-x-3 text-sm font-semibold">
                    {{ f.attr }}
                    <span class="text-xs font-medium text-ink-500">recall gap {{ pct(f.recall_gap) }} · false-positive gap {{ pct(f.fpr_gap) }}</span>
                  </h3>
                  <div class="table-wrap">
                    <table class="plain">
                      <thead>
                        <tr><th scope="col">Group</th><th scope="col" class="num">Members</th><th scope="col" class="num">Churn rate</th><th scope="col" class="num">Recall</th><th scope="col" class="num">Precision</th><th scope="col" class="num">False-positive rate</th></tr>
                      </thead>
                      <tbody>
                        <tr v-for="(g, name) in f.groups" :key="name">
                          <td>{{ name }}</td>
                          <td class="num">{{ g.n }}</td>
                          <td class="num">{{ pct(g.churn_rate) }}</td>
                          <td class="num">{{ pct(g.recall) }}</td>
                          <td class="num">{{ pct(g.precision) }}</td>
                          <td class="num">{{ pct(g.fpr, 1) }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </SectionCard>
          </template>
        </PageState>
      </template>
    </PageState>
  </div>
</template>

<style scoped>
.best td { font-weight: 600; color: var(--color-ink-900); background: color-mix(in srgb, var(--color-brand-50) 60%, transparent); }
:deep(.narrow) {
  width: 6rem;
}
</style>
