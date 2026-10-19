<script setup lang="ts">
import { CircleCheck, CircleX, Network, Scale, Users } from 'lucide-vue-next'
import Drawer from 'primevue/drawer'
import { computed, watch } from 'vue'
import { api } from '../api/client'
import type { Explanation } from '../api/types'
import { useAsync } from '../composables/useAsync'
import { date, probability } from '../format'
import { ruleCode } from '../labels'
import { useGlossaryStore } from '../stores/glossary'
import PageState from './PageState.vue'

// Stream B: the full reason behind one plan item (GET /api/plan/explanations/{id}).
const props = defineProps<{ explanationId: string | null; offerName?: string }>()
const emit = defineEmits<{ close: [] }>()
const glossary = useGlossaryStore()
glossary.load()

const why = useAsync((id: string) => api<Explanation>(`/plan/explanations/${encodeURIComponent(id)}`))
watch(
  () => props.explanationId,
  (id) => id && why.run(id),
  { immediate: true },
)
const visible = computed({
  get: () => props.explanationId !== null,
  set: (open) => {
    if (!open) emit('close')
  },
})
const e = computed(() => why.data.value)
const maxDriver = computed(() => Math.max(...(e.value?.top_drivers ?? []).map(([, v]) => Math.abs(v)), 1e-9))
const treated = computed(() => (e.value?.similar_cases ?? []).filter((c) => c.offer_id))
const control = computed(() => (e.value?.similar_cases ?? []).filter((c) => !c.offer_id))
const stayed = (cases: { stayed: boolean }[]) => `${cases.filter((c) => c.stayed).length} of ${cases.length}`
</script>

<template>
  <Drawer v-model:visible="visible" position="right" :header="e ? `Why ${e.member_id}?` : 'Why?'" class="w-full sm:!w-[30rem]">
    <PageState :loading="why.loading.value" :error="why.error.value" @retry="explanationId && why.run(explanationId)">
      <div v-if="e" class="flex flex-col gap-6 text-sm">
        <p class="m-0 text-[0.95rem] leading-relaxed text-ink-800">{{ e.summary }}</p>

        <section>
          <h3 class="m-0 mb-2 flex items-center gap-2 text-sm font-semibold text-ink-900">
            Churn risk {{ probability(e.churn_prob) }} · main drivers
          </h3>
          <ul class="m-0 flex list-none flex-col gap-1.5 p-0">
            <li v-for="[name, value] in e.top_drivers" :key="name" class="grid grid-cols-[1fr_5rem_4.5rem] items-center gap-2">
              <span class="leading-tight text-ink-700">{{ glossary.fact(name) }}</span>
              <span class="h-2 overflow-hidden rounded-full bg-ink-100">
                <span class="block h-full rounded-full" :class="value > 0 ? 'bg-danger' : 'bg-success'" :style="{ width: `${(100 * Math.abs(value)) / maxDriver}%` }" />
              </span>
              <span class="whitespace-nowrap text-xs text-ink-500">{{ value > 0 ? 'raises risk' : 'lowers risk' }}</span>
            </li>
          </ul>
        </section>

        <section>
          <h3 class="m-0 mb-2 flex items-center gap-2 text-sm font-semibold text-ink-900"><Scale :size="15" /> Rules that fired</h3>
          <ul class="m-0 flex list-none flex-col gap-1 p-0">
            <li v-for="f in e.rule_trace" :key="f.rule_id">
              <span class="font-mono text-xs text-ink-500">{{ ruleCode(f.rule_id) }}</span>
              {{ f.description }} <span class="text-ink-500">→ {{ f.effect }}</span>
            </li>
          </ul>
        </section>

        <section v-if="e.graph_signals.length">
          <h3 class="m-0 mb-2 flex items-center gap-2 text-sm font-semibold text-ink-900"><Network :size="15" /> Gym context</h3>
          <ul class="m-0 list-disc pl-5">
            <li v-for="s in e.graph_signals" :key="s">{{ s }}</li>
          </ul>
        </section>

        <section>
          <h3 class="m-0 mb-1 flex items-center gap-2 text-sm font-semibold text-ink-900"><Users :size="15" /> Similar past members</h3>
          <p class="m-0 mb-2 text-ink-600">
            {{ stayed(treated) }} who got {{ offerName?.toLowerCase() ?? 'the offer' }} stayed; {{ stayed(control) }} with no offer did.
          </p>
          <ul class="m-0 flex list-none flex-col gap-1 p-0">
            <li v-for="c in e.similar_cases" :key="c.member_id" class="flex items-center gap-2">
              <CircleCheck v-if="c.stayed" :size="15" class="shrink-0 text-success" aria-label="stayed" />
              <CircleX v-else :size="15" class="shrink-0 text-danger" aria-label="left" />
              <RouterLink :to="`/members/${c.member_id}`" class="member-link">{{ c.member_id }}</RouterLink>
              <span class="text-ink-600">{{ c.offer_id ? glossary.offer(c.offer_id) : 'No offer' }} · week of {{ date(c.week_start) }}</span>
            </li>
          </ul>
        </section>
      </div>
    </PageState>
  </Drawer>
</template>
