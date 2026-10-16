<script setup lang="ts">
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import { computed, nextTick, ref, watch } from 'vue'
import type { AssistantReply } from '../api/types'
import { useAssistantStore } from '../stores/assistant'
import { useAuthStore } from '../stores/auth'
import AssistantAnswer from './AssistantAnswer.vue'

const props = defineProps<{ memberId?: string | null }>()

const INTENT_LABELS: Record<string, string> = {
  member_risk: 'Member risk',
  member_actions: 'Member actions',
  compare_members: 'Compare members',
  graph_impact: 'Graph impact',
  plan_summary: 'Plan summary',
  what_if_budget: 'What-if budget',
  unknown: 'Not understood',
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
  const out = [`Why is ${m} at risk?`, `What should we offer ${m}?`, `Compare ${m} with ${other}`]
  out.push('Who is affected by Maya Chen leaving?')
  if (isManager.value) out.push("What's in this week's plan?")
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
  <div class="chat">
    <div class="bar">
      <span v-if="focus" class="focus">
        Talking about
        <RouterLink :to="`/members/${encodeURIComponent(focus)}`">{{ focus }}</RouterLink>
      </span>
      <span v-else class="muted">No member selected</span>
      <Button v-if="store.turns.length" label="New chat" size="small" text severity="secondary" @click="store.reset()" />
    </div>

    <div ref="scroller" class="scroll" aria-live="polite">
      <div v-if="!store.turns.length" class="empty">
        <div class="avatar big" aria-hidden="true">A</div>
        <p>{{ intro }} Answers come only from AnchorAI's data, with the sources marked.</p>
        <div class="chips">
          <button v-for="s in starters" :key="s" type="button" class="chip" @click="send(s)">{{ s }}</button>
        </div>
      </div>

      <template v-for="t in store.turns" :key="t.id">
        <div class="row user">
          <div class="bubble user">{{ t.question }}</div>
        </div>
        <div class="row bot">
          <div class="avatar" aria-hidden="true">A</div>
          <div class="bubble bot">
            <div v-if="!t.reply && !t.error" class="typing" aria-label="Thinking"><i /><i /><i /></div>
            <p v-else-if="t.error" class="error">{{ t.error }}</p>
            <template v-else-if="t.reply">
              <AssistantAnswer :answer="t.reply.answer" :evidence="t.reply.evidence" />
              <div class="meta">
                <span>{{ INTENT_LABELS[t.reply.intent] ?? t.reply.intent }}</span>
                <span v-if="t.reply.follow_up">· follow-up</span>
                <span v-if="!t.reply.grounded" class="warn">· no evidence</span>
                <span v-else-if="!t.reply.llm_used" class="warn" title="The language model is offline, so the evidence is shown as is">
                  · LLM offline
                </span>
              </div>
            </template>
          </div>
        </div>
      </template>

      <div v-if="lastReply && !store.busy && followUps(lastReply).length" class="chips next">
        <button v-for="s in followUps(lastReply)" :key="s" type="button" class="chip" @click="send(s)">{{ s }}</button>
      </div>
    </div>

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
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.4 20.4 21 12 3.4 3.6 3.4 10l12.6 2-12.6 2z" /></svg>
      </button>
    </form>
    <small class="hint muted">Enter to send · Shift+Enter for a new line · a refresh clears the chat</small>
  </div>
</template>

<style scoped>
.chat { display: flex; flex-direction: column; flex: 1; min-height: 0; gap: 0.5rem; }
.bar { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; min-height: 2rem; font-size: 0.85rem; }
.focus { display: inline-flex; gap: 0.3rem; align-items: center; padding: 0.2rem 0.6rem; border-radius: 999px; background: color-mix(in srgb, var(--accent) 10%, transparent); color: var(--muted); }
.focus a { color: var(--accent); font-weight: 600; text-decoration: none; }
.scroll { flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 0.75rem; padding: 0.25rem 0.25rem 0.5rem; }
.empty { margin: auto 0; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0.75rem; padding: 1rem; color: var(--muted); }
.empty p { margin: 0; max-width: 34rem; line-height: 1.5; }
.chips { display: flex; flex-wrap: wrap; gap: 0.4rem; justify-content: center; }
.chips.next { justify-content: flex-start; padding-left: 2.4rem; }
.chip { font: inherit; font-size: 0.82rem; padding: 0.35rem 0.75rem; border-radius: 999px; border: 1px solid var(--border); background: var(--surface); color: var(--text); cursor: pointer; }
.chip:hover, .chip:focus-visible { border-color: var(--accent); color: var(--accent); outline: none; }
.row { display: flex; gap: 0.5rem; align-items: flex-end; }
.row.user { justify-content: flex-end; }
.avatar { flex: none; width: 1.9rem; height: 1.9rem; border-radius: 50%; display: grid; place-items: center; background: var(--nav); color: #fff; font-weight: 700; font-size: 0.8rem; }
.avatar.big { width: 2.75rem; height: 2.75rem; font-size: 1.1rem; }
.bubble { max-width: min(85%, 40rem); padding: 0.6rem 0.85rem; border-radius: 14px; overflow-wrap: anywhere; }
.bubble.user { background: var(--accent); color: #fff; border-bottom-right-radius: 4px; white-space: pre-wrap; }
.bubble.bot { background: var(--surface); border: 1px solid var(--border); border-bottom-left-radius: 4px; }
.error { margin: 0; color: #b42318; }
.meta { display: flex; align-items: center; gap: 0.3rem; margin-top: 0.35rem; font-size: 0.72rem; color: var(--muted); }
.meta .warn { color: #b25e09; }
.typing { display: flex; gap: 0.25rem; padding: 0.3rem 0.1rem; }
.typing i { width: 0.45rem; height: 0.45rem; border-radius: 50%; background: var(--muted); opacity: 0.4; animation: blink 1.2s infinite; }
.typing i:nth-child(2) { animation-delay: 0.2s; }
.typing i:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 30% { opacity: 1; transform: translateY(-2px); } }
.composer { display: flex; gap: 0.5rem; align-items: flex-end; padding: 0.4rem; border: 1px solid var(--border); border-radius: 14px; background: var(--surface); }
.composer:focus-within { border-color: var(--accent); }
.composer :deep(textarea) { flex: 1; border: 0; box-shadow: none; resize: none; max-height: 9rem; overflow-y: auto; background: transparent; }
.send { flex: none; display: grid; place-items: center; width: 2.25rem; height: 2.25rem; border: 0; border-radius: 10px; background: var(--accent); color: #fff; cursor: pointer; }
.send svg { width: 1.1rem; height: 1.1rem; fill: currentColor; }
.send:disabled { opacity: 0.4; cursor: default; }
.hint { font-size: 0.72rem; text-align: center; }
</style>
