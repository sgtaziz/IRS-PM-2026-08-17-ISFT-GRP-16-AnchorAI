// Mirrors anchorai/auth/schemas.py.
export type Role = 'staff' | 'manager' | 'admin'

export interface UserOut {
  id: number
  username: string
  role: Role
  full_name: string
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserOut
}

// Mirrors anchorai/schemas.py.
export interface MemberScore {
  member_id: string
  as_of: string
  segment: string
  churn_prob: number
  monthly_value: number
  top_drivers: [string, number][]
  features: Record<string, number>
}

// Mirrors anchorai/discovery/views.py.
export type RiskBand = 'high' | 'medium' | 'low'

export interface MemberRow {
  member_id: string
  segment_id: number
  segment: string
  churn_prob: number
  risk_band: RiskBand
  monthly_value: number
  club_id: string
  lifetime: number
  contract_period: number
  age: number
  avg_class_frequency_total: number
  trend_ratio: number
}

export interface MemberPage {
  items: MemberRow[]
  total: number
  page: number
  page_size: number
}

export interface Facets {
  clubs: string[]
  segments: string[]
}

export interface MemberHit {
  member_id: string
  segment: string
  risk_band: RiskBand
  churn_prob: number
}

export interface SegmentCard {
  segment_id: number
  name: string
  description: string
  size: number
  churn_rate: number
  at_risk: number
  monthly_revenue: number
  profile: Record<string, number>
}

export interface AttendanceRow {
  class_id: string
  class_name: string
  instructor_id: string
  instructor_name: string
  visits_per_week: number
}

export interface InterventionRow {
  week_start: string
  offer_id: string | null
  channel: string | null
  treated: boolean
  stayed: boolean
}

export interface MemberDetail {
  score: MemberScore
  risk_band: RiskBand
  segment_id: number
  segment_description: string
  club_id: string
  profile: Record<string, number>
  segment_averages: Record<string, number>
  feature_labels: Record<string, string>
  attendance: AttendanceRow[]
  interventions: InterventionRow[]
}

export interface Kpis {
  total_members: number
  members_at_risk: number
  revenue_at_risk: number
  plan_coverage: number | null
  contacted: number
  reached: number
  retained: number
  outcome_week: string | null
}

export interface Dashboard {
  as_of: string
  kpis: Kpis
  risk_distribution: { start: number; end: number; count: number }[]
  segment_mix: { segment: string; size: number; at_risk: number }[]
  outcome_trend: { week_start: string; contacted: number; reached: number; retained: number }[]
}

// Mirrors anchorai/catalog.py.
export type Channel = 'sms' | 'email' | 'call' | 'in_person'

export interface Offer {
  offer_id: string
  name: string
  cost: number
  staff_minutes: number
  inventory: number | null
  channels: Channel[]
  eligibility: string
  required_skill: string
  active: boolean
}

export interface StaffRow {
  user_id: number
  username: string
  full_name: string
  weekly_hours: number
  skills: string[]
}

export interface Constraints {
  default_budget: number
  default_staff_minutes: number
  max_contacts_per_member_per_30d: number
  max_offers_per_member_per_90d: number
}

export interface CatalogView {
  offers: Offer[]
  staff: StaffRow[]
  constraints: Constraints
  skills: string[]
}

// Mirrors model_card.json written by anchorai/pipeline.py plus the admin data router.
export interface Metrics {
  f1: number
  precision: number
  recall: number
  pr_auc: number
  roc_auc: number
  brier: number
  threshold: number
  confusion: { tn: number; fp: number; fn: number; tp: number }
}

export interface FairnessGroup {
  n: number
  churn_rate: number
  recall: number
  precision: number
  fpr: number
}

export interface Fairness {
  groups: Record<string, FairnessGroup>
  recall_gap: number
  fpr_gap: number
}

export interface CalibrationCurve {
  predicted: number[]
  observed: number[]
}

export interface BuildStatus {
  state: 'idle' | 'running' | 'done' | 'failed'
  seed: number | null
  started_at: string | null
  finished_at: string | null
  error: string | null
}

export interface RawInfo {
  name: string
  bytes: number
  modified_at: string
}

export interface DataOverview {
  built_at?: string
  seed?: number
  source?: string
  n_members?: number
  segmentation?: {
    k: number
    silhouette: number
    silhouette_by_k: Record<string, number>
    stability_ari: number
  }
  churn?: {
    model: string
    n_train: number
    n_test: number
    test: Metrics
    resampling: { chosen: string } & Record<string, Metrics | string>
    leakage: Record<'with_suspect' | 'without_suspect', { test: Metrics; cv: Metrics }>
    baselines: { visit_rule: Metrics & { rule: string }; single_lr: Metrics }
    calibration: { calibrated: CalibrationCurve; uncalibrated: CalibrationCurve }
    fairness: Record<'age_band' | 'gender', Fairness>
  }
  build: BuildStatus
  raw: RawInfo | null
}

// Stream C: mirrors anchorai/schemas.py RuleFiring and anchorai/reasoning/models.py.
export interface RuleFiring {
  rule_id: string
  description: string
  facts_matched: Record<string, unknown>
  effect: string
}

export interface Proposal {
  offer_id: string
  channel: string
  rule_id: string
}

export interface RuleOutcome {
  member_id: string
  facts: Record<string, unknown>
  firings: RuleFiring[]
  proposals: Proposal[]
  blocked: Record<string, string>
  allowed: Proposal[]
}

// Mirrors anchorai/knowledge/ego.py: Cytoscape elements.
export interface GraphElement {
  data: { id: string; type: string; label?: string; source?: string; target?: string } & Record<string, unknown>
}

export interface EgoGraph {
  nodes: GraphElement[]
  edges: GraphElement[]
}

// Mirrors anchorai/reasoning/models.py, validate.py and service.py.
export type RuleKind = 'derive' | 'playbook' | 'guardrail'

export interface Rule {
  id: string
  kind: RuleKind
  salience: number
  description: string
  when: string[]
  then: { assert?: Record<string, unknown> | null; propose?: Proposal | null; block?: 'all' | string[] | null }
  source: string
  enabled: boolean
}

export interface RuleIssue {
  rule_id: string
  severity: 'error' | 'warning'
  message: string
}

export interface Glossary {
  rules: Record<string, string>
  offers: Record<string, string>
  facts: Record<string, string>
}

export interface RuleSet {
  version: number | null
  rules: Rule[]
  issues: RuleIssue[]
}

// Mirrors anchorai/reasoning/versions.py.
export interface RuleReport {
  rule_count: number
  parse_errors: string[]
  issues: RuleIssue[]
}

export interface RuleVersion {
  version: number
  note: string
  created_by: string | null
  created_at: string
  is_active: boolean
  rule_count: number
}

export interface RuleVersionDetail extends RuleVersion {
  yaml_text: string
}

export interface FactInfo {
  name: string
  type: 'number' | 'bool' | 'category'
  description: string
  source: string
  derived: boolean
  choices: string[]
}

export interface Vocabulary {
  facts: FactInfo[]
  offers: { offer_id: string; name: string; channels: string[] }[]
  channels: string[]
}

// Mirrors anchorai/auth/users.py.
export interface UserRow {
  id: number
  username: string
  role: Role
  full_name: string
  is_active: boolean
  created_at: string
}

// Mirrors anchorai/assistant/slots.py, tools.py and service.py.
export interface Slots {
  member_ids: string[]
  amount: number | null
  instructor_ids: string[]
  class_ids: string[]
  limit?: number | null
  risk_band?: string | null
  segment?: string | null
  club_id?: string | null
  new_members?: boolean
}

export interface Evidence {
  id: string
  text: string
  kind: 'member' | 'rule' | 'offer' | 'event' | 'plan'
  ref: string | null
}

export interface AssistantReply {
  intent: string
  score: number
  slots: Slots
  tool: string | null
  evidence: Evidence[]
  answer: string
  grounded: boolean
  llm_used: boolean
  follow_up: boolean
}

export interface HistoryTurn {
  question: string
  answer: string
  intent: string
  slots: Slots
}

// Mirrors anchorai/knowledge/simulate.py.
export type EventType = 'instructor_left' | 'class_cancelled'

export interface GraphEntity {
  id: string
  name: string
  club_id: string
  detail: string
  has_event: boolean
}

export interface GraphEntities {
  instructors: GraphEntity[]
  classes: GraphEntity[]
}

export interface AffectedMember {
  member_id: string
  churn_prob: number
  risk_band: RiskBand
  share: number | null
  new_rules: string[]
  allowed: Proposal[]
}

export interface Simulation {
  event_type: EventType
  entity_id: string
  label: string
  affected: number
  high_risk: number
  newly_flagged: number
  members: AffectedMember[]
  graph_out_of_date: boolean
}

// Mirrors anchorai/knowledge/roster.py and reload.py.
export interface RosterEvent {
  event_id: string
  week_start: string
  note: string
  source: 'generated' | 'added'
}

export interface RosterInstructor {
  id: string
  name: string
  club_id: string
  source: 'generated' | 'added'
  status: 'active' | 'left'
  classes: number
  event: RosterEvent | null
}

export interface RosterClass {
  id: string
  name: string
  club_id: string
  instructor_id: string
  instructor_name: string
  source: 'generated' | 'added'
  status: 'active' | 'cancelled'
  event: RosterEvent | null
}

export interface Roster {
  clubs: string[]
  instructors: RosterInstructor[]
  classes: RosterClass[]
}

export interface KgStatus {
  stale: boolean
  last_reloaded_at: string | null
  error: string | null
  counts: Record<string, number> | null
}

export interface RosterEdit {
  id: string | null
  kg: KgStatus
}

// Mirrors anchorai/db/audit.py.
export interface AuditRow {
  id: number
  ts: string
  username: string
  action: string
  entity: string
  entity_id: string | null
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
}

export interface AuditPage {
  items: AuditRow[]
  total: number
  actions: string[]
  usernames: string[]
}

// Mirrors anchorai/assistant/drafts.py.
export interface MessageDraft {
  text: string
  subject: string | null
  channel: Channel
  source: 'llm' | 'template'
  evidence: string[]
}

// Events of POST /assistant/chat/stream (assistant/service.py stream_answer).
export type AssistantStreamMeta = Omit<AssistantReply, 'answer' | 'grounded' | 'llm_used'>

export interface AssistantStreamDone {
  grounded: boolean
  llm_used: boolean
  answer: string
}
