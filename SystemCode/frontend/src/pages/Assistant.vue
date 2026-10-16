<script setup lang="ts">
import { CalendarCheck, Gift, Network, Scale, ShieldCheck, TrendingDown } from 'lucide-vue-next'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AssistantChat from '../components/AssistantChat.vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()
const memberId = computed(() => (typeof route.query.member === 'string' ? route.query.member : null))

const skills = computed(() => [
  { icon: TrendingDown, title: 'Member risk', text: 'Why a member is likely to leave, from the churn model and rules.' },
  { icon: Gift, title: 'What to offer', text: 'Allowed offers and channels after guardrails.' },
  { icon: Scale, title: 'Compare members', text: 'Two members side by side.' },
  { icon: Network, title: 'Graph impact', text: 'Who an instructor leaving or a class closing affects.' },
  ...(auth.hasRole(['manager', 'admin'])
    ? [{ icon: CalendarCheck, title: 'Weekly plan', text: "What's in this week's plan." }]
    : []),
])

const SOURCES = [
  { kind: 'member', label: 'Member data' },
  { kind: 'rule', label: 'Rule' },
  { kind: 'offer', label: 'Offer' },
  { kind: 'event', label: 'Graph event' },
  { kind: 'plan', label: 'Weekly plan' },
]
</script>

<template>
  <div class="assistant-page page">
    <section class="chat-panel" aria-label="Assistant chat">
      <AssistantChat :member-id="memberId" />
    </section>

    <aside class="rail" aria-label="About the assistant">
      <div class="rail-card">
        <h2 class="rail-title">What I can answer</h2>
        <ul class="m-0 flex list-none flex-col gap-3 p-0">
          <li v-for="s in skills" :key="s.title" class="flex gap-3">
            <span class="grid size-8 shrink-0 place-items-center rounded-lg bg-brand-50 text-brand-600">
              <component :is="s.icon" :size="16" aria-hidden="true" />
            </span>
            <div class="min-w-0">
              <p class="m-0 text-sm font-semibold text-ink-800">{{ s.title }}</p>
              <p class="m-0 text-xs leading-relaxed text-ink-500">{{ s.text }}</p>
            </div>
          </li>
        </ul>
      </div>
      <div class="rail-card">
        <h2 class="rail-title">Reading the sources</h2>
        <p class="m-0 mb-3 text-xs leading-relaxed text-ink-500">
          Numbered chips in an answer point to the evidence behind it. Hover for a summary; click to open it.
        </p>
        <ul class="m-0 grid list-none grid-cols-2 gap-2 p-0">
          <li v-for="s in SOURCES" :key="s.kind" class="flex items-center gap-2 text-xs text-ink-600">
            <span class="legend-dot" :class="`k-${s.kind}`" aria-hidden="true">1</span>{{ s.label }}
          </li>
        </ul>
      </div>
      <div class="rail-card flex gap-3">
        <ShieldCheck :size="18" class="mt-0.5 shrink-0 text-success" aria-hidden="true" />
        <p class="m-0 text-xs leading-relaxed text-ink-600">
          Answers use only AnchorAI's own data: the plan, explanations, rule traces and the knowledge graph. When nothing
          supports an answer, the assistant says it doesn't know.
        </p>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.assistant-page {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1.25rem;
  height: calc(100dvh - var(--topbar-h) - var(--main-pt) - var(--main-pb));
  min-height: 30rem;
}
.chat-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 1rem 1.25rem 1rem;
  background: var(--color-card);
  border: 1px solid var(--color-ink-200);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}
.rail { display: none; }
@media (min-width: 1280px) {
  .assistant-page { grid-template-columns: minmax(0, 1fr) 19rem; }
  .rail { display: flex; flex-direction: column; gap: 1rem; overflow-y: auto; }
}
@media (min-width: 1880px) {
  .assistant-page { grid-template-columns: minmax(0, 1fr) 21rem; }
}
@media (max-width: 639.98px) {
  .chat-panel { padding: 0.75rem; }
}
.rail-card { padding: 1rem 1.1rem; background: var(--color-card); border: 1px solid var(--color-ink-200); border-radius: var(--radius-card); }
.rail-title { margin: 0 0 0.75rem; font-size: 0.8125rem; font-weight: 600; color: var(--color-ink-900); }
.legend-dot {
  --c: var(--color-ev-member);
  display: inline-grid; place-items: center; min-width: 1.2rem; height: 1.1rem; padding: 0 0.3rem; border-radius: 999px;
  font-size: 0.65rem; font-weight: 700; color: var(--c);
  background: color-mix(in srgb, var(--c) 10%, transparent); border: 1px solid color-mix(in srgb, var(--c) 30%, transparent);
}
.k-member { --c: var(--color-ev-member); }
.k-rule { --c: var(--color-ev-rule); }
.k-offer { --c: var(--color-ev-offer); }
.k-event { --c: var(--color-ev-event); }
.k-plan { --c: var(--color-ev-plan); }
</style>
