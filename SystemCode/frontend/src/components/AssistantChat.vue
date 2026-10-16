<script setup lang="ts">
import { ArrowUp, CalendarCheck, ListOrdered, ThumbsDown, ThumbsUp, Gift, Network, RotateCcw, Scale, Sparkles, TrendingDown, TriangleAlert, UserRound } from 'lucide-vue-next'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import { computed, nextTick, ref, watch, type Component } from 'vue'
import type { AssistantReply } from '../api/types'
import { useToast } from 'primevue/usetoast'
import { errorMessage } from '../composables/useAsync'
import { useAssistantStore, type Turn } from '../stores/assistant'
import { useAuthStore } from '../stores/auth'
import AssistantAnswer from './AssistantAnswer.vue'

const props = defineProps<{ memberId?: string | null; compact?: boolean }>()
const toast = useToast()

async function rate(turn: Turn, rating: 1 | -1) {
  try {
    await store.rate(turn, rating)
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Feedback not saved', detail: errorMessage(e), life: 4000 })
  }
}

const INTENT_LABELS: Record<string, string> = {
  member_risk: 'Member risk',
  member_actions: 'Member actions',
  compare_members: 'Compare members',
  graph_impact: 'Graph impact',
  list_members: 'Member list',
  plan_summary: 'Plan summary',
  what_if_budget: 'What-if budget',
  unknown: 'Not understood',
}
const TOOL_LABELS: Record<string, string> = {
  member_risk: 'Churn model',
  member_actions: 'Rule trace',
  compare_members: 'Churn model + rule trace',
  graph_impact: 'Knowledge graph',
  list_members: 'Member ranking',
  plan_summary: 'Weekly plan',
  what_if_budget: 'Plan optimiser',
}
const EXAMPLE_MEMBER = 'M0155'

const store = useAssistantStore()
const auth = useAuthStore()
const text = ref('')
const scroller = ref<HTMLElement | null>(null)

const pageMember = computed(() => props.memberId ?? null)
const focus = computed(() => store.focus(pageMember.value))
const isManager = computed(() => auth.hasRole(['manager', 'admin']))

const intro = computed(() =>
  isManager.value
    ? "Ask about a member's risk, what to offer them, who an instructor leaving affects, or this week's plan."
    : "Ask about a member's risk, what to offer them, or who an instructor leaving affects.",
)

const starters = computed(() => {
  const m = focus.value ?? EXAMPLE_MEMBER
  const other = m === EXAMPLE_MEMBER ? 'M0042' : EXAMPLE_MEMBER
  const out: { text: string; icon: Component }[] = [
    { text: `Why is ${m} at risk?`, icon: TrendingDown },
    { text: `What should we offer ${m}?`, icon: Gift },
    { text: `Compare ${m} with ${other}`, icon: Scale },
    { text: 'Who are the top 10 members at risk?', icon: ListOrdered },
    { text: 'Who is affected by Maya Chen leaving?', icon: Network },
  ]
  if (isManager.value) out.push({ text: "What's in this week's plan?", icon: CalendarCheck })
  return out
})

// Next questions that make sense after the latest answer.
function followUps(reply: AssistantReply): string[] {
  const [a, b] = reply.slots.member_ids
  switch (reply.intent) {
    case 'member_risk':
      return [`What should we offer ${a}?`, 'Explain that more simply']
    case 'member_actions':
      return [`Why is ${a} at risk?`, 'Why those offers?']
    case 'compare_members':
      return [`What should we offer ${a}?`, `What should we offer ${b}?`]
    case 'list_members':
    case 'graph_impact': {
      const top = reply.evidence.find((e) => e.kind === 'member' && e.ref)?.ref
      return top ? [`Why is ${top} at risk?`, `What should we offer ${top}?`] : []
    }
    default:
      return []
  }
}

const lastReply = computed(() => store.turns.at(-1)?.reply ?? null)

async function send(question = text.value) {
  if (!question.trim() || store.busy) return
  text.value = ''
  await store.ask(question, pageMember.value)
}

function onEnter(e: KeyboardEvent) {
  if (e.shiftKey || e.isComposing) return
  e.preventDefault()
  send()
}

watch(
  () => [store.turns.length, store.busy],
  async () => {
    await nextTick()
    scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' })
  },
  { immediate: true },
)
</script>

<template>
  <div class="chat" :class="{ compact }">
    <div class="bar">
      <span v-if="focus" class="focus">
        <UserRound :size="14" aria-hidden="true" />
        Talking about
        <RouterLink :to="`/members/${encodeURIComponent(focus)}`">{{ focus }}</RouterLink>
      </span>
      <span v-else class="text-ink-500">No member selected</span>
      <Button v-if="store.turns.length" label="New chat" size="small" text severity="secondary" @click="store.reset()">
        <template #icon><RotateCcw :size="14" /></template>
      </Button>
    </div>

    <div ref="scroller" class="scroll" aria-live="polite">
      <div class="column">
        <div v-if="!store.turns.length" class="empty">
          <span class="hero-mark" aria-hidden="true"><Sparkles :size="compact ? 22 : 28" /></span>
          <h2 class="m-0 font-semibold text-ink-900" :class="compact ? 'text-lg' : 'text-2xl'">How can I help?</h2>
          <p>{{ intro }} Answers come only from AnchorAI's data, with the sources marked.</p>
          <div class="starters">
            <button v-for="s in starters" :key="s.text" type="button" class="starter" @click="send(s.text)">
              <component :is="s.icon" :size="16" class="shrink-0 text-brand-600" aria-hidden="true" />
              <span>{{ s.text }}</span>
            </button>
          </div>
        </div>

        <template v-for="t in store.turns" :key="t.id">
          <div class="row user">
            <div class="bubble user">{{ t.question }}</div>
          </div>
          <div class="row bot">
            <span class="avatar" aria-hidden="true"><Sparkles :size="15" /></span>
            <div class="bubble bot">
              <div v-if="!t.reply && !t.error" class="typing" aria-label="Thinking"><i /><i /><i /></div>
              <p v-else-if="t.error" class="error"><TriangleAlert :size="15" aria-hidden="true" /> {{ t.error }}</p>
              <template v-else-if="t.reply">
                <AssistantAnswer :answer="t.reply.answer" :evidence="t.reply.evidence" />
                <div class="meta">
                  <span class="intent">{{ INTENT_LABELS[t.reply.intent] ?? t.reply.intent }}</span>
                  <span v-if="t.reply.tool" title="The data source the answer came from">via {{ TOOL_LABELS[t.reply.tool] ?? t.reply.tool }}</span>
                  <span v-if="t.reply.follow_up">Follow-up</span>
                  <span v-if="!t.reply.grounded" class="warn">No evidence found</span>
                  <span v-else-if="!t.reply.llm_used" class="warn" title="The language model is offline, so the evidence is shown as is">
                    Language model offline
                  </span>
                  <template v-if="t.reply.grounded">
                    <span class="grow !bg-transparent !p-0" />
                    <button
                      v-for="r in ([1, -1] as const)"
                      :key="r"
                      type="button"
                      class="rate"
                      :class="{ on: t.rated === r }"
                      :disabled="!!t.rated"
                      :aria-pressed="t.rated === r"
                      :aria-label="r === 1 ? 'Helpful' : 'Not helpful'"
                      :title="r === 1 ? 'Helpful' : 'Not helpful'"
                      @click="rate(t, r)"
                    >
                      <component :is="r === 1 ? ThumbsUp : ThumbsDown" :size="14" aria-hidden="true" />
                    </button>
                  </template>
                </div>
              </template>
            </div>
          </div>
        </template>

        <div v-if="lastReply && !store.busy && followUps(lastReply).length" class="chips next">
          <button v-for="s in followUps(lastReply)" :key="s" type="button" class="chip" @click="send(s)">{{ s }}</button>
        </div>
      </div>
    </div>

    <div class="column">
      <form class="composer" @submit.prevent="send()">
        <label for="assistant-input" class="sr-only">Ask the assistant</label>
        <Textarea
          id="assistant-input"
          v-model="text"
          rows="1"
          auto-resize
          maxlength="1000"
          :placeholder="focus ? `Ask about ${focus}, another member, the plan or the graph` : 'Ask about a member, the plan or the graph'"
          @keydown.enter="onEnter"
        />
        <button type="submit" class="send" :disabled="!text.trim() || store.busy" aria-label="Send">
          <ArrowUp :size="18" stroke-width="2.5" aria-hidden="true" />
        </button>
      </form>
      <small class="hint">Enter to send · Shift+Enter for a new line · a refresh clears the chat</small>
    </div>
  </div>
</template>

<style scoped>
.chat { display: flex; flex-direction: column; flex: 1; min-height: 0; gap: 0.75rem; }
.column { width: 100%; max-width: 52rem; margin-inline: auto; }
.compact .column { max-width: none; }
.bar { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; min-height: 2rem; font-size: 0.8125rem; }
.focus { display: inline-flex; gap: 0.35rem; align-items: center; padding: 0.3rem 0.7rem; border-radius: 999px; background: var(--color-brand-50); color: var(--color-ink-600); }
.focus a { color: var(--color-brand-700); font-weight: 600; text-decoration: none; }
.focus a:hover { text-decoration: underline; }
.scroll { flex: 1; min-height: 0; overflow-y: auto; padding: 0.25rem 0.25rem 0.5rem; scrollbar-gutter: stable; }
.scroll > .column { display: flex; flex-direction: column; gap: 1.1rem; min-height: 100%; }
.empty { margin: auto 0; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0.75rem; padding: 1.5rem 0.5rem; color: var(--color-ink-500); }
.empty p { margin: 0; max-width: 36rem; line-height: 1.55; font-size: 0.9375rem; }
.hero-mark { display: grid; place-items: center; width: 3.5rem; height: 3.5rem; border-radius: 1.1rem; color: #fff; background: linear-gradient(135deg, #347ef6, #1a3fac); box-shadow: var(--shadow-fab); margin-bottom: 0.25rem; }
.compact .hero-mark { width: 2.75rem; height: 2.75rem; border-radius: 0.9rem; }
.starters { display: grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); gap: 0.6rem; width: 100%; max-width: 44rem; margin-top: 0.75rem; }
.compact .starters { grid-template-columns: 1fr; }
.starter {
  display: flex; align-items: center; gap: 0.65rem; padding: 0.75rem 0.9rem; text-align: left;
  border: 1px solid var(--color-ink-200); border-radius: 0.75rem; background: var(--color-card); color: var(--color-ink-700);
  font: 500 0.875rem/1.35 var(--font-sans); cursor: pointer; transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
}
.starter:hover, .starter:focus-visible { border-color: var(--color-brand-300); box-shadow: var(--shadow-raised); transform: translateY(-1px); }
.starter:focus-visible, .chip:focus-visible { outline: 2px solid var(--color-brand-500); outline-offset: 2px; }
.chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.chips.next { padding-left: 0; }
.chip {
  font: 500 0.8125rem/1 var(--font-sans); padding: 0.5rem 0.8rem; border-radius: 999px; cursor: pointer;
  border: 1px solid var(--color-brand-200); background: var(--color-brand-50); color: var(--color-brand-800);
}
.chip:hover, .chip:focus-visible { background: var(--color-brand-100); border-color: var(--color-brand-300); }
.row { display: flex; gap: 0.6rem; align-items: flex-start; }
.row.user { justify-content: flex-end; }
.avatar { flex: none; display: none; place-items: center; width: 2rem; height: 2rem; border-radius: 0.6rem; color: #fff; background: linear-gradient(135deg, #347ef6, #1a3fac); }
.bubble { max-width: min(88%, 44rem); padding: 0.7rem 0.95rem; border-radius: 1rem; overflow-wrap: anywhere; font-size: 0.9375rem; }
.compact .bubble { font-size: 0.875rem; }
.bubble.user { background: var(--color-brand-600); color: #fff; border-bottom-right-radius: 0.3rem; white-space: pre-wrap; }
.bubble.bot { background: var(--color-card); border: 1px solid var(--color-ink-200); border-top-left-radius: 0.3rem; box-shadow: var(--shadow-card); color: var(--color-ink-800); }
.error { margin: 0; display: flex; gap: 0.4rem; align-items: center; color: var(--color-danger); }
.meta { display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem; margin-top: 0.6rem; font-size: 0.72rem; color: var(--color-ink-500); }
.meta > span { padding: 0.15rem 0.5rem; border-radius: 999px; background: var(--color-ink-100); }
.meta .intent { background: var(--color-brand-50); color: var(--color-brand-800); font-weight: 600; }
.rate { display: grid; place-items: center; width: 1.6rem; height: 1.6rem; border: 0; border-radius: 6px; background: none; color: var(--color-ink-500); cursor: pointer; }
.rate:hover:not(:disabled) { background: var(--color-ink-100); color: var(--color-ink-800); }
.rate:focus-visible { outline: 2px solid var(--color-brand-500); outline-offset: 1px; }
.rate:disabled { cursor: default; opacity: 0.45; }
.rate.on { opacity: 1; color: var(--color-brand-600); }
.meta .warn { background: var(--color-warn-soft); color: var(--color-warn-ink); }
.typing { display: flex; gap: 0.3rem; padding: 0.35rem 0.1rem; }
.typing i { width: 0.45rem; height: 0.45rem; border-radius: 50%; background: var(--color-brand-400); opacity: 0.35; animation: blink 1.2s infinite; }
.typing i:nth-child(2) { animation-delay: 0.2s; }
.typing i:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 30% { opacity: 1; transform: translateY(-2px); } }
.composer {
  display: flex; gap: 0.5rem; align-items: flex-end; padding: 0.5rem 0.5rem 0.5rem 0.25rem;
  border: 1px solid var(--color-ink-300); border-radius: 1rem; background: var(--color-card); box-shadow: var(--shadow-raised);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.composer:focus-within { border-color: var(--color-brand-500); box-shadow: 0 0 0 4px color-mix(in srgb, var(--color-brand-500) 15%, transparent), var(--shadow-raised); }
.composer :deep(textarea) { flex: 1; border: 0; box-shadow: none; resize: none; max-height: 10rem; overflow-y: auto; background: transparent; font-size: 0.9375rem; }
.composer :deep(textarea:focus) { box-shadow: none; }
.send { flex: none; display: grid; place-items: center; width: 2.4rem; height: 2.4rem; border: 0; border-radius: 0.7rem; background: var(--color-brand-600); color: #fff; cursor: pointer; transition: background 0.15s; }
.send:hover:not(:disabled) { background: #184bd5; }
.send:disabled { background: var(--color-ink-200); color: var(--color-ink-400); cursor: default; }
.hint { display: none; margin-top: 0.5rem; font-size: 0.72rem; text-align: center; color: var(--color-ink-400); }
@media (min-width: 640px) { .hint { display: block; } .avatar { display: grid; } .chips.next { padding-left: 2.6rem; } }
</style>
