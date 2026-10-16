import type { FactInfo, Rule } from './api/types'

export type Op = '>=' | '<=' | '>' | '<' | '==' | '!=' | 'in' | 'not in'

export interface ConditionRow {
  fact: string
  op: Op
  value: string
  list: string[]
}

const PATTERN = /^\s*([a-z_][a-z0-9_]*)\s+(>=|<=|==|!=|>|<|not in|in)\s+(.+?)\s*$/
const BARE = /^[A-Za-z_][A-Za-z0-9_ -]*$/
const NUMERIC_OPS: Op[] = ['>=', '<=', '>', '<', '==', '!=']

export const OP_LABELS: Record<Op, string> = {
  '>=': 'at least',
  '<=': 'at most',
  '>': 'more than',
  '<': 'less than',
  '==': 'is',
  '!=': 'is not',
  in: 'is one of',
  'not in': 'is none of',
}

export function opsFor(type: FactInfo['type'] | undefined): Op[] {
  if (type === 'number') return NUMERIC_OPS
  if (type === 'bool') return ['==', '!=']
  return ['==', '!=', 'in', 'not in']
}

const unquote = (s: string) => {
  const t = s.trim()
  return t.length >= 2 && t[0] === t.at(-1) && '\'"'.includes(t[0]) ? t.slice(1, -1) : t
}

export function parseCondition(text: string): ConditionRow | null {
  const m = PATTERN.exec(text)
  if (!m) return null
  const [, fact, op, raw] = m
  if (op === 'in' || op === 'not in') {
    if (!(raw.startsWith('[') && raw.endsWith(']'))) return null
    const list = raw.slice(1, -1).split(',').map(unquote).filter(Boolean)
    return { fact, op, value: '', list }
  }
  return { fact, op: op as Op, value: unquote(raw), list: [] }
}

function scalar(value: string, type: FactInfo['type'] | undefined): string {
  const v = value.trim()
  if (type === 'bool' || type === 'number') return v
  return BARE.test(v) && !['true', 'false'].includes(v) ? v : `"${v}"`
}

export function composeCondition(row: ConditionRow, type: FactInfo['type'] | undefined): string {
  if (row.op === 'in' || row.op === 'not in') return `${row.fact} ${row.op} [${row.list.map((v) => scalar(v, type)).join(', ')}]`
  return `${row.fact} ${row.op} ${scalar(row.value, type)}`
}

export function blankRule(): Rule {
  return {
    id: '',
    kind: 'playbook',
    salience: 30,
    description: '',
    when: [],
    then: { propose: { offer_id: '', channel: '', rule_id: '' } },
    source: '',
    enabled: true,
  }
}

export function parseAssertValue(raw: string): string | number | boolean {
  const v = raw.trim()
  if (v === 'true' || v === 'false') return v === 'true'
  return v !== '' && !Number.isNaN(Number(v)) ? Number(v) : v
}
