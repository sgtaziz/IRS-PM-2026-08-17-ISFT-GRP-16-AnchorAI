# Experiments E6 to E8 (rules, knowledge graph, assistant)

*Stream C. Reproduce them with `uv run anchorai data build` (seed 42), `uv run anchorai kg load`, then `notebooks/c_e6_rules.ipynb`, `notebooks/c_e7_kg.ipynb` and `notebooks/c_e8_assistant.ipynb`. Figures are in `notebooks/figures/`, tables in `notebooks/results/`. All three notebooks import from `anchorai` and were run on 2026-10-20.*

**Which results use real data and which use the scenario layer.**

| Experiment | Real data | Scenario layer (synthetic) |
|---|---|---|
| E6 | The 4,000 Kaggle members and the churn bands built on them; the rule thresholds come from the real training split | Contact history, lost-instructor and cancelled-class facts, the true uplift that scores plan value |
| E7 | The churn model's scores | Gym events, the flagged cohorts, their effect sizes, and the true post-event hazard used as the label |
| E8 | The members and plans the assistant reads | The evidence the assistant cites comes from scenario-layer data, so "faithful" means faithful to the evidence lines, not true of a real gym |

E6 and E7 therefore test that the rules and the graph do what we designed, and recover a known effect. They do not show how real members behave (PLAN §4 drift item 2, §11 risk on circularity).

## E6: Are the rules correct, and do guardrails matter?

**Method.** The rule base has 29 rules: 16 playbooks, 8 derive rules and 5 guardrails. Four checks, all using the real engine and rules:

- the conflict check (`validate`: duplicate ids, unknown facts, offers or channels, unreachable conditions, contradicting derive rules)
- 29 hand-built scenario cases with the expected firings, allowed offers and blocked offers (`tests/fixtures/rule_cases.yaml`, also a regression test)
- coverage on the 4,000 members, with facts built exactly as the API builds them
- plan value with and without guardrails, using Stream B's candidate builder, planners and evaluator

**Baseline.** The same playbooks with the guardrails switched off.

**Setup for plan value.** The planners are `greedy-uplift`, `exact` (CP-SAT) and the GA (3 seeds), at weekly budgets of $500, $1,500 and $4,000 and at 36 h (the seeded roster) and 120 h of staff time. The score is Stream B's `evaluate(plan, load_truth())`: extra members retained by the scenario's true uplift, which no planner sees. 60 plans were run.

**Conflict check and cases** (`results/e6_validation_issues.csv`, `results/e6_scenario_cases.csv`). 0 validator issues, and 29 of 29 scenario cases match. No rule is dead: every rule fires for at least one member (`results/e6_rule_coverage.csv`, `e6_rule_coverage.png`).

**What the guardrails remove** (`results/e6_guardrail_bites.csv`). Of 3,448 proposals over 1,422 members, 1,080 (31.3%) are removed:

| Guardrail | Proposals removed | Members | Members matching the guardrail |
|---|---|---|---|
| G01 contact fatigue (30-day cap) | 1,029 | 372 | 657 |
| G02 offer cap | 0 | 0 | 45 |
| G03 discount eligibility | 0 | 0 | 1,793 |
| G04 low risk, no paid offers | 7 | 7 | 2,861 |
| G05 PT eligibility | 44 | 30 | 353 |

**With and without guardrails, counts** (`results/e6_with_vs_without_guardrails.csv`):

| | Members with an offer | Offers |
|---|---|---|
| no guardrails | 1,422 | 2,907 |
| with guardrails | 1,045 | 2,025 (30.3% of the guardrail-free set removed) |

The 882 offers the guardrails remove are 845 contacts inside the 30-day cap (G01), 30 repeat free PT sessions (G05) and 7 paid offers to low-risk members (G04). All guardrail-free plans contain violations; no plan with guardrails contains any (0 of 2,025 options).

**Where members end up.** 2,955 of 4,000 members (73.9%) have no allowed offer, but 2,577 of those are low-risk members that no playbook targets, by design. Of 970 high-risk members, 300 end with no allowed offer, 298 of them because G01 blocks every offer (`results/e6_member_outcomes.csv`).

**Plan value, extra members retained by the true uplift** (`results/e6_plan_value.csv`, `e6_plan_value.png`):

| Staff time | Budget | With guardrails | Without | Gap (without − with) | G01 violations per guardrail-free plan |
|---|---|---|---|---|---|
| 36 h | $500-$4,000 | 15.6-21.8 | 15.9-23.1 | −1.0 to +1.4 (−6% to +9%) | 75-148 |
| 120 h | $500-$4,000 | 30.4-51.1 | 44.1-56.6 | +5.6 to +14.3 (+11% to +45%) | 230-287 |

- At 36 h staff time binds, so budgets above about $1,000 change nothing and removing the guardrails gains about one member at most. Every guardrail-free plan contacts 75-148 members a second time within 30 days.
- At 120 h the gap is large (13-14 members at $500-$1,500, 6-8 at $4,000), because the guardrail-free plans spend the extra hours on members inside the 30-day cap, including the demo week's 182.
- All violations are G01. No planner picks a repeat free PT session or a paid offer to a low-risk member.
- `greedy-uplift` matches or beats `exact` and the GA on true value in most cells, consistent with Stream B's finding that the CBR estimates are noisy. Which planner wins is E4's question, not this one.

**Other findings.**
- **G02 fires but removes nothing.** With the demo week's logged contacts counted, 45 members have 2 offers in 90 days, so `at_offer_cap` is reachable on real data. All 45 were contacted in the demo week, so G01 already blocks them and the trace names G01.
- **G03 never removes a proposal.** Its only proposers (P05, P05b) already require `contract_period == 1`. It is a safety net for manual plan overrides and future playbooks, not a working guardrail today.
- **Logged contacts matter.** Counting the contacts staff have logged raised the proposals removed from 528 (15.3%) to 1,080 (31.3%), as 657 members are now inside the 30-day cap (475 from the scenario history plus the 182 contacted in the demo week). Next week's plan cannot contact last week's members again.
- **Medium risk is a thin band:** 169 members (4.2%).
- **No phone, no SMS or call.** The 386 members without a phone get the email or in-person twin of each playbook (338 twin firings). No member without a phone is proposed an SMS or a call.
- **Low-risk new and slipping members** are proposed a PT session and then blocked by G04 (7 cases). Decision: keep G04, because the churn model already weighs tenure heavily and G04 blocks only paid offers. The blocked proposals stay visible in the trace.
- **Interview changes (2026-10-16).** D01 covers 72 members (was 127), D03 315 (was 502) and the new D04 258 new members who are barely visiting.

**Caveats.**
- **The rule base is ours.** The rules are hand-written and the thresholds come from the real training split. The scenario cases test that the rules do what we meant, not that what we meant is right; because we wrote both, they are optimistic.
- **Suspect features.** `trend_ratio` and `avg_class_frequency_current_month` are suspect features (`results/a_leakage.md`), so rules built on them (D01, D03, P01) select members partly on information that may come from the churn month.
- **Synthetic facts.** `lost_anchor_instructor`, `class_cancelled` and `days_since_last_contact` come from the scenario layer, so how often they fire reflects our simulator, not real gyms.
- **No fatigue effect in the scenario.** The scenario's true uplift has no contact-fatigue effect, so re-contacting a member reached last week is worth as much as a first contact. The gap in the plan-value table is therefore the cost of G01 under a simulator that cannot see what G01 protects against. It is an upper bound, and the benefit of the guardrails is not measurable here. A negative gap at 36 h means the guardrails removed contacts the noisy CBR estimates over-valued, not that guardrails add value.
- **Opt-out.** There is no opt-out fact, so "never contact opted-out members" cannot be expressed or tested. Decided out of scope: consent handling is assumed to happen in the gym's messaging tool.
- **Demo-week dependence.** The counts include Stream B's demo week (an approved plan for the week of 2026-10-12 with 182 logged outcomes) after `anchorai db reset`.

**Verdict.** The rule base is internally consistent (0 validator issues, 29 of 29 cases, no dead rule) and the guardrails do real work: they remove 31.3% of proposals, almost all of them G01 contacts inside the 30-day cap. Their cost in retained members is zero to small at the seeded 36 h and up to about 14 members at 120 h, but the scenario cannot price the fatigue they prevent, so we claim safety and auditability, not a retention gain. Two of the five guardrails (G02, G03) remove nothing on today's data and are kept as safety nets.

## E7: Do knowledge-graph cohort signals add information?

**Method.** Four parts, all reading the cached KG facts (`uv run anchorai kg load`); the notebook never connects to Neo4j.

1. **Signal check:** the churn hazard of KG-flagged members, before and after the scenario's gym events.
2. **Ranking (main result):** on the 800 held-out test members (66 KG-flagged: 37 lost instructor, 29 cancelled class), does adding the KG flags to the churn model's ranking surface members with a higher true post-event hazard?
3. **Rule layer:** the shipped rule base over all 4,000 members with and without the KG facts.
4. **Plan value:** Stream B's planners on the two candidate sets, scored by the true uplift.

**Baseline.** No KG: rank by `churn_prob`, and for the rule layer and plan value, facts built with `kg=None`.

**Ranking setup.** The KG variant adds a fixed bonus to `churn_prob` for members with `lost_anchor_instructor` or `class_cancelled`, at three sizes (0.05, 0.10, 0.20), plus a rank-only variant that moves flagged members ahead within their risk band. The bonus does not use the documented event multipliers or any scenario truth, which would be circular. The label is the scenario's true post-event hazard (`event_churn`), not `members.churn`: the Kaggle label has no events in it, so it cannot reward a signal about them. Scores are Spearman against `event_churn` and hazard-weighted precision at k = 50, 100 and 200, with an oracle ranking as a ceiling. Uncertainty is 1,000 bootstrap resamples of the test members; the table reports the 95% interval of the difference to the baseline.

**Signal** (`results/e7_signal_lift.csv`, `e7_signal_lift.png`):

| Signal | Flagged members | Within-member lift | Raw lift vs all members |
|---|---|---|---|
| lost anchor instructor | 186 | 1.80 | 1.41 |
| class cancelled | 170 | 1.32 | 1.00 |

Within-member lift is hazard after the event divided by hazard before it for the same people, and matches Stream A's `results/a5_event_lift.csv` exactly. Raw lift is lower because class-goers are lower-risk to begin with.

**Ranking** (`results/e7_ranking.csv`, `e7_ranking.png`):

| Ranking | Spearman | p@50 | p@100 | p@200 | Spearman difference [95% CI] |
|---|---|---|---|---|---|
| baseline (`churn_prob`) | 0.8324 | 0.7595 | 0.7089 | 0.6247 | |
| KG bonus +0.05 | 0.8375 | 0.7607 | 0.7134 | 0.6259 | +0.005 [−0.008, +0.019] |
| KG bonus +0.10 | 0.8337 | 0.7607 | 0.7134 | 0.6259 | +0.001 [−0.013, +0.016] |
| KG bonus +0.20 | 0.8312 | 0.7573 | 0.7154 | 0.6269 | −0.001 [−0.016, +0.015] |
| KG in-band | 0.8291 | 0.7481 | 0.7122 | 0.6276 | −0.003 [−0.019, +0.013] |
| oracle (`event_churn`) | 1.0000 | 0.8260 | 0.7744 | 0.6763 | +0.168 [+0.148, +0.193] |

Precision at k moves by at most ±0.012 and every interval includes 0. The result does not depend on the bonus size. The oracle shows there is room the KG does not fill: only about 8% of test members are flagged, and the churn model already explains most of the hazard.

**Rule layer** (`results/e7_rules_with_without_kg.csv`):

| | Members |
|---|---|
| with an allowed offer, with KG | 1,227 |
| with an allowed offer, without KG | 984 |
| gain an allowed offer (none to some) | 243 |
| lose all allowed offers | 0 |
| offer list changes at all | 298 |

All 243 gainers are low-risk by the model. The KG reaches them through D07 and D08 into P03 (P03b without a phone), and the only offer added is the free `checkin_message` (279 members), which G04 allows for low-risk members. They hold 34.5 of the 60.4 total event-driven excess hazard (57%; mean +0.14 each). Flagged high- and medium-risk members are reached with or without the KG. Rules that fire only because of the KG: D07 (159 members), D08 (139), P03 (263) and P03b (35); the per-rule counts are among the 298 members whose offer list changes, so D07 shows 159 of its 186.

**Plan value, extra members retained by the true uplift** (`results/e7_plan_value.csv`), at the default $1,500 budget:

| Staff time | With KG | Without KG | Gain | KG-only members contacted | Their true uplift |
|---|---|---|---|---|---|
| 36 h | 17.5-19.4 | 17.6-19.6 | −0.1 to −0.4 | 10-21 of 243 | 0.3-0.4 |
| 120 h | 48.8-50.1 | 41.6-43.1 | +7.0 to +7.2 (+17%) | 243 of 243 | 5.0 |

- At 36 h the plan is full at 182 contacts, and the planner's CBR estimates give the KG-only check-ins no reason to beat the contacts it already has (Stream B's E3: CBR cannot tell members apart for the check-in). The KG adds nothing and costs a fraction of a member.
- At 120 h every KG-only member is contacted. They account for 5.0 of the 7.0-7.2 gain, the rest coming from the 55 other members whose offer list the KG facts change.
- So the KG's reach turns into plan value only when there is staff time to spare. At the seeded roster it is a list of extra candidates, not extra retention.

**Caveats.**
- **Synthetic events.** The events, the flagged cohorts and the effect sizes come from the scenario layer (`docs/SCENARIO.md`, "Gym events"). The churn model is trained on the Kaggle snapshot, which has no events, so it is blind to them by construction. E7 shows that the KG carries information the model lacks when events of this kind exist, not that real gyms have such events or that our effect sizes are right.
- **Recovery, not evidence.** The rule-layer gain is a recovery test of a known effect, not evidence from real churn. The label is a hazard we generated from features plus the event shift, and a ranking by `base_churn` would also be strong.
- **Kaggle label.** On the Kaggle label the flags show lift below 1 (`results/c3_signal_churn.csv`), which is why that label cannot be used here.
- **Facts without logged contacts.** Part 4 builds facts without the app's logged contacts (as parts 1-3 do), so its plans are not the app's next-week plan. E6 part 4 has that.

**Verdict.** The KG flags identify the members the events hurt (lift 1.80 and 1.32, exact match to Stream A). They do not improve who ranks highest: no ranking difference has an interval that excludes 0, whatever the bonus. They do change who gets contacted: 243 low-risk members whose routine was just disrupted, a group the churn score misses, are routed to a free check-in, and those check-ins are worth about 7 extra members when staff time allows (120 h) and nothing at the seeded 36 h.

## E8: Is the assistant accurate and grounded?

**Method.** Seven parts: intent accuracy, grounded answers, faithfulness (programmatic checks, then LLM-as-judge), latency, a manual spot check, a local versus hosted model comparison and a prompt-variant test.

**Baseline.** A keyword router with the same slot extraction (member ids, amounts), so the comparison is about the intent decision.

**Setup.**
- **Questions:** 71 labelled questions (`data/e8_questions.yaml`) over 7 intents plus `unknown` (13 questions): 62 written by an AI (Claude) from the intent descriptions, and 9 held out, written by Stream B.
- **Classifier:** sentence-embedding similarity to each intent's example centroid, a threshold of 0.35 for `unknown`, and a member-slot rule.
- **Grounded answers:** a stratified sample of 20 questions goes through the real pipeline (classifier, slots, deterministic tool, grounded prompt, LLM) as the manager role, keeping the evidence lines for the judge.
- **Hosted model:** `claude-haiku-5-5`, also the judge by default.

**Intent accuracy** (`results/e8_intent_predictions.csv`, `results/e8_intent_report.csv`, `e8_intent_confusion.png`). Overall: classifier 87.3%, keyword baseline 77.5% (macro F1 0.89 vs 0.79).

| Questions | n | Classifier | Keyword baseline |
|---|---|---|---|
| AI-written | 62 | 91.9% | 77.4% |
| Stream B, held out | 9 | 55.6% | 77.8% |

- On the held-out questions the classifier is worse than the keyword router (5 of 9 vs 7 of 9). Three of its four misses are out-of-scope questions it answers instead of refusing ("does this member attend PT sessions?", "what is the offer that most members like?", "which club has the highest impact if closed?"). The fourth reads "what is the type of this member?" as a request for actions.
- The 5 AI-set misses are boundary and bare-number cases ("how worried should we be about 1288?", "Show the playbook for 1999", "anyone hurt by the recent staff departure?", "which members are we ringing this week?", an app how-to) (`results/e8_intent_errors.csv`).
- Stream A's questions (HANDOFFS #14) were not delivered.
- Adding 3 staff-hours examples to `what_if_budget` moved the AI-set score from 90.3% to 91.9%.
- Classification takes about 2 ms (median and p95).

**Threshold sweep** (`results/e8_threshold_sweep.csv`, `e8_threshold_sweep.png`):

| Threshold | 0.25 | 0.325 | **0.35** | 0.375 | 0.45 | 0.525 |
|---|---|---|---|---|---|---|
| accuracy | 0.859 | 0.873 | **0.873** | 0.873 | 0.845 | 0.803 |
| in-scope refused | 0.017 | 0.034 | **0.034** | 0.052 | 0.103 | 0.190 |
| off-topic answered | 0.385 | 0.308 | **0.308** | 0.308 | 0.231 | 0.077 |

At 0.35, 31% of off-topic questions are answered (62% below 0.25). Raising the threshold to 0.45 cuts that to 23% but refuses 10% of in-scope questions. Accuracy peaks at 0.325-0.375 (87.3%).

**Grounding and programmatic faithfulness** (`results/e8_answers.csv`, `results/e8_static_checks.csv`). Of 20 sampled questions, 17 went to the LLM and the 3 off-topic ones got the fixed "I don't know based on the data I have". Plan and what-if questions answer from Stream B's approved demo plan and planner.
- No answer used a number or member id missing from the evidence, and no citation pointed at a missing line.
- 15 of 17 answers (88%) pass all three static checks (8 of 13 on 2026-10-17 with the old prompt). q40 has one uncited sentence and q25 three, each inside a bullet that ends with a citation.
- 3 answers are "I don't know": rightly for b01 ("is a member sleeping dog?") and the misrouted b05, wrongly for q28, whose evidence answers it. q28 was refused in both of the last two runs but answered in both part 7 replays, so it is run-to-run variation, not a fixed failure.

**LLM-as-judge** (`results/e8_judge_calibration.csv`, `results/e8_faithfulness.csv`, `results/e8_judge_sentences.csv`, `e8_faithfulness.png`). The judge sees only the evidence lines and the answer and labels each sentence supported, unsupported or contradicted. It was calibrated first on two known bad answers (an invented discount reason and an unsupported "start with the check-in" ordering) and two good ones: it flagged both bad answers and nothing in the good ones.

| | Sentences | Supported | Unsupported | Contradicted | Fully supported answers |
|---|---|---|---|---|---|
| 17 LLM answers | 80 | 96.2% | 3.8% | 0% | 15 of 17 (88.2%; 76.9% on 2026-10-17) |

The 3 flagged sentences are "Maya Chen is the only instructor listed, so she has the highest impact" (b07, a ranking the tool does not do) and q40's "so they are the ones to call" and "Start at the top of this ranked list".

**Manual spot check** (`results/e8_spot_check.csv`), 15 answers:

| Faithful | Answers the question | Mean usefulness | Judge agrees |
|---|---|---|---|
| 13 of 15 (87%) | 12 of 15 (80%) | 3.7 / 5 | 15 of 15 |

- Unfaithful: b07 (the ranking above) and q40 (outreach advice, as in every run: the question asks for advice, and the prompt rule against it does not fully hold).
- Not answered: q28's refusal, b07, and q53. The what-if read "Is another $1,500 worth it?" as a $1,500 budget and reported no change. That slot bug was fixed after this run (`e48c01d`: "another", "extra" and "more" now add to the current limit), so q53 is the one answer here that the code no longer gives.
- Driver wording stays fixed: q05, q03 and q09 read the signed visit change correctly.

**Latency** (`results/e8_latency.csv`, `e8_latency.png`), hosted `claude-haiku-5-5`, 20 questions:

| | n | Median | p95 | Max |
|---|---|---|---|---|
| end to end | 20 | 4.52 s | 7.11 s | 8.17 s |
| LLM call only | 17 | 4.58 s | 6.25 s | 8.14 s |

This is slower than on 2026-10-17 (2.9 s) on the same hosted model, so it reflects the endpoint on the day more than the code. The what-if tool adds about 2 s of planning (two exact solves).

**Prompt variant** (`results/e8_prompt_variant.csv`, `results/e8_prompt_variant_judge.csv`). The same evidence is replayed through the old prompt and a stricter candidate (cite every sentence including the first; add no advice or remarks about the data that the evidence does not state), then checked statically and judged. The candidate was adopted as `prompt.SYSTEM`. Two runs:

| | 2026-10-17 old | new | 2026-10-20 old | new |
|---|---|---|---|---|
| answers | 13 | 13 | 17 | 17 |
| pass every static check | 4 | 11 | 9 | 17 |
| uncited sentences | 9 | 4 | 11 | 0 |
| judged sentences supported | 95.5% | 95.5% | 89.2% | 97.3% |
| fully supported answers | 9 | 10 | 9 | 15 |
| "I don't know" replies | 0 | 0 | 3 | 4 |
| median words | 57 | 61 | 54 | 38 |

The 2026-10-20 columns are in the results file; the 2026-10-17 columns are from the notebook findings. The new prompt cites every sentence and drops most remarks about what the data does not show; on the larger second run it also raises judged support from 89% to 97%. The costs are shorter answers (38 vs 54 words, and some leave out context such as why a check-in applies) and refusals that vary run to run (the extra one is q14, whose member has every offer blocked). Advice still slips through when the question asks for it (q40). Both runs use the same small sample and a judge that varies, so this is a consistent direction, not a measured gain.

**Local versus hosted model** (`results/e8_model_comparison.csv`, `results/e8_alt_answers.csv`). `qwen2.5:7b` on Ollama against the hosted `claude-haiku-5-5`, on the same 17 evidence sets and the adopted prompt, so only the answering model differs. Both are judged by the hosted judge in the same session.

| | Hosted Haiku | Local qwen2.5:7b |
|---|---|---|
| judged sentences supported | 95.1% | 95.1% |
| answers passing every static check | 88% | 71% |
| LLM time, median (p95) | 4.6 s (6.2 s) | 0.23 s (0.83 s) |

- The 7B model invents nothing the static check can see (no number or member id outside the evidence) and is as well supported by the judge. Most of its static failures are format: citations at the start of a bullet instead of the end, and citations appended to "I don't know".
- The real differences are usefulness and a few slips: list answers are bare member ids with no context (q30, q36, q40), it refused q44 although the evidence says the plan is approved, it added an unsupported reason in q05 ("Not scheduled for the week, possibly due to risk") and cited the wrong line once (q21).
- The judge's own variation is about 2 points: it scored Haiku's same answers 96.2% in the faithfulness table and 95.1% here, and an earlier part 6 run gave 93.8% (Haiku) vs 91.9% (Qwen).

**Caveats.**
- **Optimistic intent accuracy.** The AI-written questions have the same authors as the training examples in `intents.yaml`, and the 0.35 threshold was chosen on the training examples. The 91.9% is optimistic. The trustworthy number is the held-out one, where the classifier is worse than the keyword baseline (55.6% vs 77.8%), though with 9 questions the interval is wide. The weak point is refusing off-topic questions.
- **Not an independent rating.** The spot check was filled by Claude Code and checked by the owner. It is not an independent human rating, and the judge agreeing on all 15 should be read with that in mind.
- **The judge varies.** An LLM judging answers is fallible, tends to favour its own wording and varies between runs (here the judge is the same model that wrote the answers, and a 2-point difference is within its variation). Refusals vary run to run too.
- **Small samples.** 20 sampled questions (17 judged answers), 9 held-out questions, 15 spot-checked answers.
- **Best-case local latency.** The local model ran on an RTX 5090, so its latency is a best case for local hardware; a gym's office PC would be slower.
- **Scenario evidence.** The evidence comes from scenario-layer data, so faithfulness is to the evidence lines.

**Verdict.**
- **Intent routing:** the classifier beats the keyword baseline on the AI-written set (91.9% vs 77.4%) but loses on the held-out set (55.6% vs 77.8%), so we do not claim it is better than a keyword router. Its weakness is answering off-topic questions.
- **Grounding:** strong on the evidence given. No invented number or member id, 96.2% of judged sentences supported, none contradicted, and 87% faithful in the spot check. The remaining failures are advice the question asks for (q40) and a ranking the tool does not do (b07).
- **Models:** a small local model is a workable private option (member data never leaves the gym, no API cost) with looser formatting and less helpful lists. The hosted model is the better default.
