import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'
import { api } from '../api/client'
import type { AssistantReply, HistoryTurn } from '../api/types'
import { errorMessage } from '../composables/useAsync'

export interface Turn {
  id: number
  question: string
  // The member page it was asked from, so moving to another member's page changes the focus.
  pageMember: string | null
  reply: AssistantReply | null
  error: string | null
  rated: 1 | -1 | null
}

const HISTORY_TURNS = 4

// One chat shared by the assistant page and the drawer. In memory only: a refresh starts over.
export const useAssistantStore = defineStore('assistant', () => {
  const turns = ref<Turn[]>([])
  const busy = ref(false)
  let nextId = 0
  // Bumped by reset, so a reply that arrives after "New chat" or logout is dropped.
  let generation = 0

  /** The member a question that names none is about: the open page's, or the chat's last one. */
  function focus(pageMember: string | null): string | null {
    const last = [...turns.value].reverse().find((t) => t.reply?.slots.member_ids.length)
    if (pageMember && (!last || last.pageMember !== pageMember)) return pageMember
    return last?.reply?.slots.member_ids.at(-1) ?? pageMember
  }

  async function ask(question: string, pageMember: string | null) {
    question = question.trim()
    if (!question || busy.value) return
    const history: HistoryTurn[] = turns.value
      .filter((t) => t.reply)
      .slice(-HISTORY_TURNS)
      .map((t) => ({ question: t.question, answer: t.reply!.answer, intent: t.reply!.intent, slots: t.reply!.slots }))
    const memberId = focus(pageMember)
    const turn = reactive<Turn>({ id: nextId++, question, pageMember, reply: null, error: null, rated: null })
    turns.value.push(turn)
    busy.value = true
    const started = generation
    try {
      turn.reply = await api<AssistantReply>('/assistant/chat', {
        method: 'POST',
        body: JSON.stringify({ message: question, member_id: memberId, history }),
      })
    } catch (e) {
      turn.error = errorMessage(e)
    } finally {
      if (started === generation) busy.value = false
    }
  }

  /** Thumbs up or down, logged for the assistant evaluation (PLAN W30). */
  async function rate(turn: Turn, rating: 1 | -1) {
    if (!turn.reply || turn.rated) return
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
  }

  function reset() {
    generation++
    busy.value = false
    turns.value = []
  }

  return { turns, busy, focus, ask, rate, reset }
})
