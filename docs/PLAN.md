# AnchorAI: Project Plan

**Deadline:** Sun 25 Oct 2026, 23:59 (aim to submit by noon). **Today:** Tue 13 Oct. **Team:** 3 members, 3 workstreams (A, B, C). Pick one each.

---

## 1. What is being assessed

From *IRS Practice Module v2.16* and the proposal/presentation guidelines:

- **Techniques:** cover at least 3 of the 4 technique groups. We cover all 4:
  - Decision automation: rules / knowledge-based reasoning
  - Resource optimisation: search / evolutionary
  - Knowledge discovery / data mining
  - Cognitive: knowledge graph, natural-language interface
- **The system:** runnable, with a UI, result interpretation and visualisation.
- **Grading criteria:**
  - business value
  - system design
  - implementation and usability
  - **experiments (quantitative)**
  - videos
  - contribution / peer review
  - value-adds (self-researched techniques, intuitive UI)
- **Deliverables:**
  - [ ] GitHub repo following the [IRS-PM template](https://github.com/IRS-PM/Workshop-Project-Submission-Template). This repo already uses its layout: `SystemCode/`, `ProjectReport/`, `Video/`, `Miscellaneous/`, `README.md`.
  - [ ] Promotion video, 5 min: business pain, value, use-case demo, pricing.
  - [ ] System design video, 5 min: system design, technical walk-through of use cases.
  - [ ] **No AI-generated speech** in either video. Record your own voices.
  - [ ] Group report (PDF):
    - business case / market research
    - system design
    - implementation
    - experiments
    - findings
  - [ ] Report appendices:
    - the proposal
    - **mapping of functionality to MR / RS / CGS** (§3 is the draft)
    - installation and user guide
    - AI-use note
  - [ ] Individual reflection, 1 page per member, plus a confidential peer review (submitted separately on Canvas).
  - [ ] `member-github.txt`, the repo zip and the report, zipped together using the naming convention `IRS-PM-<date>-<batch>-GRP-<team>-AnchorAI.zip`.

---

## 2. What the three courses teach (summary)

| Course | Core techniques taught (workshops in **bold**) |
|---|---|
| **Machine Reasoning (MR)** | **D1:** search (BFS/DFS/UCS, greedy, **A\***), CSP (backtracking, propagation, MRV), **OR-Tools CP**. **D2:** forward/backward chaining, conflict resolution, **CBR / kNN**, Bayes nets, **decision trees** and rule extraction, **Naive Bayes**, ROC/AUC. **D3:** knowledge graphs, Cypher/SPARQL, **KG embeddings (PyKEEN TransE/DistMult)**, XAI (SHAP, LIME, counterfactuals). **D4:** ensembles, random forest importance, **k-means + RFM segmentation**, MLP, CV, surrogate explanations. |
| **Reasoning Systems (RS)** | **D1:** hybrid patterns (rules + ML, search + optimisation, KG + LLM, RAG, agents), explainability as design, **hybrid triage workshop: ML score + IF-THEN rules + explanation + validation + human review**. **D2:** CRISP-DM, **Apriori, content-based, collaborative filtering, SVD (Surprise)**. **D3:** hybrid / deep / sequence / graph recommenders, cold start. **D4:** **genetic algorithms** (encoding, selection, crossover, mutation, elitism, penalty constraints; DEAP). **D5:** **Neo4j + Cypher, GraphRAG (LangChain)**, metaheuristics overview. |
| **Cognitive Systems (CGS)** | **D1:** NLU (**intent detection by embedding similarity**, slot filling / NER, dialogue management), **sentence-transformer retrieval**, RAG, agents, guardrails. **D1 PM:** vision cognition, perception + rule engine + human-in-the-loop. **D2:** audio / speech, LLM reasoning, evaluation at model, task and system level. **D3:** cognitive architecture, frames / semantic networks / KR, **RAG pipeline with LLM-as-judge evaluation**. |

---

## 3. Technique to course mapping (draft of the report appendix)

| Component | Technique | Course / day | Stream |
|---|---|---|---|
| Data prep | Stratified split, SMOTE-NC (training folds only), CRISP-DM | RS D2 | A |
| Features | Trend / ratio features (current-month vs lifetime class frequency), encoding, scaling | MR D4, RS D2 | A |
| Segmentation | K-means, silhouette, cluster profiling | MR D4 | A |
| Churn model | Calibrated LR + gradient-boosting ensemble, CV, F1 / PR-AUC / Brier | MR D2, MR D4 | A |
| Driver explanations | SHAP / feature importance, decision-tree surrogate rules | MR D2, MR D3, MR D4 | A |
| Scenario layer | Synthetic club/class/instructor structure + intervention history with known effects (the "can only simulate" branch of the MR flowchart) | MR D3 | A |
| Uplift baseline | T-learner (ensemble per treatment arm) | MR D4 (self-research extension) | A |
| Offer reasoner | **Case-based reasoning** (retrieve, reuse, revise, retain) as kNN uplift | MR D2 | B |
| Plan optimiser | **Genetic algorithm** (DEAP): integer encoding, tournament selection, repair + penalties, elitism | RS D4 | B |
| Exact benchmark | **CP-SAT constraint optimisation** (OR-Tools) | MR D1, RS D1 | B |
| Policy evaluation | Simulation-based policy comparison | RS D1 (search + optimisation pattern) | B |
| Rule engine | **Forward chaining**, salience-based conflict resolution, traced explanations, guardrails | MR D2, RS D1 | C |
| Knowledge graph | **Neo4j / Cypher**, multi-hop queries, cohort signal propagation | MR D3, RS D5 | C |
| Staff assistant | **Intent detection by embedding similarity**, slot filling, grounded LLM generation, LLM-as-judge evaluation | CGS D1, CGS D3 | C |
| Overall | Hybrid ML + rules + optimisation + KG + NL interface with human-in-the-loop explanations | RS D1, CGS D1 PM | all |

---

## 4. Changes from the proposal and presentation (drift log)

Two sources were reviewed:
- the proposal (`Gate0_AnchorAI_Project_Proposal.docx`, 11 Sep)
- the updated deck (`AnchorAI — Project.pptx`, 27 Sep)

Where they disagree, the decision taken is noted below. Each change is something to mention in the report ("Deviations from plan").

1. **Resource optimisation: ANN → genetic algorithm.** ⚠️ Most important.
   - *What:* the deck (slide "Four technique groups") says *"An ANN that picks who to contact within budget and staff time."* The docx says a GA.
   - *Why:* an ANN is a learning model, not an optimisation technique. The technique group is "informed search OR evolutionary computing". An ANN cannot enforce budget, staff-hour or fatigue constraints, and it would not count for this group.
   - *Change:* use a GA (RS D4), benchmarked with CP-SAT (MR D1). Correct this in the report and both videos.
2. **Data strategy: real Kaggle data first, plus a thin synthetic scenario layer. No full longitudinal simulator.**
   - *Before:* the docx proposed an agent-based longitudinal simulator. The deck dropped it and centres on the real Kaggle dataset ("measure it on real data").
   - *Change:* segmentation and the churn model are trained and evaluated **only on the real 4,000 members**. Kaggle lacks clubs, classes, instructors, an offer catalogue and any intervention history, all of which the KG, CBR, uplift and optimiser need. A **scenario layer** therefore attaches those to the real members:
     - attendance consistent with `Group_visits` and the class-frequency columns
     - instructor / class events
     - a past-intervention history whose outcomes follow a documented ground-truth effect function
   - *Why:* this keeps the deck's real-data story, removes the riskiest critical-path item, and still lets the "budget-aware decision" claims be tested.
   - The report must say plainly which results are on real data (E1, E2) and which use the scenario layer (E3–E7).
3. **SMOTE-NC kept, but probabilities are recalibrated.**
   - *What:* the deck oversamples to 50/50.
   - *Problem:* SMOTE inflates predicted churn probabilities. The optimiser multiplies probability × uplift × value, so miscalibrated probabilities silently distort the plan.
   - *Change:*
     - SMOTE-NC is applied inside CV folds only (imblearn `Pipeline`).
     - Calibrate on a held-out slice of the real training data (isotonic / Platt), never on the test set.
     - Compare against class weights as an alternative.
4. **Metrics: keep F1 (churn class) as the headline, and add PR-AUC and Brier score / a calibration curve.**
   - *Why:* F1 measures the yes/no flag, but the plan consumes probabilities, so their quality must be shown too.
5. **Leakage check on Kaggle features.**
   - `Avg_class_frequency_current_month` (and possibly `Month_to_end_contract`) may be measured in the same month as the churn label.
   - Report the model with and without the suspect features. This honours the docx's leakage argument.
   - Trend is still available: `current_month / total` class frequency is the deck's "12 → 4 visits" signal, computed on real data.
6. **Fuzzy inference: core → optional stretch.**
   - *Why:* none of MR, RS or CGS teaches fuzzy logic, so it earns no "mapped to course" credit, and the timeline is 12 days.
   - Calibrated probabilities and trend-based `derive` rules already avoid threshold cliffs.
7. **GMM dropped. K-means only, with k chosen by silhouette plus interpretability.** This matches the deck and MR D4.
8. **CBR and uplift merged into one job, instead of two components that estimate the same thing.**
   - *Now:* CBR **is** the uplift estimator. For each offer, it takes retention among similar treated past cases minus retention among similar untreated cases (kNN uplift). Its neighbours double as explanation by precedent ("8 of 10 similar members who got a PT session stayed").
   - The T-learner becomes the baseline in experiment E3.
9. **The optimisation objective is made non-linear, so the GA is justified.**
   - *Problem:* with independent per-member value minus cost under budget and staff limits, this is a multiple-choice knapsack. CP-SAT solves it exactly in seconds, and a grader will ask "why a GA?".
   - *Change:* add a **KG cohort spillover** term and **diminishing returns** per instructor or club.
   - The GA optimises the full objective. CP-SAT gives the exact optimum of the linearised problem, and of the full problem on small instances, which gives the optimality gap.
10. **Class recommendations: core → stretch.** Item-based CF (RS D2) or PyKEEN link prediction on the KG (MR D3).
11. **Interviews: 2–4 → aim for 1–2, with a documented fallback.**
    - Every rule carries a `source:` field (interview / publication / team assumption).
    - Notes go in `Miscellaneous/interviews/`.
12. **Censoring item dropped.** The Kaggle data is a single snapshot with a binary label, so there is no time window to censor.
13. **Sponsor framing.**
    - Aramco sponsors the studies; it is not a data provider or client.
    - The report should say so, position the target user as mid-market gym operators, and not imply client validation.
14. **Assistant design: an intent router comes before the LLM.**
    - Small local models are unreliable at tool calling, so the default path is:
      1. embedding-based intent detection
      2. slot filling
      3. a deterministic tool call
      4. the LLM phrases the answer from the tool output only
    - Native tool calling is behind a flag.
    - The endpoint is configurable (Ollama / OpenAI / any OpenAI-compatible API).
    - This maps onto the CGS D1 NLU pipeline.
15. **Experiments widened beyond F1 and silhouette.** The headline business result is policy comparison: members retained per dollar for contact-all, risk-top-k, greedy-uplift, GA and exact (§9).

---

## 5. Architecture

```
            ┌──────────────────── Stream A ─────────────────────┐   ┌──────────── Stream C ────────────┐
 Kaggle ───►│ Prep (split, SMOTE-NC) ─► Features ─► Segments    │   │ Rule engine (derive/playbook/    │
 (real)     │                       ─► Churn (calibrated)+SHAP ─┼──►│ guardrail) ◄── KG facts (Neo4j)  │
            │ Scenario layer: clubs/classes/instructors,        │   │        │ allowed actions + trace │
            │ offers, intervention history (known effects) ─────┼──►│ KG loader                        │
            └───────────────────────────────────────────────────┘   └────────┼─────────────────────────┘
                                                                             ▼
                                       ┌──────────── Stream B ────────────────────┐
                                       │ CBR kNN uplift per (member, offer)        │
                                       │ → GA optimiser (budget, staff, inventory, │
                                       │   fatigue, spillover)  ⇄ CP-SAT benchmark │
                                       └──────────────┬───────────────────────────┘
                                                      ▼
                        Weekly Plan + Explanation (drivers, rule trace, similar cases, graph signals)
                                                      ▼
                  FastAPI  ──►  Vue web app  ◄──  Staff assistant (intent → tool → grounded LLM)
```

**Stack:**
- **Backend:** Python 3.12 (uv), FastAPI, SQLModel + SQLite (app data), PyJWT + bcrypt (auth), pandas, scikit-learn, imbalanced-learn, LightGBM, SHAP, DEAP, OR-Tools, neo4j driver, openai client, sentence-transformers.
- **Frontend:** Vue 3 + Vite + TypeScript, PrimeVue, Pinia, ECharts, Cytoscape.js.
- **Infrastructure:** Neo4j in docker-compose. The LLM endpoint is external and configurable.

---

## 6. Interfaces (agree on day 1, then change only with all three)

Defined in `SystemCode/backend/anchorai/schemas.py`:
- `MemberScore` (A → C, B)
- `RuleFiring` / `CandidateAction` (C → B)
- `PlanRequest` / `Plan` / `PlanItem` (B → API)
- `Explanation` (B + C → API / assistant)

The data tables are the other contract (A → everyone). They are saved as parquet in `SystemCode/data/generated/`. Exact columns and dtypes are fixed in `anchorai/scenario/tables.py`; `tests/fixtures/` holds a small synthetic copy:
- `members`: Kaggle rows (lower-cased column names) + `member_id`, synthetic `club_id`, `monthly_value`, `split` (train / test)
- `classes`
- `instructors`
- `attendance`: member → class, visits
- `offers`
- `interventions`: member, offer, channel, treated, stayed
- `true_uplift`: scenario-only ground truth
- `events`: `instructor_left`, `class_cancelled`

**Unblocking rule:** until scenario v0 lands, B and C build against a tiny hand-made fixture (`tests/fixtures/`) that has the same columns.

---

## 7. Workstreams

Each stream owns:
- one or more core course techniques
- its API router
- its web pages
- its experiments
- its report sections
- its segment of the system video

The loads are sized to be roughly equal.

### Stream A: Member Intelligence (knowledge discovery)

**Profile:** data and ML heavy. **Owns the critical path** (the data tables unblock everyone).

| # | Task | Done when | Target |
|---|---|---|---|
| A1 | Kaggle EDA, cleaning, stratified 80/20 split, `member_id`s; scenario v0: clubs, classes, instructors, attendance, offers (crude) | parquet tables load; B and C switch from the fixture | Wed 14 |
| A2 | Features: trend ratio, encodings, scaling; leakage check on suspect columns | feature table + leakage note | Thu 15 |
| A3 | K-means segmentation, k by silhouette, plain-English names | segment profile table + names | Fri 16 |
| A4 | Churn ensemble (LR + LightGBM) in an imblearn pipeline with SMOTE-NC inside CV, calibration, class-weight comparison, SHAP drivers, fairness by age / gender | `MemberScore` for all members; F1 / PR-AUC / Brier on the real test set | Sun 18 |
| A5 | Scenario v1: intervention history whose outcomes follow a documented ground-truth uplift function (heterogeneous by segment × offer), instructor / class events | ground truth in the appendix; sanity plots | Sat 17 |
| A6 | T-learner uplift baseline (input to E3) | uplift per offer per member | Mon 19 |
| A7 | Web: **W02 shell, W03 shared components** (§8) | other streams build pages inside the shell | Thu 15 |
| A8 | Web: **W10 Dashboard, W11 Segments, W12 Members, W13 Member 360, W41 Offers and constraints, W42 Data and models** + `/api/members`, `/api/admin/data`, `/api/admin/offers` | pages work on live data, for each role | Wed 21 |

- **Experiments:** E1, E2 (and data for E3).
- **Report:**
  - data collection and preparation, including the scenario-layer appendix
  - features
  - knowledge discovery
  - E1 and E2
  - **Installation guide**
- **Video:** the data → prediction segment.

### Stream B: Decision & Optimisation (CBR + evolutionary + constraint optimisation)

**Profile:** algorithmic. Most of the "business value" numbers come from here.

| # | Task | Done when | Target |
|---|---|---|---|
| B1 | Plan objective + constraint model, random-instance generator for testing | objective evaluated on a fixture plan | Wed 14 |
| B2 | GA in DEAP: integer chromosome (gene = action index, 0 = no contact), tournament selection, uniform crossover, mutation, **repair operator** + penalties, elitism; convergence logging | feasible plans on 2k-member instances in < 30 s | Fri 16 |
| B3 | CP-SAT exact model (linearised, and the full objective on small n) | optimality gap computed for n ≤ 200 | Sat 17 |
| B4 | CBR offer reasoner: case base from scenario interventions, scaled weighted kNN retrieve, kNN-uplift reuse, shrinkage revise, weekly retain | uplift + neighbour list per (member, offer) | Sun 18 |
| B5 | Baseline policies (contact-all, risk-top-k, greedy-uplift) + **policy evaluator** that scores any plan against the scenario's ground-truth uplift | one function evaluates any plan | Mon 19 |
| B6 | Pipeline orchestration: `MemberScore` → rules → CBR → optimiser → `Plan` + `Explanation` | `POST /api/plan` works end to end | Tue 20 |
| B7 | Web: **W14 Plan builder, W15 Review and overrides, W16 Assignment, W17 Scenarios, W20 My contacts, W21 Outcome logging, W45 Settings and health** + `/api/plan`, `/api/assignments`, `/api/outcomes` | full weekly workflow (§8.2) runs end to end | Wed 21 |

- **Experiments:** E3, E4 (headline), E5.
- **Report:**
  - system architecture overview
  - optimisation and CBR design
  - E3–E5
- **Video:** owns editing of the **system design video**, plus the decision → plan segment.

### Stream C: Knowledge & Interaction (rules + KG + NL interface)

**Profile:** knowledge engineering plus integration. Most domain-facing (interviews, playbooks). The gentlest on-ramp is the rule writing and KG schema; the assistant is the most open-ended piece.

| # | Task | Done when | Target |
|---|---|---|---|
| C1 | Forward-chaining rule engine: YAML rules, match-fire loop, salience + specificity conflict resolution, `RuleFiring` trace, rule validation (unknown facts, contradictions) | engine runs the sample rules on a fixture | Thu 15 |
| C2 | Rule base: ~15–25 rules (derive / playbook / guardrail), each with `source`; run 1–2 interviews (script in `Miscellaneous/interviews/`) | rules reviewed against interview notes | Sun 18 |
| C3 | Neo4j KG: schema, loader from the data tables, Cypher queries for cohort signals (`lost_anchor_instructor`, `cohort_at_risk`, `class_cancelled`) → facts into the rule engine; spillover weights for B | `events` → facts → rule firings | Sun 18 |
| C4 | Assistant: intent set + ~10 example utterances each, embedding classifier, slot filling, tool layer (plan, explanation, Cypher templates, what-if budget), grounded prompt, configurable LLM, optional native tool calling | answers the 6 intents with cited evidence | Tue 20 |
| C5 | Web: **W01 auth and roles, W04 app database, migrations and seeds** | a fresh clone reaches a seeded, logged-in app with the commands in §8.5; other streams use the role dependency and DB session | Thu 15 |
| C6 | Web: **W18 Graph explorer, W22 Message drafts, W30 Assistant, W40 Rules admin, W43 Users, W44 Audit log** + `/api/rules`, `/api/graph`, `/api/assistant`, `/api/admin/*` | pages work on live data, for each role | Wed 21 |

- **Experiments:** E6, E7, E8.
- **Report:**
  - business case and market research (update from the proposal)
  - knowledge acquisition
  - rules, KG and assistant
  - E6–E8
  - **User guide**
  - **course-mapping appendix**
- **Video:** owns editing of the **promotion video**, plus the KG + assistant segment.

### Shared, by everyone

- A day-1 contract review (§6).
- A daily 15-minute sync.
- PR review: every PR is reviewed by one other stream.
- One page each of individual reflection plus peer review.
- Each member records their own narration.

## 8. Web application

The web app is the product. It is what a club actually uses for the weekly retention cycle, and it is the stage for both videos. It is graded directly under *system implementation (functionality and usability)* and *value-adds (intuitive UI)*. Every feature below has **one owning stream**. The owner builds both the page and its API endpoints. Panels that show another stream's output call that stream's endpoint.

### 8.1 Roles

| Role | Who | Access |
|---|---|---|
| **Staff** | Front desk, trainers | Their own contact list, outcome logging, read-only Member 360, message drafts, assistant |
| **Manager** | Club manager | Everything Staff has, plus: dashboard, segments, members, plan builder / review / approval / assignment, scenarios, graph explorer |
| **Admin** | Operator / owner | Everything, plus: rules, offers and constraints, data and models, users, audit log, settings |

- Access is enforced **server-side**: a FastAPI dependency checks the role on every endpoint.
- The UI hides what a role cannot use (router `meta.roles`).
- Demo users are seeded: `admin`, `manager`, `staff1`, `staff2`.

### 8.2 The weekly workflow (core use case = demo script)

1. **Admin** keeps rules, offers and constraints current. They test a rule change on a real member before saving it.
2. **Manager** opens the Dashboard and sees members at risk, revenue at risk and last week's outcomes.
3. **Manager** generates this week's plan for a given budget and staff hours. They review it, open "why" on any member, and override with a reason; guardrails are re-checked live.
4. **Manager** approves the plan and auto-assigns calls to staff by available hours.
5. **Staff** open *My contacts* on a tablet. For each member they see the offer, talking points and an editable message draft. They log the outcome in two taps.
6. Outcomes flow back into the CBR case base (the *retain* step) and the Dashboard.
7. **Anyone** can ask the assistant at any point, e.g. "Why is member 1043 on the list but not 2210?"
8. **Event:** "Instructor Sam leaves" is triggered in the graph explorer. The affected members surface, and re-running the plan picks them up.

### 8.3 Features

Size: S ≈ ½ day, M ≈ 1 day, L ≈ 2 days (web + endpoint work only).

#### Platform

| ID | Feature | Must include | Stream | Size |
|---|---|---|---|---|
| W01 | **Login, auth and role guards** | Password login; JWT; bcrypt-hashed passwords; role dependency on all routers; route guards; seeded demo users; logout | **C** | M |
| W02 | **App shell** | Role-aware sidebar; global member search (Ctrl+K); toasts; loading, empty and error states on every page; responsive down to tablet width | **A** | M |
| W03 | **Shared UI components** | `KpiTile`, `RiskBadge` (text label, not colour alone), `DataTable` wrapper (sort, filter, CSV export), `ConfirmDialog`, `ChartCard` | **A** | S |
| W04 | **App database, migrations and seeds** | SQLite via SQLModel: users, plans, plan_items, assignments, outcomes, rule_versions, audit_log, assistant_feedback. Alembic migrations, deterministic seeds and `db` CLI commands, as set out in §8.5 | **C** | M |

#### Manager

| ID | Feature | Must include | Stream | Size |
|---|---|---|---|---|
| W10 | **Dashboard** | KPIs: members at risk, monthly revenue at risk, plan coverage, contacted / reached / retained this week. Risk distribution, segment mix, outcome trend by week | **A** | M |
| W11 | **Segments** | One card per segment: name, size, churn rate, profile chart; click through to the filtered member list | **A** | S |
| W12 | **Members list** | Server-side paged table; filter by segment, risk band, tenure, club; sort by risk or value; CSV export | **A** | S |
| W13 | **Member 360** | Profile; churn probability + SHAP driver chart (A); segment; rule trace (C endpoint); similar past cases (B endpoint); ego graph (C component); contact and outcome history (B endpoint); "Ask the assistant about this member" button | **A** | L |
| W14 | **Plan builder** | Week, budget, staff hours and solver inputs; runs as a background job with a progress bar; results table (member, offer, channel, expected value, one-line reason); "why" drawer showing the full `Explanation`; plan totals vs limits | **B** | M |
| W15 | **Plan review and overrides** | Remove, add or swap an offer, with a mandatory reason; live guardrail check (C rules endpoint) with violations shown inline; re-optimise remaining budget; approve (locks the plan, writes audit); compare with last week | **B** | L |
| W16 | **Assignment and call sheets** | Auto-assign approved items to staff by weekly hours and skills (e.g. PT offers go to trainers); drag or manual reassign; printable PDF / CSV call sheet per staff member | **B** | M |
| W17 | **Scenarios** | Budget and staff-hour sliders; compare contact-all, risk-top-k, greedy-uplift, GA and exact on expected retained members, cost and retained-per-dollar; GA convergence chart; save and name scenarios | **B** | M |
| W18 | **Knowledge graph explorer** | Search a member, class or instructor; Cytoscape neighbourhood view; highlight at-risk cohorts; "simulate event" (instructor leaves, class cancelled) lists affected members and the rules they trigger. Also exported as the reusable ego-graph component for W13 | **C** | M |

#### Staff

| ID | Feature | Must include | Stream | Size |
|---|---|---|---|---|
| W20 | **My contacts** | Today's assigned members in priority order; card per member showing offer, channel, talking points (from drivers + rule trace) and a link to Member 360; tablet-first layout | **B** | M |
| W21 | **Outcome logging** | Outcomes: reached / no answer / accepted / declined / follow-up, plus a note, in two taps. Writes to outcomes, appends to the CBR case base, updates dashboard counters | **B** | S |
| W22 | **Message drafts** | The LLM drafts an SMS or email from the `Explanation` and offer in the gym's tone. Staff edit before copying. **Never auto-sent.** Falls back to a template if the LLM is unavailable | **C** | S |

#### Assistant

| ID | Feature | Must include | Stream | Size |
|---|---|---|---|---|
| W30 | **Assistant (page + floating widget)** | Available on every page; aware of context (current member or plan); streams answers; shows the detected intent, the tool used and **evidence chips** linking to the member, rule or case; thumbs up/down logged (feeds E8); shows "I don't know" when nothing grounds the answer | **C** | L |

#### Admin

| ID | Feature | Must include | Stream | Size |
|---|---|---|---|---|
| W40 | **Rules admin** | Rules listed by kind and salience; enable / disable; form-based condition builder over known facts plus a raw YAML tab; mandatory `source`; validation (unknown facts, contradictions, unreachable rules); "test on member" shows the firing trace; version history with diff and rollback | **C** | L |
| W41 | **Offers and constraints** | Offer catalogue CRUD (cost, staff minutes, channels, weekly inventory, eligibility); default budget; staff roster with weekly hours and skills; contact-fatigue caps | **A** | M |
| W42 | **Data and models** | Upload Kaggle CSV; regenerate the scenario layer (seed); retrain segmentation and churn; rebuild KG (calls C's endpoint); model card with current F1, PR-AUC, Brier, silhouette, fairness gaps and training date | **A** | M |
| W43 | **Users** | User CRUD, role assignment, password reset | **C** | S |
| W44 | **Audit log** | Every write (rule edit, plan approve / override, assignment, outcome, user change): who, when, what, before / after; filterable | **C** | S |
| W45 | **Settings and health** | Active LLM endpoint and model (read from `.env`, key masked), "test connection", Neo4j status, model versions, data freshness, current DB migration revision | **B** | S |

#### Load check (S = 1, M = 2, L = 3)

| Stream | Web features | Web points |
|---|---|---|
| A | W02, W03, W10, W11, W12, W13, W41, W42 | 13 |
| B | W14, W15, W16, W17, W20, W21, W45 | 13 |
| C | W01, W04, W18, W22, W30, W40, W43, W44 | 16 |

C's total is higher, but four of its features are small CRUD pages, and W04 unblocks everyone early.

### 8.4 Non-functional requirements

- **Explainable in one click:** every recommendation opens its `Explanation`, covering drivers, rule trace, similar cases and graph signals.
- **Human in the loop:**
  - Nothing is sent to members automatically.
  - Plans need manager approval.
  - Overrides need a reason.
  - All writes are audited.
- **Graceful degradation:**
  - LLM down: assistant and drafts show "unavailable" and templates are used.
  - Neo4j down: graph panels are hidden and cached KG facts are used.
  - Neither failure breaks the plan.
- **Performance:**
  - Plan generation for 4,000 members takes ≤ 60 s, as a background job with progress.
  - Pages load in < 2 s on demo data.
- **Responsive:** staff pages (W20–W22) work on a tablet. Manager and admin pages target desktop.
- **Accessibility basics:**
  - labelled inputs
  - keyboard navigation
  - risk shown with text and colour, not colour alone
- **Demo-ready seed:**
  - seeded users
  - one past approved week with logged outcomes, so dashboards and the CBR retain loop are not empty
  - a `make demo`-style reset command
- **Consistent UI:**
  - PrimeVue components
  - ECharts for charts
  - Cytoscape.js for graphs
  - Pinia for auth and session state
  - No other UI libraries.

### 8.5 Database, migrations and seeds

The goal is that every member, the graders, and a fresh clone get **the same database from the same commands**. No one ever shares a `.db` file or edits the database by hand.

**Storage:**
- SQLite file at `SystemCode/data/app.db`, with the path set by `ANCHORAI_DB_URL`. The file is git-ignored.
- SQLModel models live in `anchorai/db/models.py`.

**Migrations (Alembic):**
- Migrations live in `SystemCode/backend/migrations/`.
- `render_as_batch=True` must be set, because SQLite cannot `ALTER` most column changes without it.
- **Every model change ships with its migration in the same PR.** Generate it with `alembic revision --autogenerate -m "<what>"`, then read and fix the generated file before committing.
- Migrations are append-only once merged to `main`. Never edit a merged migration; add a new one.
- **Parallel work creates multiple heads.** The PR author whose migration lands second rebases and runs `alembic merge heads`.
- A test asserts that there is a single head and that `upgrade head` → `downgrade base` → `upgrade head` runs cleanly on an empty DB.

**Seeds:** idempotent (safe to run twice), deterministic (`ANCHORAI_SEED`), and layered:

| Layer | Contents | Needs |
|---|---|---|
| `base` | Demo users (`admin`, `manager`, `staff1`, `staff2`) with known demo passwords; offer catalogue; staff roster with hours and skills; default budget and fatigue caps; current `rules/*.yaml` imported as rule version 1 | nothing |
| `demo` | One approved past week (plan, assignments, logged outcomes, audit entries), so dashboards, the CBR retain loop and the audit log are not empty | `base` + data tables from Stream A |

- Seed data is defined in code or in versioned YAML under `anchorai/db/seeds/`, never as a binary dump.
- Each stream adds the seed rows for its own features: A offers and constraints, B the past week, C users and rules.

**Commands:** one CLI, `uv run anchorai <cmd>`:

| Command | Does |
|---|---|
| `db upgrade` | Apply migrations to head |
| `db seed [--demo]` | Load the `base` seeds, plus `demo` if the flag is given |
| `db reset` | Delete `app.db`, upgrade and seed with `--demo` (the pre-demo / pre-video reset) |
| `data build` | Regenerate the parquet tables and model artefacts from `data/raw/` (Stream A) |
| `kg load` | Load the knowledge graph into Neo4j from the parquet tables (Stream C) |
| `setup` | `data build` → `db reset` → `kg load`: **one command from a fresh clone to a working demo** |

**Docker:** the `api` container runs `db upgrade` on start. `anchorai setup` is documented in the README and the installation guide.

**Fresh-clone test:**
- Sat 24 (§10): another member runs `anchorai setup` on a clean clone.
- Run it again after any migration or seed change.

---

## 9. Experiments (the quantitative evidence)

| ID | Question | Method / metric | Baseline | Owner |
|---|---|---|---|---|
| E1 | Are segments meaningful? (**real data**) | silhouette vs k, profile table, stability across seeds | k = 2..10 | A |
| E2 | Does the churn model beat simple rules? (**real data**) | F1 (churn class) + confusion matrix, PR-AUC, Brier, calibration curve on the untouched test set; SMOTE-NC vs class weights; with / without suspect features; fairness gaps | visit-threshold rule; single LR | A |
| E3 | Can we find who is persuadable? | Qini / AUUC vs scenario ground truth | T-learner; risk score used as uplift proxy | B (A supplies T-learner) |
| E4 | **Does AnchorAI retain more members per dollar?** | members retained (scenario ground truth) per budget level at three staff levels (36, 72, 120 h), 5 seeds; per $1,000 and per staff hour | contact-all, risk-top-k, greedy-uplift | B |
| E5 | How good and fast is the GA? | optimality gap vs CP-SAT, convergence curve, runtime vs n, parameter sensitivity | CP-SAT | B |
| E6 | Are rules correct and do guardrails matter? | scenario test cases (expected firings), conflict check, plan value with vs without guardrails | no guardrails | C |
| E7 | Do KG cohort signals add information? | inject instructor-leave events; churn lift of KG-flagged members; plan value with vs without KG facts | no KG | C |
| E8 | Is the assistant accurate and grounded? | intent accuracy on ~60 labelled questions; LLM-as-judge faithfulness + manual spot check; latency and quality of Ollama vs hosted model | keyword router | C |

---

## 10. Timeline

| Date | Milestone |
|---|---|
| **Tue 13** | Kick-off: pick streams, push repo, review contracts (§6), create fixture |
| Wed 14 | **Data tables v0 land** (Kaggle + scenario v0); B1, C1 underway |
| Thu 15 | **App shell (A7) + auth and app DB (C5) land**, so pages can start inside a working app |
| Thu 15 – Sat 17 | Core build (A2–A5, B2–B3, C1–C3); pages built against fixtures / mock responses |
| **Sun 18** | **M1: every component runs standalone on the real tables**; scenario layer frozen (regenerating after this means re-running everyone's experiments) |
| Mon 19 – Tue 20 | Integration: pages wired to live endpoints; the §8.2 workflow runs end to end for all three roles |
| **Wed 21** | **M2: feature freeze.** All pages wired. Run all experiments on frozen data |
| Thu 22 | Figures and tables; **cross-stream usability pass** (each member runs the §8.2 demo script on another stream's pages and files issues); bug fixes only; report sections drafted |
| Fri 23 | Record both videos; assemble report |
| Sat 24 | User guide, README, reflections, peer review; **fresh-clone install test** on another member's machine |
| **Sun 25** | Buffer. Zip and submit by noon |

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| Data tables slip and block B and C | Fixture first; scenario v0 deliberately crude; A gets help from B/C on day 2 if needed |
| Scenario layer makes E3–E7 look circular ("you designed the effects you recover") | Be explicit: churn and segments are real-data results; the scenario layer tests *recovery* of known structure and decision quality; run sensitivity with different effect sizes |
| The deck says ANN for optimisation | Fix it in the report and videos (drift item 1); a grader comparing against the proposal will see a justified change |
| Local LLM too weak | The intent router means the LLM only phrases answers; switch the `.env` to a hosted endpoint for the demo |
| Neo4j setup friction | docker-compose; the loader is idempotent; KG facts cached to parquet so the pipeline still runs without Neo4j |
| Integration crunch | Contracts fixed day 1; integration starts Mon 19, not Thu 22 |
| Scope creep | Stretches (fuzzy, class recommender, KG embeddings) only after M2 |
