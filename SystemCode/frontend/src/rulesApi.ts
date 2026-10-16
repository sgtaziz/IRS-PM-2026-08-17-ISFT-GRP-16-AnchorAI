import { ApiError, api } from './api/client'
import type { Rule, RuleReport, RuleVersion } from './api/types'

/** The backend reads rules as YAML, and JSON is valid YAML; it stores its own canonical dump. */
export const draftText = (rules: Rule[]) =>
  JSON.stringify(
    rules.map((r) => ({
      id: r.id,
      kind: r.kind,
      salience: r.salience,
      description: r.description,
      when: r.when,
      then: Object.fromEntries(Object.entries(r.then).filter(([, v]) => v != null)),
      source: r.source,
      ...(r.enabled ? {} : { enabled: false }),
    })),
  )

export const validateText = (yaml_text: string) =>
  api<RuleReport>('/rules/validate', { method: 'POST', body: JSON.stringify({ yaml_text }) })

export const saveText = (yaml_text: string, note: string, base_version: number | null) =>
  api<RuleVersion>('/rules', { method: 'PUT', body: JSON.stringify({ yaml_text, note, base_version }) })

export const isStale = (e: unknown) => e instanceof ApiError && e.status === 409
