<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { CircleCheck, PhoneCall, Target, TrendingDown, UserRoundCheck, Wallet } from 'lucide-vue-next'
import { computed, onMounted } from 'vue'
import { api } from '../api/client'
import type { Dashboard } from '../api/types'
import { riskColors } from '../charts'
import ChartCard from '../components/ChartCard.vue'
import KpiTile from '../components/KpiTile.vue'
import PageHeader from '../components/PageHeader.vue'
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
    tooltip: { trigger: 'axis' },
    grid: { left: 8, right: 16, top: 28, bottom: 32, containLabel: true },
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
        name: 'Members',
        type: 'bar',
        barMaxWidth: 36,
        data: d.risk_distribution.map((b) => ({
          value: b.count,
          itemStyle: { color: b.start >= 0.6 ? riskColors.high : b.start >= 0.3 ? riskColors.medium : riskColors.low },
        })),
      },
    ],
  }
})

const mixOption = computed<EChartsOption | null>(() => {
  const d = data.value
  if (!d) return null
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { bottom: 0 },
    grid: { left: 24, right: 16, top: 8, bottom: 36, containLabel: true },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: d.segment_mix.map((s) => s.segment), inverse: true },
    series: [
      { name: 'Members', type: 'bar', data: d.segment_mix.map((s) => s.size), barGap: '15%' },
      { name: 'High risk', type: 'bar', data: d.segment_mix.map((s) => s.at_risk), itemStyle: { color: riskColors.high } },
    ],
  }
})

const trendOption = computed<EChartsOption | null>(() => {
  const d = data.value
  if (!d?.outcome_trend.length) return null
  return {
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0 },
    grid: { left: 8, right: 16, top: 16, bottom: 36, containLabel: true },
    xAxis: { type: 'category', data: d.outcome_trend.map((w) => date(w.week_start)) },
    yAxis: { type: 'value' },
    series: (['contacted', 'reached', 'retained'] as const).map((k) => ({
      name: k[0].toUpperCase() + k.slice(1),
      type: 'line',
      areaStyle: { opacity: 0.06 },
      data: d.outcome_trend.map((w) => w[k]),
    })),
  }
})
</script>

<template>
  <div class="page">
    <PageHeader title="Dashboard" :subtitle="data ? `Retention at a glance · scores as of ${date(data.as_of)}` : 'Retention at a glance'" />
    <PageState :loading="loading" :error="error" @retry="run">
      <template v-if="data && kpis">
        <section class="mb-6 grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-3 3xl:grid-cols-6" aria-label="Key figures">
          <KpiTile
            label="Members at high risk"
            :value="kpis.members_at_risk.toLocaleString()"
            :hint="`of ${kpis.total_members.toLocaleString()} members`"
            tone="warn"
            :icon="TrendingDown"
          />
          <KpiTile
            label="Monthly revenue at risk"
            :value="money(kpis.revenue_at_risk)"
            hint="Σ churn probability × monthly fee"
            tone="warn"
            :icon="Wallet"
          />
          <KpiTile
            label="Plan coverage"
            :value="pct(kpis.plan_coverage)"
            :hint="kpis.plan_coverage === null ? 'No approved plan yet' : 'High-risk members in the latest approved plan'"
            :icon="Target"
          />
          <KpiTile
            label="Contacted"
            :value="kpis.contacted"
            :hint="kpis.outcome_week ? `Week of ${date(kpis.outcome_week)}` : 'No outcomes logged yet'"
            :icon="PhoneCall"
          />
          <KpiTile label="Reached" :value="kpis.reached" :icon="UserRoundCheck" />
          <KpiTile label="Retained (accepted offer)" :value="kpis.retained" tone="good" :icon="CircleCheck" />
        </section>
        <section class="grid gap-5 lg:grid-cols-2 3xl:grid-cols-3">
          <ChartCard title="Risk distribution" subtitle="Members by calibrated churn probability" :option="riskOption" height="300px" />
          <ChartCard title="Segment mix" subtitle="Segment size and how many are high risk" :option="mixOption" height="300px" />
          <ChartCard
            title="Outcomes by week"
            subtitle="Contacted, reached and retained members"
            :option="trendOption"
            height="300px"
            class="lg:col-span-2 3xl:col-span-1"
            empty-text="No outcomes have been logged yet. They appear here once staff log contacts."
          />
        </section>
      </template>
    </PageState>
  </div>
</template>
