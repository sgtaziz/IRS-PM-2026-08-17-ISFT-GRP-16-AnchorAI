<script setup lang="ts">
import { CalendarCheck, Clock, DollarSign, Lock, Play, Plus, Repeat, Trash2, UserCheck, Users } from 'lucide-vue-next'
import Button from 'primevue/button'
import Column from 'primevue/column'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import Dialog from 'primevue/dialog'
import SelectButton from 'primevue/selectbutton'
import Textarea from 'primevue/textarea'
import vTooltip from 'primevue/tooltip'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ApiError, api } from '../api/client'
import type { PlanItem, PlanJob, PlanRequest, SavedPlan } from '../api/types'
import AddContactDialog from '../components/AddContactDialog.vue'
import ConfirmAction from '../components/ConfirmAction.vue'
import ExplanationDrawer from '../components/ExplanationDrawer.vue'
import PlanAssignment from '../components/PlanAssignment.vue'
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
const SOLVERS = [
  { label: 'Genetic algorithm', value: 'ga' },
  { label: 'Exact (linear)', value: 'exact' },
  { label: 'Greedy', value: 'greedy' },
]
const solver = ref('ga')

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
    solver.value = plan.value.request.solver ?? 'ga'
  }
})

const generating = ref(false)
const generateError = ref<string | null>(null)
const job = ref<PlanJob | null>(null)
const STAGES: Record<string, string> = {
  queued: 'Starting',
  loading: 'Reading members, rules and estimates',
  optimising: 'Searching for the best plan',
  explaining: 'Writing the reasons',
  saving: 'Saving',
}
let timer: ReturnType<typeof setTimeout> | undefined
// The manager's own calendar day, not UTC: just after midnight UTC is still yesterday.
const localDate = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
onBeforeUnmount(() => clearTimeout(timer))

// The GA takes about half a minute, so the plan is built as a background job and polled.
async function poll() {
  try {
    job.value = await api<PlanJob>('/plan/jobs/current')
    if (job.value.state === 'running') {
      timer = setTimeout(poll, 700)
      return
    }
    if (job.value.state === 'failed') generateError.value = job.value.error ?? 'The planner failed'
    else if (job.value.plan_id) plan.value = await api<SavedPlan>(`/plan/${job.value.plan_id}`)
  } catch (e) {
    generateError.value = errorMessage(e)
  }
  generating.value = false
}

async function generate() {
  generating.value = true
  generateError.value = null
  const request: PlanRequest = {
    as_of: localDate(),
    budget: budget.value,
    staff_minutes: Math.round(staffHours.value * 60),
    solver: solver.value,
  }
  try {
    job.value = await api<PlanJob>('/plan/jobs', { method: 'POST', body: JSON.stringify(request) })
    poll()
  } catch (e) {
    generateError.value = errorMessage(e)
    generating.value = false
  }
}

const usedHours = computed(() => (plan.value ? plan.value.total_staff_minutes / 60 : 0))
const isDraft = computed(() => plan.value?.status === 'draft')

// W14: the "why" drawer.
const whyItem = ref<PlanItem | null>(null)

// W15: overrides on a draft plan, each with a reason, then approval locks it.
const addOpen = ref(false)
const swapMember = ref<string | null>(null)
function openAdd(memberId: string | null = null) {
  swapMember.value = memberId
  addOpen.value = true
}

const removing = ref<PlanItem | null>(null)
const removeReason = ref('')
const removeError = ref<string | null>(null)
const busy = ref(false)
function openRemove(item: PlanItem) {
  removing.value = item
  removeReason.value = ''
  removeError.value = null
}
async function remove() {
  if (!plan.value || !removing.value) return
  busy.value = true
  try {
    plan.value = await api<SavedPlan>(`/plan/${plan.value.id}/items/${removing.value.member_id}/remove`, {
      method: 'POST',
      body: JSON.stringify({ reason: removeReason.value.trim() }),
    })
    removing.value = null
  } catch (e) {
    removeError.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}

const approveError = ref<string | null>(null)
async function approve() {
  if (!plan.value) return
  approveError.value = null
  try {
    plan.value = await api<SavedPlan>(`/plan/${plan.value.id}/approve`, { method: 'POST' })
  } catch (e) {
    approveError.value = errorMessage(e)
  }
}
</script>

<template>
  <div class="page">
    <PageHeader title="Weekly plan" subtitle="Build, review and approve this week's retention contacts within budget and staff hours." />

    <SectionCard title="Generate a plan" :icon="CalendarCheck" subtitle="Uplift from case-based reasoning over past interventions; the genetic algorithm takes up to a minute.">
      <form class="flex flex-wrap items-end gap-4 px-5 pb-5 pt-3" @submit.prevent="generate">
        <label class="field">
          <span>Weekly budget</span>
          <InputNumber v-model="budget" :min="0" mode="currency" currency="USD" :max-fraction-digits="0" />
        </label>
        <label class="field">
          <span>Staff hours this week</span>
          <InputNumber v-model="staffHours" :min="0" :max="1000" suffix=" h" />
        </label>
        <div class="field">
          <span>Planner</span>
          <SelectButton v-model="solver" :options="SOLVERS" option-label="label" option-value="value" :allow-empty="false" aria-label="Planner" />
        </div>
        <Button type="submit" label="Generate plan" :loading="generating">
          <template #icon><Play :size="15" /></template>
        </Button>
      </form>
      <div v-if="generating && job" class="mx-5 mb-5 flex flex-col gap-1.5" role="status" aria-live="polite">
        <span class="text-sm text-ink-600">{{ STAGES[job.stage ?? 'queued'] ?? humanize(job.stage ?? '') }}…</span>
        <ProgressBar :value="Math.round(job.progress * 100)" style="height: 0.5rem" :show-value="false" />
      </div>
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
          <template #actions>
            <template v-if="isDraft">
              <Button label="Add contact" size="small" severity="secondary" outlined @click="openAdd()">
                <template #icon><Plus :size="15" /></template>
              </Button>
              <ConfirmAction
                label="Approve plan"
                severity="primary"
                header="Approve this plan?"
                :message="`Approving locks plan #${plan.id}: no more changes, and its ${plan.items.length} contacts can be assigned to staff.`"
                @confirm="approve"
              />
            </template>
            <span v-else class="flex items-center gap-1.5 text-sm text-ink-500"><Lock :size="14" /> Approved and locked</span>
          </template>
          <Message v-if="approveError" severity="error" class="mx-5 mb-3">{{ approveError }}</Message>
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
            <Column header="" :exportable="false">
              <template #body="{ data }">
                <div class="flex justify-end gap-1">
                  <Button label="Why" size="small" text @click="whyItem = data" />
                  <template v-if="isDraft">
                    <Button size="small" text severity="secondary" aria-label="Swap offer" v-tooltip.top="'Swap offer'" @click="openAdd(data.member_id)">
                      <template #icon><Repeat :size="14" /></template>
                    </Button>
                    <Button size="small" text severity="danger" aria-label="Remove" v-tooltip.top="'Remove'" @click="openRemove(data)">
                      <template #icon><Trash2 :size="14" /></template>
                    </Button>
                  </template>
                </div>
              </template>
            </Column>
          </DataTableX>
        </SectionCard>
        <PlanAssignment v-if="!isDraft" :key="plan.id" :plan-id="plan.id" />
      </template>
    </PageState>

    <ExplanationDrawer
      :explanation-id="whyItem?.explanation_id ?? null"
      :offer-name="whyItem ? glossary.offer(whyItem.offer_id) : undefined"
      @close="whyItem = null"
    />
    <AddContactDialog v-if="plan" v-model:visible="addOpen" :plan-id="plan.id" :member-id="swapMember" @saved="plan = $event" />
    <Dialog :visible="!!removing" modal :header="`Remove ${removing?.member_id} from the plan`" class="w-full max-w-md" @update:visible="removing = null">
      <form class="flex flex-col gap-4" @submit.prevent="remove">
        <label class="field">
          <span>Reason (required)</span>
          <Textarea v-model="removeReason" rows="2" auto-resize placeholder="Why should this member not be contacted?" fluid />
        </label>
        <Message v-if="removeError" severity="error">{{ removeError }}</Message>
        <div class="flex justify-end gap-2">
          <Button label="Cancel" severity="secondary" outlined type="button" @click="removing = null" />
          <Button type="submit" label="Remove" severity="danger" :disabled="removeReason.trim().length < 3" :loading="busy" />
        </div>
      </form>
    </Dialog>
  </div>
</template>
