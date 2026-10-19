<script setup lang="ts">
import { CircleCheck, CircleX } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import type { OfferEvidence } from '../api/types'
import { date } from '../format'

// Stream B: CBR's estimate per offer for one member, with the past cases behind it (GET /api/plan/similar-cases/{id}).
const props = defineProps<{ evidence: OfferEvidence[] }>()
const open = ref(props.evidence[0]?.offer_id ?? null)
const shown = computed(() => props.evidence.find((e) => e.offer_id === open.value) ?? null)
const points = (v: number) => `${v >= 0 ? '+' : ''}${Math.round(v * 100)} pts`
const stayed = (e: OfferEvidence, treated: boolean) => {
  const group = e.cases.filter((c) => !!c.offer_id === treated)
  return `${group.filter((c) => c.stayed).length} of ${group.length}`
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex flex-wrap gap-2" role="tablist" aria-label="Offers">
      <button
        v-for="e in evidence"
        :key="e.offer_id"
        type="button"
        role="tab"
        :aria-selected="open === e.offer_id"
        class="rounded-lg border px-3 py-1.5 text-left text-sm"
        :class="open === e.offer_id ? 'border-brand-600 bg-brand-50 text-brand-800' : 'border-ink-200 text-ink-700'"
        @click="open = e.offer_id"
      >
        <span class="block font-medium">{{ e.offer_name }}</span>
        <span class="tabular-nums text-xs" :class="e.estimate >= 0 ? 'text-success-ink' : 'text-danger-ink'">{{ points(e.estimate) }}</span>
      </button>
    </div>
    <template v-if="shown">
      <p class="m-0 text-sm text-ink-600">
        Of the {{ shown.cases.length }} most similar past members, {{ stayed(shown, true) }} who got {{ shown.offer_name.toLowerCase() }}
        stayed, against {{ stayed(shown, false) }} with no offer. Estimated effect {{ points(shown.estimate) }}, from
        {{ shown.neighbours_treated }} treated and {{ shown.neighbours_control }} untreated neighbours.
      </p>
      <ul class="m-0 flex list-none flex-col gap-1 p-0 text-sm">
        <li v-for="c in shown.cases" :key="c.member_id" class="flex items-center gap-2">
          <CircleCheck v-if="c.stayed" :size="15" class="shrink-0 text-success" aria-label="stayed" />
          <CircleX v-else :size="15" class="shrink-0 text-danger" aria-label="left" />
          <RouterLink :to="`/members/${c.member_id}`" class="member-link">{{ c.member_id }}</RouterLink>
          <span class="text-ink-600">{{ c.offer_id ? shown.offer_name : 'No offer' }} · week of {{ date(c.week_start) }}</span>
        </li>
      </ul>
    </template>
  </div>
</template>
