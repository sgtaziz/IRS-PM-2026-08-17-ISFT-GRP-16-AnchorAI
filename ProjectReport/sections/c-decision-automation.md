# Decision automation: rules and knowledge acquisition

*Code in `SystemCode/backend/anchorai/reasoning/`, rules in `reasoning/rules/*.yaml`, thresholds in `SystemCode/notebooks/c_rules.ipynb`, checks in `c_e6_rules.ipynb` (results in `notebooks/results/`).*

## What the rule base does

The churn model says who is at risk. The rule base says what staff may do about it. For each member it turns the facts we know (scores, attendance, contract, contacts, knowledge-graph signals) into the offers that are allowed, the channel for each, and the reason. The optimiser only sees offers that survive the rules.

Rules are plain data, not code. They are YAML files that an admin can read, test and change in the app, and each one names where it came from.

## The rule engine

`reasoning/engine.py` is a forward-chaining engine: it matches rules against a working memory of facts, fires one, and repeats until nothing new matches.

1. **Match.** The agenda is every enabled rule that has not fired and whose conditions all hold. A condition is `<fact> <op> <value>` (`reasoning/conditions.py`), parsed with a regular expression and never `eval`.
2. **Resolve conflicts.** The rule with the highest priority fires: salience first, then the number of conditions (more specific first), then file order (`_priority` in `engine.py`). This is the same for all three kinds of rule.
3. **Fire.** A rule does exactly one of three things (`reasoning/models.py`):

   | Kind | Effect | Count |
   |---|---|---|
   | Derive | asserts a new fact, e.g. `falling_regular = true` | 8 |
   | Playbook | proposes an offer on a channel | 16 |
   | Guardrail | blocks named offers, or all offers | 5 |

4. **Repeat.** Each rule fires at most once per run (refraction), so the loop always ends.
5. **Apply guardrails.** After the loop, blocked offers are removed from the proposals, and duplicates are dropped. If a guardrail blocks `all`, nothing is allowed. Guardrails therefore win over playbooks because blocks are applied last, not because they fire first.

Details that matter for correctness:

- **Missing facts do not match.** A member who was never contacted has no `days_since_last_contact`; a rule on it simply does not fire. A fact of the wrong kind never matches either, and `true` is not treated as `1` (`Condition.holds`).
- **First assertion wins.** If two derive rules assert the same fact, the first to fire sets it and later ones are kept out (`_fire`), so a fact never changes after other rules have read it.
- **Output.** `run()` returns a `RuleOutcome`: facts, firings, proposals, blocked offers (with the guardrail that blocked each) and the allowed offers. This is the contract between the rule engine and the optimiser (`models.py`).

## The rule base

29 rules, in three files (`reasoning/rules/derive.yaml`, `playbook.yaml`, `guardrails.yaml`).

**Derive, D01 to D08.** They name a pattern once, so playbooks and traces read in plain words.

| Rule | Concludes | Condition (summary) |
|---|---|---|
| D01 | `falling_regular` | lifetime visits ≥ 2 a week and `trend_ratio` ≤ 0.7 |
| D02 | `new_member` | `lifetime` ≤ 1 month |
| D03 | `disengaged` | visits this month < 0.5 a week and `trend_ratio` < 0.8 |
| D04 | `disengaged` | `lifetime` ≤ 1 and visits this month < 0.5 a week |
| D05 | `high_value_at_risk` | high risk band and `monthly_value` ≥ 54 |
| D06 | `social_member` | joined through a friend |
| D07, D08 | `routine_disrupted` | an anchor instructor left (D07), or a class they attend was cancelled (D08) |

**Playbooks, P01 to P08.** Each has a twin, with the same code plus "b", for members with no phone on file.

| Rule | Proposes | Channel (phone / no phone) | Salience |
|---|---|---|---|
| P03 routine disrupted | check-in message | SMS / email | 45 |
| P01 new and slipping | free PT session | call / in person | 40 |
| P02 falling regular | check-in message | call / email | 40 |
| P06 high-value at risk | free PT session | call / in person | 35 |
| P04 social, medium or high risk | class pass | SMS / email | 30 |
| P05 month-to-month, high risk | discounted month | call / email | 25 |
| P07 disengaged, medium or high risk | check-in message | SMS / email | 20 |
| P08 medium risk | check-in message | SMS / email | 10 |

**Guardrails, G01 to G05.**

| Rule | Blocks | When |
|---|---|---|
| G01 contact fatigue | all offers | contacts in the last 30 days have reached the cap (default 1) |
| G02 offer cap | all offers | offers in the last 90 days have reached the cap (default 2) |
| G03 discount eligibility | discounted month | `contract_period` ≠ 1 |
| G04 low risk | free PT, class pass, discounted month | low risk band |
| G05 PT eligibility | free PT | a free PT session in the last 90 days |

Every rule has a mandatory `source` field: "simulated interviews 2026-10-16" (see below), "team assumption" (D05, P06), "team policy" or "offer catalogue eligibility" (guardrails), or "channel fallback ... review RULE-3 2026-10-17" for the no-phone twins.

### Facts the rules read

`reasoning/facts.py` lists every input fact in `KNOWN_FACTS`, with its type and source:

- **Member and model facts:** the model features, `churn_prob`, `risk_band`, `segment`, `monthly_value`, `club_id`.
- **Contact facts:** `days_since_last_contact`, `contacts_last_30d`, `offers_last_90d`, `pt_last_90d`, `at_contact_cap`, `at_offer_cap`. They combine the synthetic intervention history with the contacts staff log in the app (`contact_facts`). A logged outcome is a contact; it counts as an offer unless it was `no_answer`, and as a PT session only if accepted. So next week's plan cannot contact last week's members again.
- **Caps:** `at_contact_cap` and `at_offer_cap` compare those counts with the two caps on the Offers & constraints page (W41), so an admin changes the guardrail without touching a rule.
- **Phone:** `phone` decides between a rule and its "b" twin.
- **Knowledge-graph facts:** `lost_anchor_instructor`, `anchor_instructor_share`, `class_cancelled`, `cohort_risk` come from the graph (see the knowledge and interaction section). If the graph is down, these facts are absent and the rules on them do not fire; the rest still runs.

## Validation

`reasoning/validate.py` checks a rule base before it is used. **Errors** block saving; **warnings** do not.

| Severity | What it catches |
|---|---|
| Error | duplicate rule ids; an unknown fact, offer or channel; a literal of the wrong type (e.g. `risk_band >= 0.6`); conditions on one fact that contradict each other; a derive rule that overwrites a measured fact; a channel the catalogue does not offer for that offer |
| Warning | an unknown category value (e.g. a segment that does not exist); a playbook that is always blocked by a guardrail; a condition no rule can make true, or a fact asserted only by disabled rules; an inactive offer; two derive rules that assert different values for one fact when both can match |

The shipped rule base has 0 issues (`notebooks/results/e6_validation_issues.csv`, empty).

### Regression cases

`tests/fixtures/rule_cases.yaml` holds 29 hand-built members. Each starts from a steady, low-risk member, changes some facts, and states which rules must fire, which must stay silent, the allowed offers in order, and the exact blocked offers. `tests/test_rule_cases.py` runs them, and E6 reports 29 of 29 matching (`notebooks/results/e6_scenario_cases.csv`, `c_e6_rules.ipynb` finding 1). The cases check that the rules do what we meant. They do not show that what we meant is right.

## Knowledge acquisition

**Data first.** `c_rules.ipynb` runs draft rules on all 4,000 members. It shows churn rates by bin on the training split only, then how often each rule fires and whether each derived pattern separates churners from the base rate. Thresholds are not tuned against the scenario's `true_uplift`, because E4 and E6 are scored on that. The caveat from member intelligence applies: `trend_ratio` and current-month visits are suspect features (`a-data-preparation.md`, leakage check), so lift for rules built on them is optimistic.

**Simulated interviews.** We wrote a script (`Miscellaneous/interviews/interview_script.md`) and ran it as three interviews dated 2026-10-16: an independent owner-manager, an area manager, and a membership and community lead (`Miscellaneous/interviews/2026-10-16_*_simulated.md`).

> **These interviews are simulated.** No real person was interviewed. Each interviewee is a persona played by an AI model (Claude Sonnet, via Claude Code) from a written brief. The model answered the script without seeing the rule base. The answers stand in for practitioner input and are plausible expert opinion, not evidence. Each file says so at the top, rule sources say "simulated interviews", and `docs/AI_USE.md` logs the use. The report must not describe them as real interviews or as validation by practitioners.

**What changed because of them** (`notebooks/c_rules.ipynb` section 6, `c_e6_rules.ipynb` finding 12):

- **D01:** a 20% dip is noise, so the fall was raised. The data showed smaller drops also churn, so the threshold is a compromise at `trend_ratio` ≤ 0.7. It covers 72 members (127 before).
- **D03:** now also requires `trend_ratio` < 0.8, so members who always came rarely are not flagged. It covers 315 members (502 before).
- **D04 (new):** a new member with almost no visits cannot show a fall in a short history. It covers 258 members.
- **P02:** a free PT session feels salesy for a fading regular, so P02 proposes a check-in message.
- **P05:** discounts only for month-to-month members, and last among offers.
- **P07 and P08:** email is rarely read, so these use SMS, with an email twin for members without a phone. P07 reaches 271 members by SMS and 28 by email.
- **G01 and G02:** interviewees said once per 14 days to once a month, and 1 to 2 offers per 90 days. The stricter team defaults stay.
- **No rule:** a contract-ending rule was dropped (the Kaggle data shows no renewal risk, and an interviewee's window had too few members).

**Not covered.** There is no opt-out or consent fact, so "never contact opted-out members" cannot be written as a rule. We decided it is out of scope: consent is assumed to be handled in the gym's messaging tool (`c_e6_rules.ipynb`, part 2 and finding 8).

## Rule administration (W40)

Admins manage the rule base on the Rules page (`ProjectReport/user-guide.md`, section 7). The logic is in `reasoning/versions.py` and `reasoning/service.py`.

- **Versions.** Every save adds a numbered version with a mandatory note and the author. The active version is the one the engine uses; with none in the database, it falls back to the YAML files (`service.active_rules`). Nothing is overwritten.
- **Dry-run check.** Before saving, the draft is parsed and validated (`check_draft`). A save with a parse error or a validation error is refused; warnings are shown.
- **Test on a member.** Admins can run the saved rules, or an unsaved YAML draft (`run_draft`), on any member and read the same trace as on Member 360.
- **Enable and disable.** A toggle saves a new version (`set_enabled`). A disabled rule stays in the file and is skipped by the engine.
- **Rollback.** Activating an older version makes it live, after validation, and adds an audit entry (`activate_version`). It works even when the active version is broken. Newer versions are kept.
- **Concurrent edits.** Each write names the version the editor saw. If another admin saved first, the write is refused ("Rules changed since you opened them") and the page reloads (`StaleRules`).
- **Audit.** Every write records an audit entry with the rules added, removed and changed (`record_audit` in `save_version`).

**Live override check.** When a manager adds or changes a contact in a plan, the page calls `POST /api/rules/check` (`api/routers/rules.py`, roles manager and admin; `reasoning/check.py`). It runs the active rules for the member and reports, for each proposed member, offer and channel:

- `allowed` and the guardrails that violate it, with their descriptions
- `on_playbook`: whether a playbook proposed this offer
- `channel_offered` (the offer supports the channel, and SMS or call needs a phone) and `offer_active`

A manager can still override the plan, but the screen shows which rule it breaks (`AddContactDialog.vue`).

## Explainability

The firing trace is the explanation for the rule part of every decision.

- **Trace.** Each `RuleFiring` (`anchorai/schemas.py`) holds the rule id, its description, the facts that matched it (`facts_matched`) and its effect, such as `assert falling_regular=true`, `propose checkin_message via call` or `block discount_1m`. Firings are listed in firing order. When a guardrail removes an offer, the trace shows which one.
- **Plan items.** `explain_plan` (`optimisation/explain.py`) attaches the member's trace to each plan item's `Explanation`, with churn drivers, similar past cases, graph signals and a one-paragraph summary that quotes the playbook that proposed the offer.
- **Screens.** The `RuleTrace` component (`frontend/src/components/RuleTrace.vue`) shows allowed offers with their channel and rule code, blocked offers with the reason, and the rules fired in order. Derived facts are violet, playbook proposals green and guardrails red. Facts use short names from the glossary (for example "Trend ratio: 0.62"). It appears on Member 360 and in the Rules page's test panel.

## Results in brief

E6 tests the rule base on all 4,000 members; the full method and findings are in `c-experiments-e6-e8.md`. Headlines from `c_e6_rules.ipynb` section 5 (run 2026-10-20):

- 29 rules, 0 validator issues, 29 of 29 cases match.
- Guardrails remove 1,080 of 3,448 proposals (31.3%), 1,029 of them by G01.
- 386 members have no phone on file. They get the email or in-person twin, and none is proposed an SMS or a call.
- G03 never removes a proposal today, because P05 and P05b already require month-to-month. It is a safety net for manual overrides and future playbooks.

Rule firing counts per rule are in `notebooks/results/e6_rule_coverage.csv` and `notebooks/figures/e6_rule_coverage.png`.

**Caveats.** The rules are hand-written, so the case tests are optimistic. Facts from the knowledge graph and contact history come from the synthetic scenario layer, so how often they fire reflects our simulator, not real gyms.
