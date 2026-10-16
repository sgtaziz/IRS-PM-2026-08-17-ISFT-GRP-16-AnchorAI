<script setup lang="ts">
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { nextTick, ref } from 'vue'
import { api } from '../api/client'
import type { AssistantReply, Evidence } from '../api/types'
import { errorMessage } from '../composables/useAsync'

const props = defineProps<{ memberId?: string | null }>()

interface Turn {
  question: string
  reply: AssistantReply | null
  error: string | null
  rated: 1 | -1 | null
}

const SUGGESTIONS = [
  'Why is M0155 at risk?',
  'What should we offer M0155?',
  'Who is affected by Maya Chen leaving?',
  "What's in this week's plan?",
]
const INTENT_LABELS: Record<string, string> = {
  member_risk: 'Member risk',
  member_actions: 'Member actions',
  compare_members: 'Compare members',
  graph_impact: 'Graph impact',
  plan_summary: 'Plan summary',
  what_if_budget: 'What-if budget',
  unknown: 'Not understood',
}

const toast = useToast()
const turns = ref<Turn[]>([])
const text = ref('')
const busy = ref(false)
const log = ref<HTMLElement | null>(null)

async function ask(question = text.value) {
  question = question.trim()
  if (!question || busy.value) return
  text.value = ''
  const turn: Turn = { question, reply: null, error: null, rated: null }
  turns.value.push(turn)
  busy.value = true
  try {
    turn.reply = await api<AssistantReply>('/assistant/chat', {
      method: 'POST',
      body: JSON.stringify({ message: question, member_id: props.memberId || null }),
    })
  } catch (e) {
    turn.error = errorMessage(e)
  } finally {
    busy.value = false
    turns.value = [...turns.value]
    await nextTick()
    log.value?.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }
}

async function rate(turn: Turn, rating: 1 | -1) {
  if (!turn.reply || turn.rated) return
  try {
    await api('/assistant/feedback', {
      method: 'POST',
      body: JSON.stringify({
        message: turn.question,
        answer: turn.reply.answer,
        intent: turn.reply.intent,
        tool: turn.reply.tool,
        rating,
      }),
    })
    turn.rated = rating
    turns.value = [...turns.value]
  } catch (e) {
    toast.add({ severity: 'error', summary: 'Feedback not saved', detail: errorMessage(e), life: 4000 })
  }
}

function link(e: Evidence) {
  return e.kind === 'member' && e.ref ? `/members/${e.ref}` : null
}
</script>

<template>
  <div class="chat">
    <p v-if="memberId" class="muted context">Asking about <strong>{{ memberId }}</strong> unless you name another member.</p>
    <div v-if="!turns.length" class="suggestions">
      <span class="muted">Try:</span>
      <Button v-for="s in SUGGESTIONS" :key="s" :label="s" size="small" severity="secondary" outlined @click="ask(s)" />
    </div>
    <ol ref="log" class="log" aria-live="polite">
      <li v-for="(t, i) in turns" :key="i" class="turn">
        <div class="question">{{ t.question }}</div>
        <div v-if="!t.reply && !t.error" class="muted">Thinking…</div>
        <Message v-else-if="t.error" severity="error" :closable="false">{{ t.error }}</Message>
        <div v-else-if="t.reply" class="answer">
          <p>{{ t.reply.answer }}</p>
          <div class="meta">
            <Tag :value="INTENT_LABELS[t.reply.intent] ?? t.reply.intent" severity="secondary" />
            <small class="muted">confidence {{ t.reply.score.toFixed(2) }}</small>
            <small v-if="t.reply.tool" class="muted">· tool {{ t.reply.tool }}</small>
            <Tag v-if="!t.reply.grounded" value="No evidence" severity="warn" />
            <Tag v-else-if="!t.reply.llm_used" value="LLM offline: evidence shown as is" severity="warn" />
          </div>
          <details v-if="t.reply.evidence.length" class="evidence">
            <summary>Evidence ({{ t.reply.evidence.length }})</summary>
            <ul>
              <li v-for="e in t.reply.evidence" :key="e.id">
                <span class="eid">{{ e.id }}</span>
                <RouterLink v-if="link(e)" :to="link(e)!">{{ e.text }}</RouterLink>
                <span v-else>{{ e.text }}</span>
              </li>
            </ul>
          </details>
          <div class="rate">
            <Button
              label="Helpful"
              size="small"
              text
              :disabled="!!t.rated"
              :severity="t.rated === 1 ? 'success' : 'secondary'"
              @click="rate(t, 1)"
            />
            <Button
              label="Not helpful"
              size="small"
              text
              :disabled="!!t.rated"
              :severity="t.rated === -1 ? 'danger' : 'secondary'"
              @click="rate(t, -1)"
            />
          </div>
        </div>
      </li>
    </ol>
    <form class="ask" @submit.prevent="ask()">
      <label for="assistant-input" class="sr-only">Ask the assistant</label>
      <InputText id="assistant-input" v-model="text" placeholder="Ask about a member, the plan or the graph" fluid :disabled="busy" />
      <Button type="submit" label="Ask" :loading="busy" :disabled="!text.trim()" />
    </form>
  </div>
</template>

<style scoped>
.chat { display: flex; flex-direction: column; gap: 0.75rem; }
.context { margin: 0; font-size: 0.85rem; }
.suggestions { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
.log { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 1rem; }
.question { font-weight: 600; margin-bottom: 0.35rem; }
.answer p { margin: 0 0 0.4rem; line-height: 1.45; }
.meta { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; }
.evidence { margin-top: 0.4rem; font-size: 0.85rem; }
.evidence ul { margin: 0.3rem 0 0; padding-left: 0; list-style: none; display: flex; flex-direction: column; gap: 0.2rem; }
.eid { display: inline-block; min-width: 2.2rem; color: var(--muted); font-weight: 600; }
.rate { display: flex; gap: 0.25rem; }
.ask { display: flex; gap: 0.5rem; }
</style>
