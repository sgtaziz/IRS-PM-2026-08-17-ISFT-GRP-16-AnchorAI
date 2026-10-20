<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { Activity, BarChart3, Info, Play, SlidersHorizontal, Trophy } from 'lucide-vue-next'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import Slider from 'primevue/slider'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { Comparison, PlanJob, PlannerResult } from '../api/types'
import { palette } from '../charts'
import ChartCard from '../components/ChartCard.vue'
import PageHeader from '../components/PageHeader.vue'
import SectionCard from '../components/SectionCard.vue'
import { errorMessage } from '../composables/useAsync'
import { money, num } from '../format'

// W17: what-if budgets and staff hours, every planner on the same week, scored by the planner's own estimates.
const NAMES: Record<string, string> = {
  'contact-all': 'Contact everyone',
  'risk-top-k': 'Riskiest first',
  'greedy-uplift': 'Greedy (uplift)',
  exact: 'Exact (CP-SAT)',
  ga: 'Genetic algorithm',
}
const ORDER = ['contact-all', 'risk-top-k', 'greedy-uplift', 'exact', 'ga']

const budget = ref(1500)
const staffHours = ref(36)
const job = ref<PlanJob | null>(null)
const result = ref<Comparison | null>(null)
const running = ref(false)
const error = ref<string | null>(null)
let timer: ReturnType<typeof setTimeout> | undefined
onBeforeUnmount(() => clearTimeout(timer))

// Show the last comparison if one finished earlier (the job runner keeps it in memory).
onMounted(async () => {
  try {
    const last = await api<PlanJob>('/plan/jobs/current')
    if (last.kind === 'compare' && last.state === 'done' && last.comparison) {
      result.value = last.comparison
      budget.value = last.comparison.request.budget
      staffHours.value = last.comparison.request.staff_minutes / 60
    }
  } catch {
    // No earlier comparison to show; the page still works.
  }
})

async function poll() {
  try {
    job.value = await api<PlanJob>('/plan/jobs/current')
    if (job.value.state === 'running') {
      timer = setTimeout(poll, 700)
      return
    }
    if (job.value.state === 'failed') error.value = job.value.error ?? 'The comparison failed'
    else result.value = job.value.comparison
  } catch (e) {
    error.value = errorMessage(e)
  }
  running.value = false
}

async function run() {
  running.value = true
  error.value = null
  const as_of = new Date()
  const request = {
    as_of: `${as_of.getFullYear()}-${String(as_of.getMonth() + 1).padStart(2, '0')}-${String(as_of.getDate()).padStart(2, '0')}`,
    budget: budget.value,
    staff_minutes: Math.round(staffHours.value * 60),
  }
  try {
    job.value = await api<PlanJob>('/plan/compare', { method: 'POST', body: JSON.stringify(request) })
    poll()
  } catch (e) {
    error.value = errorMessage(e)
    running.value = false
  }
}

const rows = computed<(PlannerResult & { name: string; perThousand: number | null; perHour: number | null })[]>(() =>
  [...(result.value?.planners ?? [])]
    .sort((a, b) => ORDER.indexOf(a.planner) - ORDER.indexOf(b.planner))
    .map((r) => ({
      ...r,
      name: NAMES[r.planner] ?? r.planner,
      perThousand: r.spend ? (1000 * r.expected_extra_members) / r.spend : null,
      perHour: r.staff_minutes ? (60 * r.expected_extra_members) / r.staff_minutes : null,
    })),
)
const best = computed(() => [...rows.value].sort((a, b) => b.full_value - a.full_value)[0]?.planner ?? null)

const barOption = computed<EChartsOption | null>(() =>
  rows.value.length
    ? {
        tooltip: { trigger: 'axis' },
        grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
        xAxis: { type: 'value', name: 'Extra members expected to stay', nameLocation: 'middle', nameGap: 28 },
        yAxis: { type: 'category', data: rows.value.map((r) => r.name), inverse: true },
        series: [
          {
            type: 'bar',
            barMaxWidth: 26,
            data: rows.value.map((r, i) => ({ value: +r.expected_extra_members.toFixed(1), itemStyle: { color: palette[i % palette.length] } })),
            label: { show: true, position: 'right', formatter: '{c}' },
          },
        ],
      }
    : null,
)

const convergenceOption = computed<EChartsOption | null>(() => {
  const log = result.value?.ga_convergence ?? []
  if (!log.length) return null
  const greedy = rows.value.find((r) => r.planner === 'greedy-uplift')?.full_value
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0 },
    grid: { left: 8, right: 16, top: 32, bottom: 32, containLabel: true },
    xAxis: { type: 'value', name: 'Generation', nameLocation: 'middle', nameGap: 26 },
    yAxis: { type: 'value', name: 'Plan value ($)', scale: true },
    series: [
      {
        name: 'Best plan',
        type: 'line',
        showSymbol: false,
        data: log.map((g) => [g.generation, g.best]),
        color: palette[0],
        // The greedy plan seeds the GA, so its value is where the curve starts from.
        markLine: greedy === undefined ? undefined : { symbol: 'none', data: [{ yAxis: greedy }], lineStyle: { type: 'dashed' }, label: { formatter: 'Greedy' } },
      },
      { name: 'Population average', type: 'line', showSymbol: false, data: log.map((g) => [g.generation, g.mean]), color: palette[5] },
    ],
  }
})
</script>

<template>
  <div class="page">
    <PageHeader title="Scenarios" subtitle="What if the budget or staff hours changed? Every planner on the same week, side by side." />

    <SectionCard title="Set the week's limits" :icon="SlidersHorizontal">
      <form class="grid gap-6 px-5 pb-5 pt-3 md:grid-cols-[1fr_1fr_auto] md:items-end" @submit.prevent="run">
        <label class="field">
          <span>Weekly budget</span>
          <InputNumber v-model="budget" :min="0" :max="10000" mode="currency" currency="USD" :max-fraction-digits="0" />
          <Slider v-model="budget" :min="0" :max="5000" :step="100" class="mt-3" aria-label="Weekly budget" />
        </label>
        <label class="field">
          <span>Staff hours</span>
          <InputNumber v-model="staffHours" :min="0" :max="400" suffix=" h" />
          <Slider v-model="staffHours" :min="0" :max="150" :step="2" class="mt-3" aria-label="Staff hours" />
        </label>
        <Button type="submit" label="Run comparison" :loading="running">
          <template #icon><Play :size="15" /></template>
        </Button>
      </form>
      <div v-if="running && job" class="mx-5 mb-5 flex flex-col gap-1.5" role="status" aria-live="polite">
        <span class="text-sm text-ink-600">Running all five planners… the genetic algorithm takes up to a minute</span>
        <ProgressBar :value="Math.round(job.progress * 100)" :show-value="false" style="height: 0.5rem" />
      </div>
      <Message v-if="error" severity="error" class="mx-5 mb-5">{{ error }}</Message>
    </SectionCard>

    <template v-if="result">
      <Message severity="info" class="mt-6">
        <span class="flex items-start gap-2">
          <Info :size="16" class="mt-0.5 shrink-0" />
          <span>
            Results for {{ money(result.request.budget) }} and {{ num(result.request.staff_minutes / 60, 0) }} staff hours, scored with the
            planner's own uplift estimates (case-based reasoning), not observed outcomes. Nothing here is saved or sent to staff.
          </span>
        </span>
      </Message>

      <SectionCard class="mt-6" title="Planners compared" :icon="Trophy" flush>
        <DataTable :value="rows" data-key="planner" scrollable>
          <Column field="name" header="Planner">
            <template #body="{ data }">
              <span class="font-medium" :class="{ 'text-brand-700': data.planner === best }">{{ data.name }}</span>
              <span v-if="data.planner === best" class="ml-2 rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-700">best value</span>
              <span v-if="!data.feasible" class="ml-2 text-xs text-danger">breaks a limit</span>
            </template>
          </Column>
          <Column field="contacts" header="Contacts" />
          <Column header="Spend"><template #body="{ data }">{{ money(data.spend) }}</template></Column>
          <Column header="Staff time"><template #body="{ data }">{{ num(data.staff_minutes / 60, 1) }} h</template></Column>
          <Column header="Extra members"><template #body="{ data }">{{ num(data.expected_extra_members, 1) }}</template></Column>
          <Column header="Per $1,000"><template #body="{ data }">{{ num(data.perThousand, 1) }}</template></Column>
          <Column header="Per staff hour"><template #body="{ data }">{{ num(data.perHour, 2) }}</template></Column>
          <Column header="Value"><template #body="{ data }">{{ money(data.full_value) }}</template></Column>
        </DataTable>
      </SectionCard>

      <div class="mt-6 grid gap-6 xl:grid-cols-2">
        <ChartCard title="Extra members expected to stay" :icon="BarChart3" :option="barOption" height="260px" />
        <ChartCard
          title="How the genetic algorithm improved"
          subtitle="Value of the best plan in each generation, starting from the greedy plan."
          :icon="Activity"
          :option="convergenceOption"
          height="260px"
        />
      </div>
    </template>
  </div>
</template>
