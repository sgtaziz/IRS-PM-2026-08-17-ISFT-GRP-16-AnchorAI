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
| 2 | C | decision | `churn_prob` is extremely bimodal: median 0.004; risk bands 2,886 low / 124 medium / 990 high. Expected, or a calibration / leakage effect? **A, 2026-10-17:** expected. The test split, scored out-of-sample, is just as extreme, and each band churns at its predicted rate (test: low 1.6% predicted vs 2.9% observed, medium 44.1% vs 41.7%, high 95.1% vs 93.9%). One part *was* an artefact: training members were scored in-sample, which overstated how predictable they are. They are now out-of-fold (`718508b`), so the bands are 2,861 / 169 / 970. For a wider watch band, see `notebooks/results/e2_band_cutoffs.csv` (medium from 0.1 gives 410 members); evidence in `a_churn.ipynb`, section "Why are the probabilities so bimodal?" | Rules on `churn_prob` and `risk_band` depend on it; medium-risk rules reach only ~125 members | answered | 2026-10-16 |
| 14 | C | deliver | Write ~10 questions a gym manager or staff member might ask the assistant, in your own words, each tagged with an intent (`member_risk`, `member_actions`, `compare_members`, `graph_impact`, `plan_summary`, `what_if_budget`) or `unknown` | E8 needs a test set the assistant's author never saw; the current one (`notebooks/c_intent_classifier.ipynb`) is optimistic | open | 2026-10-16 |
| 20 | C | decision | Offer catalogue (`anchorai/scenario/offers.py`) changes we'd like, from the simulated manager interviews (`Miscellaneous/interviews/`): add `call` to `checkin_message` channels, and consider a smaller discount (e.g. 15% off, lower cost), since all three treat discounts as a last resort. **A, 2026-10-17:** `call` added (`636b825`); C's draft-refusal test now uses `in_person` as the unsupported channel. Discount kept at 20%: "last resort" is about *when* to offer it, which belongs in C's playbooks and guardrails. A cheaper discount with the same effect would make the optimiser pick it *more* often, not less. Existing app DBs need `anchorai db reset` to pick up catalogue changes | The catalogue also drives the scenario history, so either change needs a data build and a re-run of A's notebooks; C switches P02 to `call` once it lands | answered | 2026-10-16 |

## Stream B: Decision & Optimisation

| # | Requested by | Kind | Item | Why it matters | Status | Added |
|---|---|---|---|---|---|---|
| 6 | C | decision | Agree the rule output contract: `RuleOutcome` (`anchorai/reasoning/models.py`) with `allowed`, `blocked`, `firings`. Batch call: `run_many(rules, build_facts(...))`. Should it move into `schemas.py`? | B's pipeline (B6) turns it into `CandidateAction` | open | 2026-10-16 |
| 7 | C | decision | What shape do you want for KG spillover weights? (`member_id, class_id, weight` per class cohort, or member–member pairs) | The GA's spillover term; C builds it once B decides | open | 2026-10-16 |
| 8 | C | deliver | `demo` seed layer: one approved past week with assignments and logged outcomes | Dashboards, audit log and the assistant's plan questions are empty without it | open | 2026-10-16 |
| 9 | C | deliver | `POST /api/plan` and `Explanation` | Assistant intents about plans (C4, W30) | open | 2026-10-16 |
| 15 | C | deliver | Write ~10 questions a gym manager or staff member might ask the assistant, in your own words, each tagged with an intent (`member_risk`, `member_actions`, `compare_members`, `graph_impact`, `plan_summary`, `what_if_budget`) or `unknown` | E8 needs a test set the assistant's author never saw; the current one (`notebooks/c_intent_classifier.ipynb`) is optimistic | open | 2026-10-16 |
| 17 | C | review | `GET /api/health` (W45, your router) now returns only `{"status": "ok"}`; the LLM endpoint and model moved to admin-only `GET /api/health/details` for your Settings page | The public health check exposed the private LLM base URL | open | 2026-10-16 |
| 26 | A | review | Sign off the same Stream A contracts as #25. For B in particular: score plans with `true_uplift` (contacting a member now) and `true_churn` (no-contact hazard); read offers, roster and caps from `offer_catalog`, `staff_profiles` and `app_settings` via `anchorai/catalog.py`. Also, `/api/plan` is mounted manager-only, so routes staff use (similar cases on Member 360, W20, W21) need their own router | AGENTS.md contract rule; avoids rework when B starts | open | 2026-10-17 |

## Stream C: Knowledge & Interaction

| # | Requested by | Kind | Item | Why it matters | Status | Added |
|---|---|---|---|---|---|---|
| 13 | B | deliver | `graph_signals(facts)` strings for `Explanation.graph_signals` | Done in `anchorai/knowledge/signals.py`; B to confirm it fits | answered | 2026-10-16 |
| 21 | A | blocker | RULE-1 (high): derive rules D01, D02, D05 and D06 can't be disabled from Rules admin. `validate.py` builds asserted facts from enabled rules only but checks every rule, disabled consumers included | W40's documented on/off toggle fails with 422 "Unknown fact"; fix in `docs/reviews/c1-c5.md` | open | 2026-10-17 |
| 22 | A | review | Medium findings from the C1–C5 review: RULE-2 contact guardrails ignore real contacts and the W41 caps; RULE-3 SMS and calls go to members with no phone; RULE-4 validator passes rules that can't fire; RULE-5 rule output ignores the live offer catalogue; RULE-6 free-PT eligibility isn't enforced; RULE-7 version Compare marks every rule changed; KG-1 the graph is shown fresh while its facts have been dropped | Each has a repro and a fix in `docs/reviews/c1-c5.md` | open | 2026-10-17 |
| 23 | A | review | Low findings from the same review: AUTH-2 to AUTH-9, RULE-8 to RULE-15, KG-2, KG-3, KG-5, KG-6 and KG-7 | `docs/reviews/c1-c5.md`; AUTH-1, RULE-16 and KG-4 were fixed by A | open | 2026-10-17 |
| 24 | A | deliver | Re-run `c_rules`, `c_e6_rules`, `c_kg` and `c_e8_assistant` after A's 2026-10-17 data changes (training members scored out-of-fold, so bands are 2,861 / 169 / 970; zero-visit attendance rows removed; new `true_churn` table; `freq_drop` became `visit_change`), and measure E7 against `true_churn` (see `docs/SCENARIO.md`, "Gym events") | The quoted E6/E7/E8 numbers come from the old build. Training-split pattern lifts were inflated by in-sample scores | open | 2026-10-17 |
| 25 | A | review | Sign off the Stream A contracts: the data tables, including the new `true_churn` (`anchorai/scenario/tables.py`); `MemberScore` (`top_drivers` uses feature keys, with readable labels from `/api/members/{id}`); and the W41 tables `offer_catalog`, `staff_profiles` and `app_settings` | AGENTS.md: contracts need all three streams' agreement, and A1–A8 landed without a cross-stream review | open | 2026-10-17 |

## Done

| # | Requested by → Owner | Item | Closed |
|---|---|---|---|
| 1 | C → A | Scenario event effect. New `true_churn` table (next-month no-contact hazard before and after events); events add 1.4 × lost-instructor share and 0.9 × cancelled share to the log-odds, from their own week on. For flagged members, their own hazard rises 1.80× (lost instructor) and 1.32× (cancelled class); lift against all members is 1.41 and 1.00, because class-goers are lower-risk to begin with. Raw-lift vs within-member measure explained in `docs/SCENARIO.md`, "Gym events" | 2026-10-17, `5b319cd`, `cf5c114`, `notebooks/results/a5_event_lift.csv` |
| 3 | C → A | Review of the shared `built` fixture: approved. It now also points the settings' data dir at its temp folder, so rule and KG code can't read the developer's real `kg_facts.parquet` (proved by planting real facts: the old fixture fails a C test, the new one passes) | 2026-10-17, `b48acf0` |
| 4 | C → A | Review of Member 360 with `RuleTrace` and `EgoGraph`: approved. A's content is intact, and every other-stream panel degrades inside its own loading/error state | 2026-10-17 |
| 5 | C → A | Cross-stream review of C1–C5 (auth and app DB, rule engine, rule base, knowledge graph): 32 verified findings (1 high, 8 medium, 23 low) plus one scope note; A fixed AUTH-1, RULE-16 and KG-4, and filed the rest as #21–#23 | 2026-10-17, `docs/reviews/c1-c5.md` |
| 16 | C → A | Review of `sync_graph()` in the rebuild job: approved. A rebuild with Neo4j down finishes as `done` and marks the graph stale. Caveat KG-3: a malformed `NEO4J_URI` makes `sync_graph` raise, so the rebuild reports `failed` | 2026-10-17 |
| 18 | C → A | Driver label: `freq_drop` replaced by signed `visit_change` = this month − lifetime (negative = fewer visits), labelled "Change in weekly visits (this month vs lifetime)". "Change" now reads true in drivers, the assistant and the rule builder | 2026-10-17, `2f8e4f1` |
| 19 | A → C | KG reload and roster-name refresh now use the request's DB session; `tests/conftest.py` points the default engine at an empty throwaway DB so no test can read the real `app.db` | 2026-10-16 |
| 10 | A → C | Reusable Cytoscape ego-graph component for Member 360 (W18) | 2026-10-16, `src/components/EgoGraph.vue`, used in Member 360 and the graph explorer |
| 11 | A → C | Rule-trace panel component for Member 360 | 2026-10-16, `src/components/RuleTrace.vue`, used in Member 360 and rules admin |
| 12 | B → C | Live guardrail check for plan overrides (W15) | 2026-10-16, `POST /api/rules/check` (manager, admin): per item `allowed`, `violations`, `on_playbook`, `channel_offered`, `offer_active`. `allowed` is rules only: B must also read the other three (inactive offer, unsupported channel, off-playbook override); B to confirm |
