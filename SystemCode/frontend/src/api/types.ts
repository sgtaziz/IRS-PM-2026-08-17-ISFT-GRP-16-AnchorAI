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

// Mirrors PlanRequest / PlanItem / Plan in anchorai/schemas.py and SavedPlan in anchorai/optimisation/service.py.
export interface PlanRequest {
  as_of: string
  budget: number
  staff_minutes: number
  max_contacts_per_member_per_30d?: number
  solver?: string
}

export interface PlanItem {
  member_id: string
  offer_id: string
  channel: Channel
  expected_value: number
  explanation_id: string
}

// Mirrors anchorai/optimisation/explain.py member_evidence and contacts.history (Stream B).
export interface SimilarCase {
  member_id: string
  offer_id: string | null
  week_start: string
  stayed: boolean
  distance: number
  outcome: string
}

export interface OfferEvidence {
  offer_id: string
  offer_name: string
  estimate: number
  local: number | null
  weight_on_local: number
  neighbours_treated: number
  neighbours_control: number
  cases: SimilarCase[]
}

export interface ContactRow {
  plan_id: number
  week_start: string
  offer_id: string
  offer_name: string
  channel: Channel
  removed: boolean
  override_reason: string | null
  assigned_to: string | null
  outcomes: { outcome: string; note: string | null; logged_at: string }[]
}

// Mirrors Explanation in anchorai/schemas.py; similar_cases as written by anchorai/optimisation/explain.py.
export interface Explanation {
  explanation_id: string
  member_id: string
  churn_prob: number
  top_drivers: [string, number][]
  rule_trace: RuleFiring[]
  similar_cases: SimilarCase[]
  graph_signals: string[]
  summary: string
}

// Mirrors ItemCheck in anchorai/reasoning/check.py (POST /api/rules/check).
export interface ItemCheck {
  member_id: string
  offer_id: string
  channel: Channel
  allowed: boolean
  violations: { rule_id: string; description: string; blocks: string }[]
  on_playbook: boolean
  channel_offered: boolean
  offer_active: boolean
}

// Mirrors anchorai/optimisation/assignment.py summary.
export interface StaffAssignment {
  user_id: number
  full_name: string
  skills: string[]
  minutes_capacity: number
  minutes_used: number
  contacts: { member_id: string; offer_id: string; channel: Channel }[]
}

export interface AssignmentSummary {
  plan_id: number
  staff: StaffAssignment[]
  unassigned: string[]
}

// Mirrors anchorai/optimisation/contacts.py my_contacts and log_outcome.
export type OutcomeCode = 'reached' | 'no_answer' | 'accepted' | 'declined' | 'follow_up'

export interface MyContact {
  plan_id: number
  week_start: string
  plan_item_id: number
  priority: number
  member_id: string
  offer_id: string
  offer_name: string
  channel: Channel
  explanation_id: string
  summary: string
  drivers: string[]
  rule: string | null
  graph_signals: string[]
  outcome: OutcomeCode | null
  note: string | null
}

// Mirrors anchorai/optimisation/jobs.py compare.
export interface PlannerResult {
  planner: string
  contacts: number
  spend: number
  staff_minutes: number
  linear_value: number
  full_value: number
  expected_extra_members: number
  feasible: boolean
}

export interface Comparison {
  request: PlanRequest
  planners: PlannerResult[]
  ga_convergence: { generation: number; best: number; mean: number }[]
}

// Mirrors anchorai/health.py (W45, admin only).
export interface HealthDetails {
  status: string
  llm: { base_url: string; model: string; api_key: string | null; tool_calling: boolean }
  knowledge_graph: {
    uri: string
    reachable: boolean
    stale: boolean
    problem: string | null
    last_reloaded_at: string | null
    counts: Record<string, number> | null
  }
  models: {
    built: boolean
    built_at?: string
    seed?: number
    members?: number
    churn_model?: string
    churn_test?: { f1: number | null; pr_auc: number | null; brier: number | null }
    uplift_baseline?: string
  }
  database: { revision: string | null; latest: string[]; up_to_date: boolean }
  planner: {
    latest_plan: { id: number; status: string; created_at: string } | null
    uplift_source: string
    case_base: { randomised: number | null; logged: number }
  }
}

export interface LlmTest {
  ok: boolean
  seconds: number
  reply?: string
  error?: string
}

// Mirrors anchorai/optimisation/jobs.py JobStatus.
export interface PlanJob {
  state: 'idle' | 'running' | 'done' | 'failed'
  kind: 'plan' | 'compare' | null
  stage: string | null
  progress: number
  started_at: string | null
  finished_at: string | null
  plan_id: number | null
  comparison: Comparison | null
  error: string | null
}

export interface SavedPlan {
  id: number
  status: string
  created_at: string
  request: PlanRequest
  items: PlanItem[]
  total_cost: number
  total_staff_minutes: number
  expected_members_retained: number
  solver_stats: Record<string, unknown>
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
  member_total?: number | null
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
  offer_channels: Record<string, Channel[]>
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
