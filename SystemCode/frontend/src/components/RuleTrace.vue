<script setup lang="ts">
import { Ban, CircleCheck, Lightbulb, ShieldAlert } from 'lucide-vue-next'
import vTooltip from 'primevue/tooltip'
import { computed, onMounted } from 'vue'
import type { RuleOutcome } from '../api/types'
import { channelLabel, humanize, ruleCode } from '../labels'
import { useGlossaryStore } from '../stores/glossary'

const props = defineProps<{ outcome: RuleOutcome }>()
const glossary = useGlossaryStore()
onMounted(glossary.load)

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
  const derived = pairs.map(([, k, v]) => (v === 'True' ? humanize(k) : `${humanize(k)} = ${v}`))
  return { kind: 'derive', text: derived.length ? `Concludes: ${derived.join(', ')}` : 'Already known' }
}

const KIND_STYLE: Record<Kind, { icon: typeof Lightbulb; cls: string }> = {
  derive: { icon: Lightbulb, cls: 'bg-[#efeafe] text-[#5b3cc4]' },
  playbook: { icon: CircleCheck, cls: 'bg-success-soft text-[#0b7a53]' },
  guardrail: { icon: ShieldAlert, cls: 'bg-danger-soft text-[#b4183a]' },
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
          <span v-tooltip.top="glossary.rule(p.rule_id)" class="id-chip" tabindex="0">{{ ruleCode(p.rule_id) }}</span>
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
          <span class="id-chip">{{ ruleCode(rule) }}</span>
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
              <span v-tooltip.top="f.rule_id" class="id-chip">{{ ruleCode(f.rule_id) }}</span>
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
  </div>
</template>

<style scoped>
.heading { margin: 0 0 0.6rem; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: var(--color-ink-500); }
.offer { display: flex; align-items: center; gap: 0.6rem; padding: 0.55rem 0.75rem; border-radius: 0.6rem; font-size: 0.875rem; }
.offer.allowed { background: color-mix(in srgb, var(--color-success-soft) 70%, #fff); border: 1px solid #c9ecdc; }
.offer.blocked { background: color-mix(in srgb, var(--color-danger-soft) 60%, #fff); border: 1px solid #f7d0d8; }
.firing { position: relative; display: flex; gap: 0.75rem; }
.firing:not(:last-child)::before { content: ''; position: absolute; left: 0.8rem; top: 1.75rem; bottom: 0.15rem; width: 1px; background: var(--color-ink-200); }
.step { display: grid; place-items: center; flex: none; width: 1.6rem; height: 1.6rem; border-radius: 999px; }
.fact { padding: 0.1rem 0.45rem; border-radius: 5px; font-size: 0.72rem; color: var(--color-ink-600); background: var(--color-ink-100); }
</style>
