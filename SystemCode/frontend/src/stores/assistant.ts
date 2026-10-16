import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'
import { api, ApiError, apiStream } from '../api/client'
import type { AssistantReply, AssistantStreamDone, AssistantStreamMeta, HistoryTurn } from '../api/types'
import { errorMessage } from '../composables/useAsync'

export interface Turn {
  id: number
  question: string
  // The member page it was asked from, so moving to another member's page changes the focus.
  pageMember: string | null
  reply: AssistantReply | null
  error: string | null
  rated: 1 | -1 | null
  // True while the answer text is still arriving.
  streaming: boolean
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

  async function stream(turn: Turn, body: string) {
    let finished = false
    turn.reply = null
    await apiStream('/assistant/chat/stream', { method: 'POST', body }, (event, data) => {
      if (event === 'meta') {
        turn.reply = { ...(data as AssistantStreamMeta), answer: '', grounded: false, llm_used: false }
      } else if (event === 'delta' && turn.reply) {
        turn.reply.answer += (data as { text: string }).text
      } else if (event === 'done' && turn.reply) {
        Object.assign(turn.reply, data as AssistantStreamDone)
        finished = true
      }
    })
    if (!finished) throw new Error('The answer stream ended early')
  }

  async function ask(question: string, pageMember: string | null) {
    question = question.trim()
    if (!question || busy.value) return
    const history: HistoryTurn[] = turns.value
      .filter((t) => t.reply)
      .slice(-HISTORY_TURNS)
      .map((t) => ({ question: t.question, answer: t.reply!.answer, intent: t.reply!.intent, slots: t.reply!.slots }))
    const memberId = focus(pageMember)
    const turn = reactive<Turn>({ id: nextId++, question, pageMember, reply: null, error: null, rated: null, streaming: false })
    turns.value.push(turn)
    busy.value = true
    const started = generation
    const body = JSON.stringify({ message: question, member_id: memberId, history })
    try {
      try {
        turn.streaming = true
        await stream(turn, body)
      } catch (e) {
        // The server's own errors (auth, 503) would repeat on /chat; a broken stream may not.
        if (e instanceof ApiError) throw e
        turn.streaming = false
        turn.reply = null
        turn.reply = await api<AssistantReply>('/assistant/chat', { method: 'POST', body })
      }
    } catch (e) {
      turn.error = errorMessage(e)
    } finally {
      turn.streaming = false
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
