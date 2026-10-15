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
