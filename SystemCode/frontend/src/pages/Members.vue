<script setup lang="ts">
import { FilterX, Search, TrendingDown, TrendingUp } from 'lucide-vue-next'
import Button from 'primevue/button'
import Column from 'primevue/column'
import type { DataTablePageEvent, DataTableSortEvent } from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, apiText, downloadText, query } from '../api/client'
import type { Facets, MemberPage, MemberRow, RiskBand } from '../api/types'
import DataTableX from '../components/DataTableX.vue'
import PageHeader from '../components/PageHeader.vue'
import PageState from '../components/PageState.vue'
import RiskBadge from '../components/RiskBadge.vue'
import { errorMessage, useAsync } from '../composables/useAsync'
import { money, num } from '../format'
import { contractLabel } from '../labels'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const RISK_OPTIONS = [
  { label: 'High', value: 'high' },
  { label: 'Medium', value: 'medium' },
  { label: 'Low', value: 'low' },
]
const PAGE_SIZES = [25, 50, 100]

interface State {
  segment: string | null
  risk_band: RiskBand | null
  club_id: string | null
  min_tenure: number | null
  max_tenure: number | null
  q: string
  page: number
  page_size: number
  sort: string
  order: 'asc' | 'desc'
}

const str = (v: unknown) => (typeof v === 'string' && v !== '' ? v : null)
const int = (v: unknown) => (str(v) !== null && !Number.isNaN(Number(v)) ? Number(v) : null)

function fromQuery(): State {
  const q = route.query
  return {
    segment: str(q.segment),
    risk_band: str(q.risk_band) as RiskBand | null,
    club_id: str(q.club_id),
    min_tenure: int(q.min_tenure),
    max_tenure: int(q.max_tenure),
    q: str(q.q) ?? '',
    page: int(q.page) ?? 1,
    page_size: int(q.page_size) ?? 25,
    sort: str(q.sort) ?? 'churn_prob',
    order: q.order === 'asc' ? 'asc' : 'desc',
  }
}

const state = reactive<State>(fromQuery())
const facets = useAsync(() => api<Facets>('/members/facets'))
const members = useAsync((qs: string) => api<MemberPage>(`/members${qs}`))

const filterQuery = computed(() =>
  query({
    segment: state.segment,
    risk_band: state.risk_band,
    club_id: state.club_id,
    min_tenure: state.min_tenure,
    max_tenure: state.max_tenure,
    q: state.q.trim(),
    sort: state.sort,
    order: state.order,
  }),
)
const pageQuery = computed(() =>
  query({
    segment: state.segment,
    risk_band: state.risk_band,
    club_id: state.club_id,
    min_tenure: state.min_tenure,
    max_tenure: state.max_tenure,
    q: state.q.trim(),
    sort: state.sort,
    order: state.order,
    page: state.page,
    page_size: state.page_size,
  }),
)

function load() {
  members.run(pageQuery.value)
}

watch(pageQuery, (qs) => {
  const next: Record<string, string> = {}
  new URLSearchParams(qs).forEach((v, k) => (next[k] = v))
  router.replace({ query: next })
  load()
})
watch(
  () => route.query,
  () => {
    const next = fromQuery()
    if (query({ ...next }) !== query({ ...state })) Object.assign(state, next)
  },
)

function resetPage() {
  state.page = 1
}

function onPage(e: DataTablePageEvent) {
  state.page = e.page + 1
  state.page_size = e.rows
}

function onSort(e: DataTableSortEvent) {
  state.sort = typeof e.sortField === 'string' ? e.sortField : 'churn_prob'
  state.order = e.sortOrder === 1 ? 'asc' : 'desc'
  state.page = 1
}

function clearFilters() {
  Object.assign(state, {
    segment: null,
    risk_band: null,
    club_id: null,
    min_tenure: null,
    max_tenure: null,
    q: '',
    page: 1,
  })
}

async function exportCsv() {
  try {
    downloadText('members.csv', await apiText(`/members/export.csv${filterQuery.value}`))
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Export failed', detail: errorMessage(e), life: 5000 })
  }
}

function openMember(e: { data: MemberRow }) {
  router.push(`/members/${e.data.member_id}`)
}

const segmentOptions = computed(() => (facets.data.value?.segments ?? []).map((s) => ({ label: s, value: s })))
const clubOptions = computed(() => (facets.data.value?.clubs ?? []).map((c) => ({ label: `Club ${c}`, value: c })))

onMounted(() => {
  facets.run()
  load()
})
</script>

<template>
  <div class="page">
    <PageHeader title="Members" subtitle="Every member with their current churn risk. Click a row to open the member's 360 view.">
      <template #actions>
        <span v-if="members.data.value" class="rounded-full bg-card px-3 py-1.5 text-sm font-medium text-ink-600 ring-1 ring-ink-200">
          {{ members.data.value.total.toLocaleString() }} members match
        </span>
      </template>
    </PageHeader>

    <form class="filters" role="search" @submit.prevent>
      <label class="field w-full sm:w-52">
        <span>Member ID</span>
        <IconField>
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="state.q" placeholder="e.g. M0042" fluid @update:model-value="resetPage" />
        </IconField>
      </label>
      <label class="field min-w-48">
        <span>Segment</span>
        <Select
          v-model="state.segment"
          :options="segmentOptions"
          option-label="label"
          option-value="value"
          placeholder="All segments"
          show-clear
          :loading="facets.loading.value"
          @change="resetPage"
        />
      </label>
      <label class="field min-w-36">
        <span>Risk band</span>
        <Select
          v-model="state.risk_band"
          :options="RISK_OPTIONS"
          option-label="label"
          option-value="value"
          placeholder="Any risk"
          show-clear
          @change="resetPage"
        />
      </label>
      <label class="field min-w-36">
        <span>Club</span>
        <Select
          v-model="state.club_id"
          :options="clubOptions"
          option-label="label"
          option-value="value"
          placeholder="All clubs"
          show-clear
          @change="resetPage"
        />
      </label>
      <fieldset class="field m-0 border-0 p-0">
        <span>Tenure (months)</span>
        <div class="flex items-center gap-2">
          <InputNumber v-model="state.min_tenure" :min="0" input-class="narrow" placeholder="From" aria-label="Tenure from (months)" @update:model-value="resetPage" />
          <span class="text-ink-400" aria-hidden="true">–</span>
          <InputNumber v-model="state.max_tenure" :min="0" input-class="narrow" placeholder="To" aria-label="Tenure to (months)" @update:model-value="resetPage" />
        </div>
      </fieldset>
      <Button label="Clear filters" severity="secondary" text class="self-end" @click="clearFilters">
        <template #icon><FilterX :size="16" /></template>
      </Button>
    </form>

    <div class="rounded-card border border-ink-200 bg-card p-4 shadow-card sm:p-5">
      <PageState :error="members.error.value" @retry="load">
        <DataTableX
          :value="members.data.value?.items ?? []"
          data-key="member_id"
          lazy
          :total-records="members.data.value?.total ?? 0"
          :rows="state.page_size"
          :first="(state.page - 1) * state.page_size"
          :rows-per-page-options="PAGE_SIZES"
          :loading="members.loading.value"
          :sort-field="state.sort"
          :sort-order="state.order === 'asc' ? 1 : -1"
          selection-mode="single"
          export-name="members"
          @page="onPage"
          @sort="onSort"
          @export="exportCsv"
          @row-click="openMember"
        >
          <template #toolbar>
            <p class="m-0 text-sm text-ink-500">Sorted by {{ state.sort === 'churn_prob' ? 'risk' : state.sort.replaceAll('_', ' ') }}, {{ state.order === 'asc' ? 'lowest' : 'highest' }} first</p>
          </template>
          <Column field="member_id" header="Member" sortable>
            <template #body="{ data }">
              <RouterLink :to="`/members/${data.member_id}`" class="member-link" @click.stop>{{ data.member_id }}</RouterLink>
            </template>
          </Column>
          <Column field="churn_prob" header="Risk" sortable>
            <template #body="{ data }"><RiskBadge :band="data.risk_band" :prob="data.churn_prob" /></template>
          </Column>
          <Column field="segment" header="Segment">
            <template #body="{ data }"><span class="whitespace-nowrap">{{ data.segment }}</span></template>
          </Column>
          <Column field="monthly_value" header="Monthly value" sortable>
            <template #body="{ data }"><span class="tabular-nums">{{ money(data.monthly_value) }}</span></template>
          </Column>
          <Column field="lifetime" header="Tenure" sortable>
            <template #body="{ data }"><span class="tabular-nums">{{ data.lifetime }} mo</span></template>
          </Column>
          <Column field="contract_period" header="Contract">
            <template #body="{ data }"><span class="whitespace-nowrap">{{ contractLabel(data.contract_period) }}</span></template>
          </Column>
          <Column field="trend_ratio" header="Visit trend" sortable>
            <template #body="{ data }">
              <span class="inline-flex items-center gap-1 tabular-nums" :class="data.trend_ratio < 0.8 ? 'text-danger' : data.trend_ratio > 1.05 ? 'text-success' : 'text-ink-600'">
                <component :is="data.trend_ratio < 1 ? TrendingDown : TrendingUp" :size="15" aria-hidden="true" />
                {{ num(data.trend_ratio) }}×
              </span>
            </template>
          </Column>
          <Column field="age" header="Age" sortable />
          <Column field="club_id" header="Club">
            <template #body="{ data }">Club {{ data.club_id }}</template>
          </Column>
        </DataTableX>
      </PageState>
    </div>
  </div>
</template>

<style scoped>
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.875rem 1rem;
  align-items: end;
  margin-bottom: 1.25rem;
  padding: 1rem 1.25rem;
  background: var(--color-card);
  border: 1px solid var(--color-ink-200);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}
:deep(.narrow) {
  width: 5.5rem;
}
</style>
