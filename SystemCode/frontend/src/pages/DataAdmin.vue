<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import Button from 'primevue/button'
import Card from 'primevue/card'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { BuildStatus, DataOverview, Fairness, Metrics } from '../api/types'
import { palette } from '../charts'
import ChartCard from '../components/ChartCard.vue'
import ConfirmAction from '../components/ConfirmAction.vue'
import KpiTile from '../components/KpiTile.vue'
import PageState from '../components/PageState.vue'
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
    color: palette,
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 16, top: 16, bottom: 36 },
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
    color: palette,
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    grid: { left: 48, right: 16, top: 16, bottom: 56 },
    xAxis: { type: 'value', name: 'Predicted', nameLocation: 'middle', nameGap: 24, min: 0, max: 1 },
    yAxis: { type: 'value', name: 'Observed', min: 0, max: 1 },
    series: [
      { name: 'Calibrated', type: 'line', data: pairs(cal.calibrated) },
      { name: 'Before calibration', type: 'line', data: pairs(cal.uncalibrated), lineStyle: { type: 'dashed' } },
      { name: 'Perfect', type: 'line', data: [[0, 0], [1, 1]], symbol: 'none', lineStyle: { color: '#9aa7b8' } },
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

const stateSeverity = (s: string | undefined) =>
  ({ running: 'info', done: 'success', failed: 'danger' })[s ?? ''] ?? 'secondary'
</script>

<template>
  <div class="page-head">
    <h2>Data & models</h2>
    <span v-if="card?.built_at" class="sub">Built {{ dateTime(card.built_at) }} · seed {{ card.seed }}</span>
  </div>
  <PageState :loading="overview.loading.value && !card" :error="overview.error.value" @retry="load">
    <template v-if="card">
      <div class="grid cols-2 block">
        <Card>
          <template #title>Source data</template>
          <template #content>
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
            <div class="upload">
              <label for="raw-upload" class="field">
                <span>Replace with a new Kaggle CSV</span>
                <input id="raw-upload" ref="fileInput" type="file" accept=".csv,text/csv" :disabled="uploading" @change="upload" />
              </label>
            </div>
          </template>
        </Card>
        <Card>
          <template #title>Rebuild</template>
          <template #content>
            <p class="muted">
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
                size="large"
                :disabled="running"
                message="Rebuild all data tables and models? Other streams' results change if the seed changes."
                @confirm="rebuild"
              />
              <Button label="Rebuild knowledge graph" severity="secondary" outlined @click="rebuildKg" />
            </div>
            <p>
              Status:
              <Tag :severity="stateSeverity(build?.state)" :value="build?.state ?? 'idle'" />
              <span v-if="build?.finished_at" class="muted"> · finished {{ dateTime(build.finished_at) }}</span>
            </p>
            <ProgressBar v-if="running" mode="indeterminate" style="height: 6px" aria-label="Rebuild in progress" />
            <Message v-if="build?.state === 'failed'" severity="error" :closable="false">{{ build.error }}</Message>
            <Message v-if="kgMessage" severity="warn" :closable="false">{{ kgMessage }}</Message>
          </template>
        </Card>
      </div>

      <PageState :empty="!built" empty-text="No models yet. Upload the Kaggle CSV and rebuild.">
        <template v-if="churn">
          <h3>Churn model (test set, {{ churn.n_test }} members never seen in training)</h3>
          <section class="grid kpis">
            <KpiTile label="F1 (churn class)" :value="num(churn.test.f1, 3)" />
            <KpiTile label="PR-AUC" :value="num(churn.test.pr_auc, 3)" />
            <KpiTile label="Brier score" :value="num(churn.test.brier, 3)" hint="Lower is better" />
            <KpiTile label="Silhouette" :value="num(card.segmentation?.silhouette, 3)" :hint="`k = ${card.segmentation?.k}, stability ARI ${num(card.segmentation?.stability_ari, 2)}`" />
            <KpiTile label="Age recall gap" :value="pct(churn.fairness.age_band.recall_gap)" tone="warn" hint="Max − min recall across age bands" />
            <KpiTile label="Gender recall gap" :value="pct(churn.fairness.gender.recall_gap)" />
          </section>

          <Card class="block">
            <template #title>Model vs baselines</template>
            <template #subtitle>{{ churn.model }} · threshold {{ num(churn.test.threshold, 3) }}</template>
            <template #content>
              <div class="scroll">
                <table class="plain">
                  <thead>
                    <tr>
                      <th scope="col">Model</th>
                      <th v-for="[, label] in METRICS" :key="label" scope="col">{{ label }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="row in comparison" :key="row.name">
                      <td>{{ row.name }}</td>
                      <td v-for="[key] in METRICS" :key="key">{{ num(row.m[key] as number, 3) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p class="muted note">
                Leakage check: the suspect features (current-month visits, months to contract end and their
                derivatives) may be measured in the same month as the churn label. The last row shows the model without them.
              </p>
            </template>
          </Card>

          <div class="grid cols-2 block">
            <ChartCard title="Calibration (test set)" :option="calibrationOption" />
            <ChartCard title="Segmentation: silhouette by k" :option="silhouetteOption" />
          </div>

          <Card>
            <template #title>Fairness (test set)</template>
            <template #content>
              <div v-for="f in fairness" :key="f.attr" class="fair">
                <h4>{{ f.attr }} · recall gap {{ pct(f.recall_gap) }} · false-positive gap {{ pct(f.fpr_gap) }}</h4>
                <table class="plain">
                  <thead>
                    <tr><th scope="col">Group</th><th scope="col">Members</th><th scope="col">Churn rate</th><th scope="col">Recall</th><th scope="col">Precision</th><th scope="col">False-positive rate</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="(g, name) in f.groups" :key="name">
                      <td>{{ name }}</td>
                      <td>{{ g.n }}</td>
                      <td>{{ pct(g.churn_rate) }}</td>
                      <td>{{ pct(g.recall) }}</td>
                      <td>{{ pct(g.precision) }}</td>
                      <td>{{ pct(g.fpr, 1) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </Card>
        </template>
      </PageState>
    </template>
  </PageState>
</template>

<style scoped>
.block {
  margin-bottom: 1rem;
}
.upload {
  margin-top: 1rem;
}
.note {
  font-size: 0.85rem;
}
.scroll {
  overflow-x: auto;
}
.fair h4 {
  margin: 0.75rem 0 0.25rem;
}
:deep(.narrow) {
  width: 6rem;
}
</style>
