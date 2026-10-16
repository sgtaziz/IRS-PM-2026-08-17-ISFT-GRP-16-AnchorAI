export type DiffKind = 'add' | 'del' | 'same'

export interface DiffLine {
  kind: DiffKind
  text: string
}

export type DiffChunk = { lines: DiffLine[]; skipped?: undefined } | { skipped: DiffLine[]; lines?: undefined }

export interface RuleChanges {
  added: string[]
  removed: string[]
  changed: string[]
}

export function diffLines(before: string, after: string): DiffLine[] {
  const a = before.split('\n')
  const b = after.split('\n')
  const n = a.length
  const m = b.length
  const width = m + 1
  const lcs = new Uint32Array((n + 1) * width)
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      lcs[i * width + j] = a[i] === b[j] ? lcs[(i + 1) * width + j + 1] + 1 : Math.max(lcs[(i + 1) * width + j], lcs[i * width + j + 1])
    }
  }
  const out: DiffLine[] = []
  let i = 0
  let j = 0
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      out.push({ kind: 'same', text: a[i] })
      i++
      j++
    } else if (lcs[(i + 1) * width + j] >= lcs[i * width + j + 1]) out.push({ kind: 'del', text: a[i++] })
    else out.push({ kind: 'add', text: b[j++] })
  }
  while (i < n) out.push({ kind: 'del', text: a[i++] })
  while (j < m) out.push({ kind: 'add', text: b[j++] })
  return out
}

// Unchanged runs longer than 2 * context are split into kept edges and one skipped middle.
export function collapse(lines: DiffLine[], context = 3): DiffChunk[] {
  const chunks: DiffChunk[] = []
  let run: DiffLine[] = []
  const flush = (atStart: boolean, atEnd: boolean) => {
    if (!run.length) return
    const head = atStart ? 0 : context
    const tail = atEnd ? 0 : context
    if (run.length > head + tail + 1) {
      if (head) chunks.push({ lines: run.slice(0, head) })
      chunks.push({ skipped: run.slice(head, run.length - tail) })
      if (tail) chunks.push({ lines: run.slice(run.length - tail) })
    } else chunks.push({ lines: run })
    run = []
  }
  let changes: DiffLine[] = []
  let seenChange = false
  for (const line of lines) {
    if (line.kind === 'same') {
      if (changes.length) {
        chunks.push({ lines: changes })
        changes = []
      }
      run.push(line)
    } else {
      flush(!seenChange, false)
      seenChange = true
      changes.push(line)
    }
  }
  if (changes.length) chunks.push({ lines: changes })
  flush(!seenChange, true)
  return chunks
}

function ruleBlocks(text: string): Map<string, string> {
  const blocks = new Map<string, string>()
  let id: string | null = null
  let body: string[] = []
  const close = () => {
    if (id) blocks.set(id, body.join('\n').trimEnd())
  }
  for (const line of text.split('\n')) {
    const start = /^-\s+id:\s*(\S+)/.exec(line)
    if (start) {
      close()
      id = start[1]
      body = []
    }
    if (id) body.push(line)
  }
  close()
  return blocks
}

export function ruleChanges(before: string, after: string): RuleChanges {
  const old = ruleBlocks(before)
  const next = ruleBlocks(after)
  return {
    added: [...next.keys()].filter((id) => !old.has(id)),
    removed: [...old.keys()].filter((id) => !next.has(id)),
    changed: [...next.keys()].filter((id) => old.has(id) && old.get(id) !== next.get(id)),
  }
}
