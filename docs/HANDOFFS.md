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
| 14 | C | deliver | Write ~10 questions a gym manager or staff member might ask the assistant, in your own words, each tagged with an intent (`member_risk`, `member_actions`, `compare_members`, `graph_impact`, `plan_summary`, `what_if_budget`) or `unknown` | E8 needs a test set the assistant's author never saw; the current one (`notebooks/c_intent_classifier.ipynb`) is optimistic | open | 2026-10-16 |
| 27 | C | deliver | Your offer in the C1–C5 review (RULE-2): add some repeat contacts to the scenario history, so a few members have 2+ offers in 90 days | `G02_offer_cap` now follows the W41 cap but still never fires on scenario data (`offers_last_90d` is 0 or 1 for everyone), so E6 can't show it working | open | 2026-10-17 |
| 28 | C | review | Notes from C's contract sign-off (#25): `docs/PLAN.md` §6 omits `true_churn`, `interventions.week_start`, and `features` / `member_scores` / `kg_facts`, which C reads. `MemberScore` (`schemas.py`) doesn't match `member_scores.parquet` (no `risk_band`, `club_id`, `segment_id`; `top_drivers` is a JSON string; no `as_of`/`features`); either align it or name the parquet as the contract. Document `visit_change` (negative = fewer visits) and `phone` (1 = phone on file) in the contract | C's rules and assistant read these; rule authors need a documented meaning to cite | open | 2026-10-17 |
| 33 | B | decision | **Team decision (A, B, C):** CBR stays the uplift estimator per PLAN drift item 8, but on the scenario it ties the T-learner overall (rank correlation 0.39 vs 0.39), beats it for PT and discount, and cannot separate members for check-in and class pass. At the seeded 36 staff hours, plans on CBR estimates keep 19.4 extra members vs 27.9 on the T-learner (level at 72 and 120 h). Keep CBR for the numbers, or let A's T-learner supply them and CBR the explanations? The GA amplifies the gap: its true net value vs greedy is up to −9% on CBR estimates, within ±2% on T-learner, up to +8% on perfect knowledge (`notebooks/b_cbr.ipynb`, `notebooks/b_ga.ipynb`, `results/e3_*.csv`, `results/e4_estimates.csv`) | Decides the planner's uplift source, PLAN drift item 8 and the E3/E4 story; the second option makes A's T-learner part of the live system | open | 2026-10-19 |

## Stream B: Decision & Optimisation

| # | Requested by | Kind | Item | Why it matters | Status | Added |
|---|---|---|---|---|---|---|
| 8 | C | deliver | `demo` seed layer: one approved past week with assignments and logged outcomes | Dashboards, audit log and the assistant's plan questions are empty without it | open | 2026-10-16 |

## Stream C: Knowledge & Interaction

| # | Requested by | Kind | Item | Why it matters | Status | Added |
|---|---|---|---|---|---|---|
| 29 | A | review | RULE-2, remaining part: build `days_since_last_contact`, `contacts_last_30d` and `offers_last_90d` from approved plan items and logged outcomes too, not only the synthetic `interventions` | Once B logs real contacts, a member contacted yesterday must be blocked. Waits on B's plans and outcomes (#8, #9) | open | 2026-10-17 |
| 30 | B | review | `POST /api/rules/check` passes SMS or call for a member with no phone on file: M0040 `checkin_message` via `sms` returns `allowed`, `on_playbook` and `channel_offered` all true. RULE-3 lives only in the playbooks, and `on_playbook` matches the offer, not the channel | A manager override (W15) could schedule an unreachable contact | open | 2026-10-19 |
| 31 | B | decision | With the seeded roster (36 h = 2,160 staff minutes) staff time runs out before money: every baseline uses all 2,160 minutes, and budgets above ~$1,000 change nothing (`notebooks/b_plan_model.ipynb`, `results/b5_e4_baselines.csv`). So `what_if_budget` will mostly answer "no change"; consider a staff-hours what-if. When E6/E7 switch to B's evaluator, keep a staff level where budget matters (E4 uses 36, 72 and 120 h) | Assistant demo answers and E6/E7 plan-value comparisons | open | 2026-10-19 |
| 32 | B | deliver | B's evaluator and baselines are in `anchorai.optimisation`: `evaluate(plan, load_truth())`, `violations`, and `POLICIES` (contact-all, risk-top-k, greedy-uplift) on `load_instance(session).options`. E6/E7 can replace the provisional greedy stand-in; the GA joins `POLICIES` in Phase 4 | E6 and E7 plan-value comparisons | open | 2026-10-19 |
| 34 | B | deliver | KG spillover weights for the GA (#7): a function returning class cohort rows `member_id, class_id, weight` (weight = share of the member's own class visits), from the graph or the cached facts, so it works without Neo4j. Until then B builds the same rows from A's `attendance` table | GA spillover and diminishing-returns terms (PLAN drift item 9) | open | 2026-10-19 |

## Done

| # | Requested by → Owner | Item | Closed |
|---|---|---|---|
| 9 | C → B | `POST /api/plan` (solvers `ga`, `exact`, `greedy`), `GET /api/plan/latest` and `GET /api/plan/explanations/{id}`. Each saved plan item stores an `Explanation` in `plan_items.explanation`: A's drivers, C's rule trace and graph signals, B's 10 most similar past cases (each with an `outcome` sentence) and a one-line summary, so the assistant's plan answers now have data | 2026-10-20 |
| 7 | C → B | Spillover shape decided: **class cohort rows** `member_id, class_id, weight` (weight = the member's share of their own class visits). B derives pair strengths within classes and diminishing-returns groups per instructor (class → instructor). Delivery requested as #34 | 2026-10-19 |
| 15 | C → B | 9 questions added to `notebooks/data/e8_questions.yaml` (`stream_b_questions`, author `asiri`): 4 about one member (context M0008), 4 tagged `unknown`, 2 ranking questions tagged `graph_impact` (hard cases, noted) | 2026-10-19 |
| 26 | A → B | Signed off. The evaluator scores a plan as Σ(1 − `true_churn.event_churn`) + Σ `true_uplift.uplift` over its items (`event_churn`, matching `true_uplift`); `true_uplift` has no channel, so channel affects only the call sheet. Offers, roster and caps come from `catalog.list_offers(active_only=True)`, `list_staff`, `get_constraints`. Staff routes (W20, W21, similar cases) go in a separate staff router | 2026-10-19 |
| 17 | C → B | Reviewed the health split: public `GET /api/health` returns only `{"status": "ok"}`; `GET /api/health/details` gives 401 without login, 403 for manager, 200 for admin, which matches the admin-only Settings page (W45). Approved | 2026-10-19, `2cd0b2d` |
| 13 | B → C | `graph_signals(facts)` confirmed: returns `list[str]` for `Explanation.graph_signals`; B passes `RuleOutcome.facts`, so no extra query (356 of 4,000 members get a signal; empty list when the graph isn't loaded) | 2026-10-19, `anchorai/knowledge/signals.py` |
| 6 | C → B | `RuleOutcome` agreed as the C → B contract; it stays in `reasoning/models.py`. B builds `CandidateAction` from `allowed` (proposed and not blocked, one channel per offer), uses `firings` for the rule trace and `blocked` for "why not on the plan". Batch call: `active_rules(session)` + `all_facts(session)` + `run_many`, then `drop_inactive` per member (`run_many` alone keeps inactive offers). Please check with B before changing its fields | 2026-10-19 |
| 24 | A → C | Re-ran `c_kg`, `c_rules`, `c_e6_rules` and `c_e8_assistant` on A's 2026-10-17 build, and measured E7 against `true_churn` in the new `c_e7_kg.ipynb`: KG flags reproduce A's within-member lifts (1.80 / 1.32) and add no ranking gain over `churn_prob`, but reach 243 low-risk members holding 57% of the event-driven excess hazard | 2026-10-17, `notebooks/results/e7_*.csv` |
| 2 | C → A | Bimodal `churn_prob`: expected, bands match observed churn; training members now scored out-of-fold (2,861 / 169 / 970). C keeps the medium band as is (P08 now reaches 169 members) | 2026-10-17, `718508b` |
| 20 | C → A | `call` added to `checkin_message`; P02 now proposes it by call (or email with no phone on file). Discount kept at 20%: agreed, "last resort" is handled by the playbooks | 2026-10-17, `636b825` |
| 21 | A → C | RULE-1: any rule can be disabled; a fact only asserted by disabled rules is a warning, not an error | 2026-10-17 |
| 22 | A → C | Medium review findings fixed: RULE-2 (G01/G02 follow the W41 caps; the real-contacts part is #29), RULE-3 (SMS/call only with a phone on file, `P0Nb` email/in-person twins), RULE-4 (literal types, category values, contradictory conditions, exact always-blocked playbooks), RULE-5 (inactive offers hidden in trace, what-if, assistant and simulate; unsupported channels are errors), RULE-6 (G05 blocks free PT within 90 days), RULE-7 (v1 seeded canonical), KG-1 (staleness from the files) | 2026-10-17 |
| 23 | A → C | Low review findings fixed: AUTH-2 to AUTH-9 (incl. `token_version` migration, `<entity>.<verb>` audit actions), RULE-8 to RULE-14, RULE-15 (a: in the E6 rerun), KG-2, KG-3, KG-5 (relabelled, summed definition kept), KG-6 (graph reads return 503 while a reload runs; single API process assumed), KG-7. Also: assistant offer names and KG offer nodes come from the live catalogue | 2026-10-17 |
| 25 | A → C | C's sign-off of A's contracts: approved with notes (data tables incl. `true_churn` match `tables.py`; `true_churn.lost_instructor_share` matches the KG's `anchor_instructor_share`). Notes for A in #28 | 2026-10-17 |
| 1 | C → A | Scenario event effect. New `true_churn` table (next-month no-contact hazard before and after events); events add 1.4 × lost-instructor share and 0.9 × cancelled share to the log-odds, from their own week on. For flagged members, their own hazard rises 1.80× (lost instructor) and 1.32× (cancelled class); lift against all members is 1.41 and 1.00, because class-goers are lower-risk to begin with. Raw-lift vs within-member measure explained in `docs/SCENARIO.md`, "Gym events" | 2026-10-17, `5b319cd`, `cf5c114`, `notebooks/results/a5_event_lift.csv` |
| 3 | C → A | Review of the shared `built` fixture: approved. It now also points the settings' data dir at its temp folder, so rule and KG code can't read the developer's real `kg_facts.parquet` (proved by planting real facts: the old fixture fails a C test, the new one passes) | 2026-10-17, `b48acf0` |
| 4 | C → A | Review of Member 360 with `RuleTrace` and `EgoGraph`: approved. A's content is intact, and every other-stream panel degrades inside its own loading/error state | 2026-10-17 |
| 5 | C → A | Cross-stream review of C1–C5 (auth and app DB, rule engine, rule base, knowledge graph): 32 verified findings (1 high, 8 medium, 23 low) plus one scope note; A fixed AUTH-1, RULE-16 and KG-4, and filed the rest as #21–#23 | 2026-10-17, `docs/reviews/c1-c5.md` |
| 16 | C → A | Review of `sync_graph()` in the rebuild job: approved. A rebuild with Neo4j down finishes as `done` and marks the graph stale. Caveat KG-3: a malformed `NEO4J_URI` makes `sync_graph` raise, so the rebuild reports `failed` | 2026-10-17 |
| 18 | C → A | Driver label: `freq_drop` replaced by signed `visit_change` = this month − lifetime (negative = fewer visits), labelled "Change in weekly visits (this month vs lifetime)". "Change" now reads true in drivers, the assistant and the rule builder | 2026-10-17, `2f8e4f1` |
| 19 | A → C | KG reload and roster-name refresh now use the request's DB session; `tests/conftest.py` points the default engine at an empty throwaway DB so no test can read the real `app.db` | 2026-10-16 |
| 10 | A → C | Reusable Cytoscape ego-graph component for Member 360 (W18) | 2026-10-16, `src/components/EgoGraph.vue`, used in Member 360 and the graph explorer |
| 11 | A → C | Rule-trace panel component for Member 360 | 2026-10-16, `src/components/RuleTrace.vue`, used in Member 360 and rules admin |
| 12 | B → C | Live guardrail check for plan overrides (W15) | 2026-10-16, `POST /api/rules/check` (manager, admin): per item `allowed`, `violations`, `on_playbook`, `channel_offered`, `offer_active`. `allowed` is rules only: B must also read the other three (inactive offer, unsupported channel, off-playbook override); B to confirm. B confirmed 2026-10-19; one gap filed as #30 |
