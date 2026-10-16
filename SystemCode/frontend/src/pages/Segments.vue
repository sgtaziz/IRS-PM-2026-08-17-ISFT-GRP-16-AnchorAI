<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { ArrowRight } from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/client'
import type { SegmentCard } from '../api/types'
import { CHART_THEME } from '../charts'
import PageHeader from '../components/PageHeader.vue'
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
    color: ['#1f60ea', '#cbd2de'],
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { bottom: 0 },
    grid: { left: 20, right: 12, top: 4, bottom: 32, containLabel: true },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: keys.map((k) => PROFILE_LABELS[k]), inverse: true },
    series: [
      { name: 'This segment', type: 'bar', barGap: '10%', data: keys.map((k) => +scaled(k, s.profile[k]).toFixed(2)) },
      { name: 'All members', type: 'bar', data: keys.map((k) => +scaled(k, mean(k)).toFixed(2)) },
    ],
  }
}

const churnTone = (rate: number) =>
  rate >= 0.4 ? 'bg-danger-soft text-[#b4183a]' : rate >= 0.2 ? 'bg-warn-soft text-[#9a5c00]' : 'bg-success-soft text-[#0b7a53]'

function open(s: SegmentCard) {
  router.push({ path: '/members', query: { segment: s.name } })
}
</script>

<template>
  <div class="page">
    <PageHeader title="Segments" subtitle="K-means clusters on member behaviour, ordered from highest to lowest churn. Open one to see its members." />
    <PageState :loading="loading" :error="error" :empty="data?.length === 0" @retry="run">
      <div v-if="data" class="grid gap-5 lg:grid-cols-2 4xl:grid-cols-4">
        <article
          v-for="s in data"
          :key="s.segment_id"
          class="segment group"
          role="link"
          tabindex="0"
          :aria-label="`Open members in ${s.name}`"
          @click="open(s)"
          @keydown.enter="open(s)"
        >
          <header class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <h2 class="m-0 text-lg font-semibold text-ink-900">{{ s.name }}</h2>
              <p class="m-0 mt-1 text-sm leading-relaxed text-ink-500">{{ s.description }}</p>
            </div>
            <span class="shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold whitespace-nowrap" :class="churnTone(s.churn_rate)">
              {{ pct(s.churn_rate) }} churn
            </span>
          </header>
          <dl class="stats">
            <div><dt>Members</dt><dd>{{ s.size.toLocaleString() }}</dd></div>
            <div><dt>Churn rate</dt><dd>{{ pct(s.churn_rate) }}</dd></div>
            <div><dt>High risk now</dt><dd>{{ s.at_risk.toLocaleString() }}</dd></div>
            <div><dt>Monthly revenue</dt><dd>{{ money(s.monthly_revenue) }}</dd></div>
          </dl>
          <p class="m-0 text-xs font-semibold tracking-wider text-ink-500 uppercase">Profile vs all members</p>
          <VChart :option="profileOption(s, data)" :theme="CHART_THEME" autoresize style="height: 250px" />
          <span class="mt-auto inline-flex items-center gap-1.5 text-sm font-semibold text-brand-700">
            View {{ s.size.toLocaleString() }} members
            <ArrowRight :size="16" class="transition group-hover:translate-x-0.5" aria-hidden="true" />
          </span>
        </article>
      </div>
    </PageState>
  </div>
</template>

<style scoped>
.segment {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem;
  background: #fff;
  border: 1px solid var(--color-ink-200);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition: box-shadow 0.15s, border-color 0.15s;
}
.segment:hover,
.segment:focus-visible {
  border-color: var(--color-brand-300);
  box-shadow: var(--shadow-raised);
  outline: none;
}
.segment:focus-visible { box-shadow: 0 0 0 3px var(--color-brand-200); }
.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.5rem;
  margin: 0;
  padding: 0.85rem 1rem;
  background: var(--color-ink-50);
  border-radius: 0.75rem;
}
@media (max-width: 520px) { .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.stats dt { font-size: 0.75rem; color: var(--color-ink-500); }
.stats dd { margin: 0.15rem 0 0; font-weight: 600; font-size: 1.05rem; color: var(--color-ink-900); font-variant-numeric: tabular-nums; }
</style>
