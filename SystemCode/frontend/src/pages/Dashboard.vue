<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { computed, onMounted } from 'vue'
import { api } from '../api/client'
import type { Dashboard } from '../api/types'
import { palette } from '../charts'
import ChartCard from '../components/ChartCard.vue'
import KpiTile from '../components/KpiTile.vue'
import PageState from '../components/PageState.vue'
import { useAsync } from '../composables/useAsync'
import { date, money, pct } from '../format'

const { data, loading, error, run } = useAsync(() => api<Dashboard>('/members/dashboard'))
onMounted(run)

const kpis = computed(() => data.value?.kpis)

const riskOption = computed<EChartsOption | null>(() => {
  const d = data.value
  if (!d) return null
  return {
    color: palette,
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 16, top: 16, bottom: 40 },
    xAxis: {
      type: 'category',
      name: 'Churn probability',
      nameLocation: 'middle',
      nameGap: 28,
      data: d.risk_distribution.map((b) => `${Math.round(b.start * 100)}–${Math.round(b.end * 100)}%`),
    },
    yAxis: { type: 'value', name: 'Members' },
    series: [
      {
        type: 'bar',
        data: d.risk_distribution.map((b) => ({
          value: b.count,
          itemStyle: { color: b.start >= 0.6 ? '#c2475b' : b.start >= 0.3 ? '#e0a339' : '#3a9d6b' },
        })),
      },
    ],
  }
})

const mixOption = computed<EChartsOption | null>(() => {
  const d = data.value
  if (!d) return null
  return {
    color: palette,
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0 },
    grid: { left: 160, right: 16, top: 8, bottom: 40 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: d.segment_mix.map((s) => s.segment) },
    series: [
      { name: 'Members', type: 'bar', data: d.segment_mix.map((s) => s.size) },
      { name: 'High risk', type: 'bar', data: d.segment_mix.map((s) => s.at_risk) },
    ],
  }
})

const trendOption = computed<EChartsOption | null>(() => {
  const d = data.value
  if (!d?.outcome_trend.length) return null
  return {
    color: palette,
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0 },
    grid: { left: 40, right: 16, top: 16, bottom: 40 },
    xAxis: { type: 'category', data: d.outcome_trend.map((w) => date(w.week_start)) },
    yAxis: { type: 'value' },
    series: (['contacted', 'reached', 'retained'] as const).map((k) => ({
      name: k[0].toUpperCase() + k.slice(1),
      type: 'line',
      data: d.outcome_trend.map((w) => w[k]),
    })),
  }
})
</script>

<template>
  <div class="page-head">
    <h2>Dashboard</h2>
    <span v-if="data" class="sub">Scores as of {{ date(data.as_of) }}</span>
  </div>
  <PageState :loading="loading" :error="error" @retry="run">
    <template v-if="data && kpis">
      <section class="grid kpis" aria-label="Key figures">
        <KpiTile
          label="Members at high risk"
          :value="kpis.members_at_risk.toLocaleString()"
          :hint="`of ${kpis.total_members.toLocaleString()} members`"
          tone="warn"
        />
        <KpiTile
          label="Monthly revenue at risk"
          :value="money(kpis.revenue_at_risk)"
          hint="Σ churn probability × monthly fee"
          tone="warn"
        />
        <KpiTile
          label="Plan coverage"
          :value="pct(kpis.plan_coverage)"
          :hint="kpis.plan_coverage === null ? 'No approved plan yet' : 'High-risk members in the latest approved plan'"
        />
        <KpiTile
          label="Contacted"
          :value="kpis.contacted"
          :hint="kpis.outcome_week ? `Week of ${date(kpis.outcome_week)}` : 'No outcomes logged yet'"
        />
        <KpiTile label="Reached" :value="kpis.reached" />
        <KpiTile label="Retained (accepted offer)" :value="kpis.retained" tone="good" />
      </section>
      <section class="grid cols-2">
        <ChartCard title="Risk distribution" :option="riskOption" />
        <ChartCard title="Segment mix" :option="mixOption" />
        <ChartCard
          title="Outcomes by week"
          :option="trendOption"
          empty-text="No outcomes have been logged yet. They appear here once staff log contacts."
        />
      </section>
    </template>
  </PageState>
</template>
