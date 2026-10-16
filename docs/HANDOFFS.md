# Cross-stream handoffs

What each stream needs from the others: blockers, reviews, decisions and promised deliverables.

**How to use it**
- **What do others need from me?** Read your own stream's section below.
- **What am I waiting on?** Look for your stream in the *Requested by* column of the other sections.
- **Need something?** Add a row to the section of the stream that has to act. Use the next free number, and today's date.
- **Done?** The stream that acted moves the row to **Done**, with the date and the commit or PR.
- Keep rows short. Put detail in a linked file, notebook or PR.

**Kinds:** `blocker` (stops work or an experiment), `review` (AGENTS.md requires another stream's review), `decision` (needs agreement), `deliver` (promised code, data or endpoint).

**Status:** `open`, `in progress` or `answered` (waiting for the requester to confirm).

## Stream A: Member Intelligence

| # | Requested by | Kind | Item | Why it matters | Status | Added |
|---|---|---|---|---|---|---|
| 1 | C | blocker | Add a documented event effect to the scenario (e.g. higher post-event churn hazard or uplift for members of a departed instructor's or cancelled class) | All KG signals show churn lift below 1 on real data (lost instructor 0.63, cancelled class 0.71, cohort risk 0.59; `notebooks/results/c3_signal_churn.csv`), because Kaggle class-goers churn less. Without an effect, E7 cannot show the KG adds anything | open | 2026-10-16 |
| 2 | C | decision | `churn_prob` is extremely bimodal: median 0.004; risk bands 2,886 low / 124 medium / 990 high. Expected, or a calibration / leakage effect? | Rules on `churn_prob` and `risk_band` depend on it; medium-risk rules reach only ~125 members | open | 2026-10-16 |
| 3 | C | review | The `built` test fixture moved from `tests/test_api_stream_a.py` into `tests/conftest.py`, so other streams' tests can reuse it | Touches A's test file | open | 2026-10-16 |
| 4 | C | review | Rule-trace and ego-graph responses are now typed in `Member360.vue` (`RuleOutcome`, `EgoGraph` in `src/api/types.ts`) | Touches A's page | open | 2026-10-16 |
| 5 | C | review | C1–C5 landed on `main` without a cross-stream review: auth and app DB, rule engine, rule base, knowledge graph | AGENTS.md requires one review from another stream (A or B) | open | 2026-10-16 |
| 14 | C | deliver | Write ~10 questions a gym manager or staff member might ask the assistant, in your own words, each tagged with an intent (`member_risk`, `member_actions`, `compare_members`, `graph_impact`, `plan_summary`, `what_if_budget`) or `unknown` | E8 needs a test set the assistant's author never saw; the current one (`notebooks/c_intent_classifier.ipynb`) is optimistic | open | 2026-10-16 |

## Stream B: Decision & Optimisation

| # | Requested by | Kind | Item | Why it matters | Status | Added |
|---|---|---|---|---|---|---|
| 6 | C | decision | Agree the rule output contract: `RuleOutcome` (`anchorai/reasoning/models.py`) with `allowed`, `blocked`, `firings`. Batch call: `run_many(rules, build_facts(...))`. Should it move into `schemas.py`? | B's pipeline (B6) turns it into `CandidateAction` | open | 2026-10-16 |
| 7 | C | decision | What shape do you want for KG spillover weights? (`member_id, class_id, weight` per class cohort, or member–member pairs) | The GA's spillover term; C builds it once B decides | open | 2026-10-16 |
| 8 | C | deliver | `demo` seed layer: one approved past week with assignments and logged outcomes | Dashboards, audit log and the assistant's plan questions are empty without it | open | 2026-10-16 |
| 9 | C | deliver | `POST /api/plan` and `Explanation` | Assistant intents about plans (C4, W30) | open | 2026-10-16 |
| 15 | C | deliver | Write ~10 questions a gym manager or staff member might ask the assistant, in your own words, each tagged with an intent (`member_risk`, `member_actions`, `compare_members`, `graph_impact`, `plan_summary`, `what_if_budget`) or `unknown` | E8 needs a test set the assistant's author never saw; the current one (`notebooks/c_intent_classifier.ipynb`) is optimistic | open | 2026-10-16 |

## Stream C: Knowledge & Interaction

| # | Requested by | Kind | Item | Why it matters | Status | Added |
|---|---|---|---|---|---|---|
| 10 | A | deliver | Reusable Cytoscape ego-graph component for Member 360 (W18) | Endpoint `GET /api/graph/ego/{id}` is done; the panel still prints raw JSON | in progress | 2026-10-16 |
| 11 | A | deliver | Rule-trace panel component for Member 360 | Endpoint `GET /api/rules/trace/{id}` is done; the panel still prints raw JSON | in progress | 2026-10-16 |
| 12 | B | deliver | Live guardrail check for plan overrides (W15) | Engine is ready; endpoint pending | open | 2026-10-16 |
| 13 | B | deliver | `graph_signals(facts)` strings for `Explanation.graph_signals` | Done in `anchorai/knowledge/signals.py`; B to confirm it fits | answered | 2026-10-16 |

## Done

| # | Requested by → Owner | Item | Closed |
|---|---|---|---|
