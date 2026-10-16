<script setup lang="ts">
import vTooltip from 'primevue/tooltip'
import { computed, nextTick, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { Evidence } from '../api/types'

const props = defineProps<{ answer: string; evidence: Evidence[] }>()

type Inline = { type: 'text' | 'bold'; text: string } | { type: 'cite'; ids: string[] }
interface Block {
  list: boolean
  lines: Inline[][]
}

const KIND_LABELS: Record<Evidence['kind'], string> = {
  member: 'Member data',
  rule: 'Rule',
  offer: 'Offer',
  event: 'Graph event',
  plan: 'Weekly plan',
}

const router = useRouter()
const open = ref(false)
const highlighted = ref<string | null>(null)
const sources = ref<HTMLElement | null>(null)
const byId = computed(() => new Map(props.evidence.map((e) => [e.id, e])))

function inline(line: string): Inline[] {
  const out: Inline[] = []
  let at = 0
  for (const m of line.matchAll(/\*\*(.+?)\*\*|((?:\s*\[E\d+\])+)/g)) {
    if (m.index > at) out.push({ type: 'text', text: line.slice(at, m.index) })
    if (m[1]) out.push({ type: 'bold', text: m[1] })
    else {
      const ids = (m[2].match(/E\d+/g) ?? []).filter((id) => byId.value.has(id))
      if (ids.length) out.push({ type: 'cite', ids })
    }
    at = m.index + m[0].length
  }
  if (at < line.length) out.push({ type: 'text', text: line.slice(at) })
  return out
}

// Paragraphs and "- " bullet lists; nothing else is rendered as markup.
const blocks = computed(() => {
  const out: Block[] = []
  let para: string[] = []
  const flush = () => {
    if (para.length) out.push({ list: false, lines: [inline(para.join(' '))] })
    para = []
  }
  for (const raw of props.answer.split('\n')) {
    const line = raw.trim()
    const bullet = line.match(/^(?:[-*•]|\d+\.)\s+(.*)$/)
    if (bullet) {
      flush()
      const last = out.at(-1)
      if (last?.list) last.lines.push(inline(bullet[1]))
      else out.push({ list: true, lines: [inline(bullet[1])] })
    } else if (line) para.push(line)
    else flush()
  }
  flush()
  return out
})

function link(e: Evidence) {
  return e.kind === 'member' && e.ref ? `/members/${encodeURIComponent(e.ref)}` : null
}

function tip(id: string) {
  const e = byId.value.get(id)!
  const action = link(e) ? `\nClick to open ${e.ref}` : '\nClick to see it in the sources'
  return { value: `${KIND_LABELS[e.kind]} · ${e.text}${action}`, class: 'cite-tip' }
}

async function cite(id: string) {
  const e = byId.value.get(id)!
  const to = link(e)
  if (to) return router.push(to)
  open.value = true
  highlighted.value = id
  await nextTick()
  sources.value?.querySelector(`[data-id="${id}"]`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
}
</script>

<template>
  <div class="answer">
    <component :is="b.list ? 'ul' : 'div'" v-for="(b, i) in blocks" :key="i" class="block">
      <component :is="b.list ? 'li' : 'p'" v-for="(line, j) in b.lines" :key="j">
        <template v-for="(t, k) in line" :key="k">
          <strong v-if="t.type === 'bold'">{{ t.text }}</strong>
          <span v-else-if="t.type === 'cite'" class="cites">
            <button
              v-for="id in t.ids"
              :key="id"
              v-tooltip.top="tip(id)"
              type="button"
              class="cite"
              :class="`k-${byId.get(id)!.kind}`"
              :aria-label="`Evidence ${id}: ${byId.get(id)!.text}`"
              @click="cite(id)"
            >{{ id.slice(1) }}</button>
          </span>
          <template v-else>{{ t.text }}</template>
        </template>
      </component>
    </component>

    <div v-if="evidence.length" class="sources">
      <button type="button" class="toggle" :aria-expanded="open" @click="open = !open">
        {{ open ? 'Hide' : 'Show' }} {{ evidence.length }} source{{ evidence.length === 1 ? '' : 's' }}
      </button>
      <ol v-if="open" ref="sources">
        <li v-for="e in evidence" :key="e.id" :data-id="e.id" :class="{ hl: highlighted === e.id }">
          <span class="cite static" :class="`k-${e.kind}`">{{ e.id.slice(1) }}</span>
          <span class="kind">{{ KIND_LABELS[e.kind] }}</span>
          <RouterLink v-if="link(e)" :to="link(e)!">{{ e.text }}</RouterLink>
          <span v-else>{{ e.text }}</span>
        </li>
      </ol>
    </div>
  </div>
</template>

<style scoped>
.answer { line-height: 1.5; }
.answer p { margin: 0; }
.block { margin: 0 0 0.5rem; }
.answer ul { padding-left: 1.1rem; display: flex; flex-direction: column; gap: 0.2rem; }
.cites { white-space: nowrap; margin-left: 0.15rem; }
.cite {
  --c: var(--accent);
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 1.15rem; height: 1.05rem; padding: 0 0.25rem; margin: 0 0.08rem;
  font: 600 0.68rem/1 system-ui, sans-serif; vertical-align: 0.15em;
  color: var(--c); background: color-mix(in srgb, var(--c) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--c) 35%, transparent); border-radius: 999px;
  cursor: pointer;
}
.cite:hover, .cite:focus-visible { background: var(--c); color: #fff; outline: none; }
.cite.static { cursor: default; vertical-align: baseline; flex: none; }
.k-member { --c: #2f6fb5; }
.k-rule { --c: #7c4dbd; }
.k-offer { --c: #23855a; }
.k-event { --c: #c46a12; }
.k-plan { --c: #12808a; }
.sources { margin-top: 0.25rem; font-size: 0.8rem; }
.toggle { background: none; border: 0; padding: 0; color: var(--muted); cursor: pointer; font: inherit; text-decoration: underline dotted; }
.toggle:hover { color: var(--text); }
.sources ol { list-style: none; margin: 0.4rem 0 0; padding: 0.4rem; display: flex; flex-direction: column; gap: 0.15rem; background: var(--bg); border-radius: 8px; }
.sources li { display: flex; gap: 0.4rem; align-items: baseline; padding: 0.2rem 0.3rem; border-radius: 6px; transition: background 0.3s; }
.sources li.hl { background: color-mix(in srgb, var(--accent) 14%, transparent); }
.kind { color: var(--muted); flex: none; min-width: 5.5rem; }
</style>

<style>
.cite-tip { max-width: 22rem; }
.cite-tip .p-tooltip-text { font-size: 0.8rem; line-height: 1.4; white-space: pre-line; }
</style>
