import type { Channel, EventType, Role, RuleKind } from './api/types'

export const CHANNEL_LABELS: Record<Channel, string> = {
  sms: 'SMS',
  email: 'Email',
  call: 'Phone call',
  in_person: 'In person',
}

export const EVENT_LABELS: Record<EventType, string> = {
  instructor_left: 'Instructor left',
  class_cancelled: 'Class cancelled',
}

export const RULE_KIND_LABELS: Record<RuleKind, string> = {
  derive: 'Derived fact',
  playbook: 'Playbook',
  guardrail: 'Guardrail',
}

export const ROLE_LABELS: Record<Role, string> = { staff: 'Staff', manager: 'Manager', admin: 'Admin' }

const ACRONYMS = new Set(['id', 'kg', 'pt', 'sms', 'llm', 'csv', 'ai'])

/** "month_to_end_contract" -> "Month to end contract", for codes that have no label anywhere. */
export function humanize(code: string): string {
  const words = code.replace(/[._-]+/g, ' ').trim().split(/\s+/)
  return words
    .map((w, i) => (ACRONYMS.has(w.toLowerCase()) ? w.toUpperCase() : i === 0 ? w[0].toUpperCase() + w.slice(1) : w))
    .join(' ')
}

export const channelLabel = (c: string | null | undefined) => (c ? (CHANNEL_LABELS[c as Channel] ?? humanize(c)) : '—')

export const contractLabel = (months: number) => (months <= 1 ? 'Month-to-month' : `${months} months`)

/** The short code a rule id starts with: "D05_high_value_at_risk" -> "D05". */
export const ruleCode = (id: string) => id.split('_')[0]

export const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('')
