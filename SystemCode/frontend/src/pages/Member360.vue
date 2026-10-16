<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { Activity, ArrowLeft, CalendarDays, ChartBar, Dumbbell, History, Hourglass, Layers, Network, ScrollText, Sparkles, TrendingDown, UserRound, Wallet } from 'lucide-vue-next'
import Button from 'primevue/button'
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/client'
import type { EgoGraph as EgoGraphData, MemberDetail, RuleOutcome } from '../api/types'
import { riskColors } from '../charts'
import ChartCard from '../components/ChartCard.vue'
import EgoGraph from '../components/EgoGraph.vue'
import EmptyState from '../components/EmptyState.vue'
import KpiTile from '../components/KpiTile.vue'
import PageState from '../components/PageState.vue'
import RiskBadge from '../components/RiskBadge.vue'
import RuleTrace from '../components/RuleTrace.vue'
import SectionCard from '../components/SectionCard.vue'
import { useAsync } from '../composables/useAsync'
import { date, money, num, pct, probability } from '../format'
import { channelLabel } from '../labels'
import { useAuthStore } from '../stores/auth'
import { useGlossaryStore } from '../stores/glossary'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const glossary = useGlossaryStore()
onMounted(glossary.load)
const memberId = computed(() => String(route.params.id))

const detail = useAsync((id: string) => api<MemberDetail>(`/members/${id}`))

// Stream B's panels; until their endpoints exist the panel says so instead of failing.
const ruleTrace = useAsync((id: string) => api<RuleOutcome>(`/rules/trace/${encodeURIComponent(id)}`))
const similarCases = useAsync((id: string) => api<unknown[]>(`/plan/similar-cases/${id}`))
const egoGraph = useAsync((id: string) => api<EgoGraphData>(`/graph/ego/${encodeURIComponent(id)}`))
const contacts = useAsync((id: string) => api<unknown[]>(`/outcomes?member_id=${encodeURIComponent(id)}`))
const panels = [
  { title: 'Similar past cases', owner: 'Stream B', icon: Layers, state: similarCases },
  { title: 'Contact and outcome history', owner: 'Stream B', icon: History, state: contacts },
]

function load() {
  const id = memberId.value
  detail.run(id)
  ruleTrace.run(id)
  egoGraph.run(id)
  for (const p of panels) p.state.run(id)
}
watch(memberId, load, { immediate: true })

const d = computed(() => detail.data.value)
const label = (key: string) => d.value?.feature_labels[key] ?? key

const driverOption = computed<EChartsOption | null>(() => {
  const drivers = d.value?.score.top_drivers
  if (!drivers?.length) return null
  const rows = [...drivers].reverse()
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (v) => `${Number(v) > 0 ? '+' : ''}${Number(v).toFixed(2)} log-odds`,
    },
    grid: { left: 24, right: 24, top: 8, bottom: 32, containLabel: true },
    xAxis: { type: 'value', name: '← keeps · churn →', nameLocation: 'middle', nameGap: 22 },
    yAxis: { type: 'category', data: rows.map(([k]) => label(k)) },
    series: [
      {
        type: 'bar',
        barMaxWidth: 18,
        data: rows.map(([, v]) => ({ value: +v.toFixed(3), itemStyle: { color: v > 0 ? riskColors.high : riskColors.low } })),
      },
    ],
  }
})

const profileRows = computed(() => {
  const m = d.value
  if (!m) return []
  return Object.entries(m.profile).map(([key, value]) => ({
    key,
    label: label(key),
    value,
    segment: m.segment_averages[key],
  }))
})

const fmt = (key: string, v: number | undefined) => {
  if (v === undefined) return '—'
  if (['group_visits', 'near_location', 'partner', 'promo_friends'].includes(key)) return v >= 0.5 ? 'Yes' : 'No'
  if (key === 'avg_additional_charges_total') return money(v)
  if (key === 'trend_ratio') return `${num(v)}×`
  return Number.isInteger(v) ? String(v) : num(v)
}
const fmtAvg = (key: string, v: number | undefined) =>
  v === undefined ? '—' : ['group_visits', 'near_location', 'partner', 'promo_friends'].includes(key) ? pct(v) : fmt(key, v)

function ask() {
  router.push({ path: '/assistant', query: { member: memberId.value } })
}
</script>

<template>
  <div class="page">
    <PageState :loading="detail.loading.value" :error="detail.error.value" @retry="load">
      <template v-if="d">
        <header class="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div class="flex min-w-0 items-center gap-4">
            <span class="grid size-14 shrink-0 place-items-center rounded-2xl bg-brand-50 text-brand-600 ring-1 ring-brand-100">
              <UserRound :size="28" aria-hidden="true" />
            </span>
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
                <h1 class="m-0 text-2xl font-semibold tracking-tight">Member {{ d.score.member_id }}</h1>
                <RiskBadge :band="d.risk_band" :prob="d.score.churn_prob" />
              </div>
              <p class="m-0 mt-1 flex flex-wrap items-center gap-x-2 text-[0.9375rem] text-ink-500">
                <span class="font-medium text-ink-700">{{ d.score.segment }}</span>
                <span aria-hidden="true">·</span><span>Club {{ d.club_id }}</span>
                <span aria-hidden="true">·</span><span>Scored {{ date(d.score.as_of) }}</span>
              </p>
            </div>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <Button
              v-if="auth.hasRole(['manager', 'admin'])"
              label="Back to members"
              severity="secondary"
              text
              @click="router.push('/members')"
            >
              <template #icon><ArrowLeft :size="16" /></template>
            </Button>
            <Button label="Ask the assistant about this member" @click="ask">
              <template #icon><Sparkles :size="16" /></template>
            </Button>
          </div>
        </header>

        <section class="mb-6 grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4" aria-label="Key figures">
          <KpiTile label="Churn probability" :value="probability(d.score.churn_prob, 1)" :tone="d.risk_band === 'high' ? 'warn' : 'default'" hint="Calibrated, next month" :icon="TrendingDown" />
          <KpiTile label="Monthly value" :value="money(d.score.monthly_value)" :icon="Wallet" />
          <KpiTile label="Months as member" :value="d.profile.lifetime ?? '—'" :icon="CalendarDays" />
          <KpiTile label="Visit trend" :value="`${num(d.profile.trend_ratio)}×`" hint="This month vs lifetime average" :icon="Activity" />
        </section>

        <div class="grid items-start gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
          <div class="flex min-w-0 flex-col gap-5">
            <ChartCard
              title="Why this risk score"
              subtitle="Top drivers from the churn model. Red pushes towards churn, green keeps the member."
              :icon="ChartBar"
              :option="driverOption"
              empty-text="No drivers recorded."
              height="300px"
            />

            <SectionCard title="Profile vs segment" :subtitle="`Compared with the average ${d.score.segment} member`" :icon="UserRound">
              <div class="table-wrap">
                <table class="plain">
                  <thead>
                    <tr><th scope="col">Feature</th><th scope="col" class="num">Member</th><th scope="col" class="num">Segment average</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="r in profileRows" :key="r.key">
                      <td>{{ r.label }}</td>
                      <td class="num font-semibold text-ink-900">{{ fmt(r.key, r.value) }}</td>
                      <td class="num text-ink-500">{{ fmtAvg(r.key, r.segment) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </SectionCard>

            <div class="grid gap-5 lg:grid-cols-2">
              <SectionCard title="Classes attended" :icon="Dumbbell">
                <PageState :empty="!d.attendance.length" empty-text="Does not attend group classes.">
                  <ul class="m-0 flex list-none flex-col divide-y divide-ink-100 p-0">
                    <li v-for="a in d.attendance" :key="a.class_id" class="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
                      <div class="min-w-0">
                        <p class="m-0 text-sm font-semibold text-ink-800">{{ a.class_name }}</p>
                        <p class="m-0 text-xs text-ink-500">with {{ a.instructor_name }}</p>
                      </div>
                      <span class="shrink-0 text-sm text-ink-600 tabular-nums">{{ num(a.visits_per_week) }} / week</span>
                    </li>
                  </ul>
                </PageState>
              </SectionCard>

              <SectionCard title="Past retention contacts" :icon="History">
                <PageState :empty="!d.interventions.length" empty-text="No past retention contacts.">
                  <ul class="m-0 flex list-none flex-col divide-y divide-ink-100 p-0">
                    <li v-for="(i, n) in d.interventions" :key="n" class="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
                      <div class="min-w-0">
                        <p class="m-0 text-sm font-semibold text-ink-800">{{ i.treated && i.offer_id ? glossary.offer(i.offer_id) : 'No offer (control)' }}</p>
                        <p class="m-0 text-xs text-ink-500">Week of {{ date(i.week_start) }}<template v-if="i.channel"> · {{ channelLabel(i.channel) }}</template></p>
                      </div>
                      <span class="shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="i.stayed ? 'bg-success-soft text-[#0b7a53]' : 'bg-danger-soft text-[#b4183a]'">
                        {{ i.stayed ? 'Stayed' : 'Left' }}
                      </span>
                    </li>
                  </ul>
                </PageState>
              </SectionCard>
            </div>

            <SectionCard title="Knowledge-graph neighbourhood" subtitle="Club, classes, instructors and events around this member" :icon="Network">
              <PageState
                :loading="egoGraph.loading.value"
                :empty="!!egoGraph.error.value || !egoGraph.data.value"
                :empty-text="egoGraph.error.value ?? 'Not in the knowledge graph.'"
              >
                <EgoGraph v-if="egoGraph.data.value" :graph="egoGraph.data.value" height="380px" />
              </PageState>
            </SectionCard>
          </div>

          <div class="flex min-w-0 flex-col gap-5">
            <SectionCard title="Segment" :icon="Layers">
              <p class="m-0 mb-1.5 text-base font-semibold text-ink-900">{{ d.score.segment }}</p>
              <p class="m-0 text-sm leading-relaxed text-ink-600">{{ d.segment_description }}</p>
            </SectionCard>

            <SectionCard title="Rule trace" subtitle="What the rule base concludes and offers" :icon="ScrollText">
              <PageState :loading="ruleTrace.loading.value" :error="ruleTrace.error.value" @retry="ruleTrace.run(memberId)">
                <RuleTrace v-if="ruleTrace.data.value" :outcome="ruleTrace.data.value" />
              </PageState>
            </SectionCard>


            <SectionCard v-for="p in panels" :key="p.title" :title="p.title" :icon="p.icon">
              <PageState :loading="p.state.loading.value" :empty="!!p.state.error.value || !p.state.data.value">
                <template #empty>
                  <EmptyState :icon="Hourglass" compact title="Coming soon" :text="`This panel arrives with ${p.owner}'s planning work.`" />
                </template>
                <pre class="raw">{{ JSON.stringify(p.state.data.value, null, 2) }}</pre>
              </PageState>
            </SectionCard>
          </div>
        </div>
      </template>
    </PageState>
  </div>
</template>

<style scoped>
.raw {
  max-height: 240px;
  overflow: auto;
  margin: 0;
  padding: 0.75rem;
  font-size: 0.8rem;
  background: var(--color-ink-50);
  border-radius: 0.5rem;
}
</style>
