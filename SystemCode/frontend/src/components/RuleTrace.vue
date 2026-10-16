<script setup lang="ts">
import Tag from 'primevue/tag'
import { computed } from 'vue'
import type { RuleOutcome } from '../api/types'

const props = defineProps<{ outcome: RuleOutcome }>()

const blocked = computed(() => Object.entries(props.outcome.blocked))

function facts(matched: Record<string, unknown>) {
  return Object.entries(matched)
    .map(([k, v]) => `${k} = ${typeof v === 'number' ? +v.toFixed(2) : v}`)
    .join(', ')
}
</script>

<template>
  <div class="trace">
    <section>
      <h4>Allowed offers</h4>
      <p v-if="!outcome.allowed.length" class="muted">No offer allowed.</p>
      <ul v-else class="tags">
        <li v-for="p in outcome.allowed" :key="p.offer_id">
          <Tag severity="success" :value="`${p.offer_id} · ${p.channel}`" />
          <small class="muted">from {{ p.rule_id }}</small>
        </li>
      </ul>
    </section>
    <section v-if="blocked.length">
      <h4>Blocked</h4>
      <ul class="tags">
        <li v-for="[target, rule] in blocked" :key="target">
          <Tag severity="danger" :value="target === 'all' ? 'All offers' : target" />
          <small class="muted">by {{ rule }}</small>
        </li>
      </ul>
    </section>
    <section>
      <h4>Rules fired, in order</h4>
      <p v-if="!outcome.firings.length" class="muted">No rule matched.</p>
      <ol v-else class="firings">
        <li v-for="f in outcome.firings" :key="f.rule_id">
          <strong>{{ f.rule_id }}</strong> {{ f.description }}
          <div class="muted small">{{ f.effect }} · because {{ facts(f.facts_matched) }}</div>
        </li>
      </ol>
    </section>
  </div>
</template>

<style scoped>
.trace { display: flex; flex-direction: column; gap: 0.75rem; }
h4 { margin: 0 0 0.35rem; font-size: 0.9rem; }
.tags { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 0.5rem 1rem; }
.tags li { display: flex; gap: 0.35rem; align-items: center; }
.firings { margin: 0; padding-left: 1.2rem; display: flex; flex-direction: column; gap: 0.4rem; font-size: 0.9rem; }
.small { font-size: 0.8rem; }
</style>
