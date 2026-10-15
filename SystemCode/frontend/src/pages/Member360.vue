<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/client'
import type { MemberDetail } from '../api/types'
import ChartCard from '../components/ChartCard.vue'
import KpiTile from '../components/KpiTile.vue'
import PageState from '../components/PageState.vue'
import RiskBadge from '../components/RiskBadge.vue'
import { useAsync } from '../composables/useAsync'
import { date, money, num, pct, probability } from '../format'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const memberId = computed(() => String(route.params.id))

const detail = useAsync((id: string) => api<MemberDetail>(`/members/${id}`))

// Panels owned by Streams B and C; until their endpoints exist the panel says so instead of failing.
const ruleTrace = useAsync((id: string) => api<unknown[]>(`/rules/trace/${id}`))
const similarCases = useAsync((id: string) => api<unknown[]>(`/plan/similar-cases/${id}`))
const egoGraph = useAsync((id: string) => api<unknown>(`/graph/ego/${id}`))
const contacts = useAsync((id: string) => api<unknown[]>(`/outcomes?member_id=${encodeURIComponent(id)}`))
const panels = [
  { title: 'Rule trace', owner: 'Stream C', state: ruleTrace },
  { title: 'Similar past cases', owner: 'Stream B', state: similarCases },
  { title: 'Knowledge-graph neighbourhood', owner: 'Stream C', state: egoGraph },
  { title: 'Contact and outcome history', owner: 'Stream B', state: contacts },
]

function load() {
  const id = memberId.value
  detail.run(id)
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
    grid: { left: 210, right: 24, top: 8, bottom: 32 },
    xAxis: { type: 'value', name: '← keeps · churn →', nameLocation: 'middle', nameGap: 22 },
    yAxis: { type: 'category', data: rows.map(([k]) => label(k)) },
    series: [
      {
        type: 'bar',
        data: rows.map(([, v]) => ({ value: +v.toFixed(3), itemStyle: { color: v > 0 ? '#c2475b' : '#3a9d6b' } })),
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
  <PageState :loading="detail.loading.value" :error="detail.error.value" @retry="load">
    <template v-if="d">
      <div class="page-head">
        <div>
          <h2>Member {{ d.score.member_id }}</h2>
          <span class="sub">{{ d.score.segment }} · Club {{ d.club_id }} · scored {{ date(d.score.as_of) }}</span>
        </div>
        <div class="actions">
          <RiskBadge :band="d.risk_band" :prob="d.score.churn_prob" />
          <Button label="Ask the assistant about this member" size="small" @click="ask" />
          <Button
            v-if="auth.hasRole(['manager', 'admin'])"
            label="Back to members"
            size="small"
            severity="secondary"
            text
            @click="router.push('/members')"
          />
        </div>
      </div>

      <section class="grid kpis">
        <KpiTile label="Churn probability" :value="probability(d.score.churn_prob, 1)" :tone="d.risk_band === 'high' ? 'warn' : 'default'" hint="Calibrated, next month" />
        <KpiTile label="Monthly value" :value="money(d.score.monthly_value)" />
        <KpiTile label="Months as member" :value="d.profile.lifetime ?? '—'" />
        <KpiTile label="Visit trend" :value="`${num(d.profile.trend_ratio)}×`" hint="This month vs lifetime average" />
      </section>

      <section class="grid cols-2">
        <ChartCard title="Why this risk score" :option="driverOption" empty-text="No drivers recorded.">
          <p class="muted note">
            Top drivers from the churn model. Red bars push towards churn, green bars keep the member.
          </p>
        </ChartCard>

        <Card>
          <template #title>Segment</template>
          <template #content>
            <p><Tag :value="d.score.segment" /></p>
            <p class="muted">{{ d.segment_description }}</p>
          </template>
        </Card>

        <Card>
          <template #title>Profile vs segment</template>
          <template #content>
            <table class="plain">
              <thead>
                <tr><th scope="col">Feature</th><th scope="col">Member</th><th scope="col">Segment average</th></tr>
              </thead>
              <tbody>
                <tr v-for="r in profileRows" :key="r.key">
                  <td>{{ r.label }}</td>
                  <td>{{ fmt(r.key, r.value) }}</td>
                  <td class="muted">{{ fmtAvg(r.key, r.segment) }}</td>
                </tr>
              </tbody>
            </table>
          </template>
        </Card>

        <Card>
          <template #title>Classes attended</template>
          <template #content>
            <PageState :empty="!d.attendance.length" empty-text="Does not attend group classes.">
              <table class="plain">
                <thead>
                  <tr><th scope="col">Class</th><th scope="col">Instructor</th><th scope="col">Visits / week</th></tr>
                </thead>
                <tbody>
                  <tr v-for="a in d.attendance" :key="a.class_id">
                    <td>{{ a.class_name }} <small class="muted">{{ a.class_id }}</small></td>
                    <td>{{ a.instructor_name }}</td>
                    <td>{{ num(a.visits_per_week) }}</td>
                  </tr>
                </tbody>
              </table>
            </PageState>
          </template>
        </Card>

        <Card>
          <template #title>Past retention contacts</template>
          <template #content>
            <PageState :empty="!d.interventions.length" empty-text="No past retention contacts.">
              <table class="plain">
                <thead>
                  <tr><th scope="col">Week</th><th scope="col">Offer</th><th scope="col">Channel</th><th scope="col">Result</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(i, n) in d.interventions" :key="n">
                    <td>{{ date(i.week_start) }}</td>
                    <td>{{ i.treated ? i.offer_id : 'No offer (control)' }}</td>
                    <td>{{ i.channel ?? '—' }}</td>
                    <td>
                      <Tag :severity="i.stayed ? 'success' : 'danger'" :value="i.stayed ? 'Stayed' : 'Left'" />
                    </td>
                  </tr>
                </tbody>
              </table>
            </PageState>
          </template>
        </Card>

        <Card v-for="p in panels" :key="p.title">
          <template #title>{{ p.title }}</template>
          <template #content>
            <PageState
              :loading="p.state.loading.value"
              :empty="!!p.state.error.value || !p.state.data.value"
              :empty-text="`Not available yet (${p.owner}).`"
            >
              <pre class="raw">{{ JSON.stringify(p.state.data.value, null, 2) }}</pre>
            </PageState>
          </template>
        </Card>
      </section>
    </template>
  </PageState>
</template>

<style scoped>
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
.note {
  margin: 0.5rem 0 0;
  font-size: 0.85rem;
}
.raw {
  max-height: 240px;
  overflow: auto;
  font-size: 0.8rem;
}
</style>
