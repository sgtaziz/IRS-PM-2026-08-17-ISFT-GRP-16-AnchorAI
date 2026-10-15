<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import Card from 'primevue/card'
import VChart from 'vue-echarts'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/client'
import type { SegmentCard } from '../api/types'
import { palette } from '../charts'
import PageState from '../components/PageState.vue'
import { useAsync } from '../composables/useAsync'
import { money, pct } from '../format'

const PROFILE_LABELS: Record<string, string> = {
  lifetime: 'Months as member',
  avg_class_frequency_total: 'Visits / week',
  trend_ratio: 'Visit trend',
  contract_period: 'Contract months',
  avg_additional_charges_total: 'Extra spend ($100s)',
  age: 'Age (decades)',
  group_visits: 'Group classes',
}

const router = useRouter()
const { data, loading, error, run } = useAsync(() => api<SegmentCard[]>('/members/segments'))
onMounted(run)

function scaled(key: string, value: number) {
  if (key === 'avg_additional_charges_total') return value / 100
  if (key === 'age') return value / 10
  return value
}

function profileOption(s: SegmentCard, all: SegmentCard[]): EChartsOption {
  const keys = Object.keys(PROFILE_LABELS).filter((k) => k in s.profile)
  const mean = (k: string) => all.reduce((acc, x) => acc + x.profile[k] * x.size, 0) / all.reduce((a, x) => a + x.size, 0)
  return {
    color: palette,
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0 },
    grid: { left: 120, right: 12, top: 4, bottom: 32 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: keys.map((k) => PROFILE_LABELS[k]) },
    series: [
      { name: 'This segment', type: 'bar', data: keys.map((k) => +scaled(k, s.profile[k]).toFixed(2)) },
      { name: 'All members', type: 'bar', data: keys.map((k) => +scaled(k, mean(k)).toFixed(2)) },
    ],
  }
}

function open(s: SegmentCard) {
  router.push({ path: '/members', query: { segment: s.name } })
}
</script>

<template>
  <div class="page-head">
    <h2>Segments</h2>
    <span class="sub">K-means on behaviour; ordered from highest to lowest churn</span>
  </div>
  <PageState :loading="loading" :error="error" :empty="data?.length === 0" @retry="run">
    <div v-if="data" class="grid cols-2">
      <Card
        v-for="s in data"
        :key="s.segment_id"
        class="segment"
        role="link"
        tabindex="0"
        :aria-label="`Open members in ${s.name}`"
        @click="open(s)"
        @keydown.enter="open(s)"
      >
        <template #title>{{ s.name }}</template>
        <template #subtitle>{{ s.description }}</template>
        <template #content>
          <dl class="stats">
            <div><dt>Members</dt><dd>{{ s.size.toLocaleString() }}</dd></div>
            <div><dt>Churn rate</dt><dd>{{ pct(s.churn_rate) }}</dd></div>
            <div><dt>High risk now</dt><dd>{{ s.at_risk.toLocaleString() }}</dd></div>
            <div><dt>Monthly revenue</dt><dd>{{ money(s.monthly_revenue) }}</dd></div>
          </dl>
          <VChart :option="profileOption(s, data)" autoresize style="height: 240px" />
          <span class="link">View members →</span>
        </template>
      </Card>
    </div>
  </PageState>
</template>

<style scoped>
.segment {
  cursor: pointer;
  transition: box-shadow 0.15s;
}
.segment:hover,
.segment:focus-visible {
  box-shadow: 0 0 0 2px var(--accent);
  outline: none;
}
.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.5rem;
  margin: 0 0 0.5rem;
}
.stats dt {
  font-size: 0.8rem;
  color: var(--muted);
}
.stats dd {
  margin: 0;
  font-weight: 700;
  font-size: 1.1rem;
}
.link {
  color: var(--accent);
  font-weight: 600;
}
</style>
