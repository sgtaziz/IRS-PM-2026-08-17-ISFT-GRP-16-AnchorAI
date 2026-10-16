<script setup lang="ts">
import { Ban, CircleCheck, Lightbulb, MessageSquareText, ShieldAlert } from 'lucide-vue-next'
import vTooltip from 'primevue/tooltip'
import { computed, onMounted, ref } from 'vue'
import type { RuleOutcome } from '../api/types'
import { channelLabel, humanize, ruleCode } from '../labels'
import { useGlossaryStore } from '../stores/glossary'
import MessageDraftDialog from './MessageDraftDialog.vue'

const props = defineProps<{ outcome: RuleOutcome }>()
const glossary = useGlossaryStore()
onMounted(glossary.load)

const drafting = ref<{ offerId: string; channel: string } | null>(null)
const draftOpen = computed({
  get: () => drafting.value !== null,
  set: (open) => {
    if (!open) drafting.value = null
  },
})

const blocked = computed(() => Object.entries(props.outcome.blocked))

// Fact descriptions double as labels when they're short; long ones read better as the humanised name.
function factLabel(name: string) {
  const d = glossary.fact(name)
  return d.length <= 32 && !d.includes(':') ? d : humanize(name)
}

function facts(matched: Record<string, unknown>) {
  return Object.entries(matched).map(([k, v]) => {
    const value = typeof v === 'number' ? +v.toFixed(2) : typeof v === 'boolean' ? (v ? 'yes' : 'no') : String(v)
    return `${factLabel(k)}: ${value}`
  })
}

const ruleTip = (id: string) => `${glossary.rule(id)} (${id})`

const lower = (label: string) => (label === label.toUpperCase() ? label : label.toLowerCase())

type Kind = 'derive' | 'playbook' | 'guardrail'

// Effects are written by anchorai/reasoning/engine.py as "assert k=v", "propose offer via channel" or "block ids".
function effect(text: string): { kind: Kind; text: string } {
  const propose = text.match(/^propose (\S+) via (\S+)/)
  if (propose) return { kind: 'playbook', text: `Proposes ${glossary.offer(propose[1])} by ${lower(channelLabel(propose[2]))}` }
  const block = text.match(/^block (.+)$/)
  if (block) {
    const ids = block[1].split(', ')
    return { kind: 'guardrail', text: `Blocks ${ids.includes('all') ? 'all offers' : ids.map(glossary.offer).join(', ')}` }
  }
  const pairs = [...text.replace(/\s*\(kept existing.*\)$/, '').matchAll(/(\w+)=([^,]+)/g)]
  const derived = pairs.map(([, k, v]) =>
    v === 'True' ? humanize(k) : v === 'False' ? `not ${humanize(k).toLowerCase()}` : `${humanize(k)} = ${v}`,
  )
  if (derived.length) return { kind: 'derive', text: `Concludes: ${derived.join(', ')}` }
  // "assert" alone means every fact was already set by an earlier rule.
  return { kind: 'derive', text: /^assert(\s|$)/.test(text) && !text.includes('=') ? 'Nothing new: already known' : text }
}

const KIND_STYLE: Record<Kind, { icon: typeof Lightbulb; cls: string }> = {
  derive: { icon: Lightbulb, cls: 'bg-violet-soft text-violet-ink' },
  playbook: { icon: CircleCheck, cls: 'bg-success-soft text-success-ink' },
  guardrail: { icon: ShieldAlert, cls: 'bg-danger-soft text-danger-ink' },
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <section>
      <h3 class="heading">Allowed offers</h3>
      <p v-if="!outcome.allowed.length" class="m-0 text-sm text-ink-500">No offer allowed.</p>
      <ul v-else class="m-0 flex list-none flex-col gap-2 p-0">
        <li v-for="p in outcome.allowed" :key="p.offer_id" class="offer allowed">
          <CircleCheck :size="16" class="shrink-0 text-success" aria-hidden="true" />
          <span class="min-w-0 flex-1">
            <span class="font-semibold text-ink-800">{{ glossary.offer(p.offer_id) }}</span>
            <span class="text-ink-500"> · {{ channelLabel(p.channel) }}</span>
          </span>
          <button type="button" class="draft-btn" @click="drafting = { offerId: p.offer_id, channel: p.channel }">
            <MessageSquareText :size="14" aria-hidden="true" />Draft message
          </button>
          <span v-tooltip.top="ruleTip(p.rule_id)" class="id-chip" tabindex="0" role="note" :aria-label="ruleTip(p.rule_id)">{{ ruleCode(p.rule_id) }}</span>
        </li>
      </ul>
    </section>
    <section v-if="blocked.length">
      <h3 class="heading">Blocked</h3>
      <ul class="m-0 flex list-none flex-col gap-2 p-0">
        <li v-for="[target, rule] in blocked" :key="target" class="offer blocked">
          <Ban :size="16" class="shrink-0 text-danger" aria-hidden="true" />
          <span class="min-w-0 flex-1">
            <span class="font-semibold text-ink-800">{{ target === 'all' ? 'All offers' : glossary.offer(target) }}</span>
            <span class="block text-xs text-ink-500">{{ glossary.rule(rule) }}</span>
          </span>
          <span v-tooltip.top="ruleTip(rule)" class="id-chip" tabindex="0" role="note" :aria-label="ruleTip(rule)">{{ ruleCode(rule) }}</span>
        </li>
      </ul>
    </section>
    <section>
      <h3 class="heading">Rules fired, in order</h3>
      <p v-if="!outcome.firings.length" class="m-0 text-sm text-ink-500">No rule matched.</p>
      <ol v-else class="m-0 flex list-none flex-col p-0">
        <li v-for="(f, i) in outcome.firings" :key="f.rule_id" class="firing">
          <span class="step" :class="KIND_STYLE[effect(f.effect).kind].cls" aria-hidden="true">
            <component :is="KIND_STYLE[effect(f.effect).kind].icon" :size="14" />
          </span>
          <div class="min-w-0 flex-1 pb-4">
            <p class="m-0 flex flex-wrap items-baseline gap-x-2 text-sm">
              <span class="sr-only">Step {{ i + 1 }}:</span>
              <span class="font-medium text-ink-800">{{ f.description }}</span>
              <span v-tooltip.top="ruleTip(f.rule_id)" class="id-chip" tabindex="0" role="note" :aria-label="ruleTip(f.rule_id)">{{ ruleCode(f.rule_id) }}</span>
            </p>
            <p class="m-0 mt-0.5 text-[0.8125rem] font-medium text-ink-600">{{ effect(f.effect).text }}</p>
            <p class="m-0 mt-1.5 flex flex-wrap gap-1">
              <span class="sr-only">Because</span>
              <span v-for="c in facts(f.facts_matched)" :key="c" class="fact">{{ c }}</span>
            </p>
          </div>
        </li>
      </ol>
    </section>
    <MessageDraftDialog
      v-if="drafting"
      v-model:visible="draftOpen"
      :member-id="outcome.member_id"
      :offer-id="drafting.offerId"
      :channel="drafting.channel"
    />
  </div>
</template>

<style scoped>
.heading { margin: 0 0 0.6rem; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: var(--color-ink-500); }
.offer { display: flex; align-items: center; gap: 0.6rem; padding: 0.55rem 0.75rem; border-radius: 0.6rem; font-size: 0.875rem; }
.offer.allowed { background: var(--color-success-soft); border: 1px solid var(--color-success-line); }
.draft-btn { display: inline-flex; align-items: center; gap: 0.3rem; flex: none; padding: 0.2rem 0.55rem; border: 1px solid var(--color-success-line); border-radius: 999px; background: transparent; font: inherit; font-size: 0.75rem; font-weight: 600; color: var(--color-success-ink); cursor: pointer; }
.draft-btn:hover { background: var(--color-success-line); }
.draft-btn:focus-visible { outline: 2px solid var(--color-brand-500); outline-offset: 2px; }
.offer.blocked { background: var(--color-danger-soft); border: 1px solid var(--color-danger-line); }
.firing { position: relative; display: flex; gap: 0.75rem; }
.firing:not(:last-child)::before { content: ''; position: absolute; left: 0.8rem; top: 1.75rem; bottom: 0.15rem; width: 1px; background: var(--color-ink-200); }
.step { display: grid; place-items: center; flex: none; width: 1.6rem; height: 1.6rem; border-radius: 999px; }
.fact { padding: 0.1rem 0.45rem; border-radius: 5px; font-size: 0.72rem; color: var(--color-ink-600); background: var(--color-ink-100); }
</style>
