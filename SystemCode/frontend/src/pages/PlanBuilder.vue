<script setup lang="ts">
import { CalendarCheck, Clock, DollarSign, Play, UserCheck, Users } from 'lucide-vue-next'
import Button from 'primevue/button'
import Column from 'primevue/column'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import { computed, onMounted, ref } from 'vue'
import { ApiError, api } from '../api/client'
import type { PlanRequest, SavedPlan } from '../api/types'
import DataTableX from '../components/DataTableX.vue'
import KpiTile from '../components/KpiTile.vue'
import PageHeader from '../components/PageHeader.vue'
import PageState from '../components/PageState.vue'
import SectionCard from '../components/SectionCard.vue'
import { errorMessage, useAsync } from '../composables/useAsync'
import { dateTime, money, num } from '../format'
import { channelLabel, humanize } from '../labels'
import { useGlossaryStore } from '../stores/glossary'

const glossary = useGlossaryStore()
const budget = ref(1500)
const staffHours = ref(36)

// No plan yet is a normal state, not an error.
const latest = useAsync(async () => {
  try {
    return await api<SavedPlan>('/plan/latest')
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null
    throw e
  }
})
const plan = ref<SavedPlan | null>(null)

onMounted(async () => {
  glossary.load()
  plan.value = await latest.run()
  if (plan.value) {
    budget.value = plan.value.request.budget
    staffHours.value = plan.value.request.staff_minutes / 60
  }
})

const generating = ref(false)
const generateError = ref<string | null>(null)

async function generate() {
  generating.value = true
  generateError.value = null
  const request: PlanRequest = {
    as_of: new Date().toISOString().slice(0, 10),
    budget: budget.value,
    staff_minutes: Math.round(staffHours.value * 60),
    solver: 'greedy',
  }
  try {
    plan.value = await api<SavedPlan>('/plan', { method: 'POST', body: JSON.stringify(request) })
  } catch (e) {
    generateError.value = errorMessage(e)
  } finally {
    generating.value = false
  }
}

const usedHours = computed(() => (plan.value ? plan.value.total_staff_minutes / 60 : 0))
</script>

<template>
  <div class="page">
    <PageHeader title="Weekly plan" subtitle="Build, review and approve this week's retention contacts within budget and staff hours." />

    <SectionCard title="Generate a plan" :icon="CalendarCheck" subtitle="Greedy planner on T-learner uplift for now; the genetic algorithm and CBR replace them later.">
      <form class="flex flex-wrap items-end gap-4 px-5 pb-5 pt-3" @submit.prevent="generate">
        <label class="field">
          <span>Weekly budget</span>
          <InputNumber v-model="budget" :min="0" mode="currency" currency="USD" :max-fraction-digits="0" />
        </label>
        <label class="field">
          <span>Staff hours this week</span>
          <InputNumber v-model="staffHours" :min="0" :max="1000" suffix=" h" />
        </label>
        <Button type="submit" label="Generate plan" :loading="generating">
          <template #icon><Play :size="15" /></template>
        </Button>
      </form>
      <Message v-if="generateError" severity="error" class="mx-5 mb-5">{{ generateError }}</Message>
    </SectionCard>

    <PageState
      class="mt-6"
      :loading="latest.loading.value && !plan"
      :error="latest.error.value"
      :empty="!plan"
      empty-text="No plan yet. Set the budget and staff hours, then generate one."
      @retry="latest.run"
    >
      <template v-if="plan">
        <section class="mt-6 grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4" aria-label="Plan totals">
          <KpiTile label="Members to contact" :value="plan.items.length.toLocaleString()" :icon="Users" />
          <KpiTile label="Spend" :value="money(plan.total_cost)" :hint="`of ${money(plan.request.budget)} budget`" :icon="DollarSign" />
          <KpiTile
            label="Staff time"
            :value="`${num(usedHours, 1)} h`"
            :hint="`of ${num(plan.request.staff_minutes / 60, 1)} h available`"
            :icon="Clock"
          />
          <KpiTile
            label="Extra members expected to stay"
            :value="num(plan.expected_members_retained, 1)"
            hint="by the planner's own estimates"
            :icon="UserCheck"
            tone="good"
          />
        </section>

        <SectionCard
          class="mt-6"
          :title="`Plan #${plan.id} · ${humanize(plan.status)}`"
          :subtitle="`Built ${dateTime(plan.created_at)} for the week of ${plan.request.as_of}`"
          flush
        >
          <DataTableX
            :value="plan.items"
            data-key="member_id"
            :export-name="`plan-${plan.id}`"
            :global-filter-fields="['member_id', 'offer_id', 'channel']"
          >
            <Column field="member_id" header="Member" sortable>
              <template #body="{ data }">
                <RouterLink :to="`/members/${data.member_id}`" class="member-link">{{ data.member_id }}</RouterLink>
              </template>
            </Column>
            <Column field="offer_id" header="Offer" sortable>
              <template #body="{ data }">{{ glossary.offer(data.offer_id) }}</template>
            </Column>
            <Column field="channel" header="Channel" sortable>
              <template #body="{ data }">{{ channelLabel(data.channel) }}</template>
            </Column>
            <Column field="expected_value" header="Expected value" sortable>
              <template #body="{ data }"><span class="tabular-nums">{{ money(data.expected_value) }}</span></template>
            </Column>
          </DataTableX>
        </SectionCard>
      </template>
    </PageState>
  </div>
</template>
