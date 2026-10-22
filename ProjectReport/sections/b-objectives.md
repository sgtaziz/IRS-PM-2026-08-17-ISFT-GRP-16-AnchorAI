# Project objectives and success measures

The proposal set three goals: segment members interpretably, predict churn with a calibrated ensemble, and turn the predictions into a weekly action plan in which every recommendation carries a justification that staff can challenge. Building the system showed that the third goal needs more than a churn score. A plan has to know which members a contact would actually keep, respect the week's budget and staff time, and leave the final decision with people. We therefore pursued six objectives.

## Objectives

| # | Objective | Why it matters to a gym |
|---|---|---|
| O1 | **Know who is at risk, and why.** Interpretable segments and a calibrated churn probability with its drivers for every member. | Staff act on reasons, not on a bare score. |
| O2 | **Know whom a contact would keep.** Estimate, for each member and offer, the extra chance that the member stays if contacted (the offer's *uplift*). | The members most likely to leave are not always the ones a call can save; budget spent on members who would stay anyway, or leave anyway, is wasted. |
| O3 | **Plan the week within its limits.** Choose who to contact, with which offer and channel, within the budget, staff hours, offer stock and contact limits. | This is the decision a manager actually makes, and the step current retention tools do not support. |
| O4 | **Keep people in control.** Every recommendation is explained and checked against the gym's rules; managers can override with a reason and must approve; every change is recorded. | Staff distrust black-box flags. An auditable plan they can question is one they will use. |
| O5 | **Make it usable by gym staff.** One web app for admins, managers and staff, and an assistant that answers questions in plain language from the system's own data. | Front-desk staff and trainers are not analysts. |
| O6 | **Make it dependable.** Reproducible results, and a system that keeps planning when the knowledge graph or the language model is unavailable. | A tool that fails when one service is down will not be trusted with a weekly routine. |

## Success measures

Each objective has a measure, a baseline it must beat or a target it must reach, and an experiment that tests it. Experiments E1 and E2 use the real Kaggle members. E3 to E7 use the synthetic scenario layer, whose true offer effects are known, so plans can be graded against a truth that no planner sees.

| # | Measure | Baseline or target | Experiment |
|---|---|---|---|
| O1 | Segments that are stable across random seeds and separate churn clearly | Other numbers of segments (k = 2 to 10); stability across seeds | E1 |
| O1 | Churn F1 (churn class), PR-AUC and Brier score on the untouched test set; calibration by risk band | A visit-count rule; a single logistic regression | E2 |
| O1 | Information added by knowledge-graph signals (an instructor leaving, a class cancelled) to risk ranking and plan value | Churn probability alone | E7 |
| O2 | Rank correlation between estimated and true uplift, per offer and overall; true uplift of the top picks | T-learner; churn risk used as uplift; random | E3 |
| O3 | Extra members retained by the plan, per $1,000 and per staff hour, at several budgets and staff levels | Contact-all and risk-top-k at the same budget and staff hours | E4 |
| O3 | Plan feasibility | No limit broken by any plan | E4, E5 |
| O3 | Optimality gap and run time of the genetic algorithm | The proven optimum from an exact solver (CP-SAT); 2,000 members in under 30 s and 4,000 in at most 60 s | E5 |
| O4 | Rule-base consistency, expected rule firings, and plan value with and without guardrails | No validator issues; hand-built expected cases; the same playbooks without guardrails | E6 |
| O4 | Explanation and audit coverage | Every plan item explained; every write audited | Automated tests |
| O5 | Intent accuracy and faithfulness of the assistant's answers | A keyword router | E8 |
| O6 | Reproducibility and behaviour when a service is down | Same results from a fresh build; planning without the knowledge graph or the language model | Automated tests |

## Scope of the evaluation

- **The business result is measured on a synthetic gym.** The real Kaggle data has no offers and no record of who was contacted, so no real outcome of a plan exists. The scenario layer gives every member a known response to every offer. This lets plans be graded fairly, but the size of any gain depends on how that response was designed. The experiments can show that the method works when effects are of this kind; only a trial in a real gym can show how large they really are.
- **Explainability and usability are assessed by design and through the assistant's evaluation, not by user testing.** No gym staff used the system, and the manager interviews were simulated (see *Business problem*).
