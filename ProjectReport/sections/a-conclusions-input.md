# Conclusions and future work: member intelligence input

*Member-intelligence findings, lessons and future work for the shared chapter "Conclusions and future work", to be merged with the other parts' input. Each point is backed by the section named in brackets.*

## Findings

1. **Real data supports a useful, calibrated churn model.** On 800 untouched test members the ensemble reaches F1 0.908, PR-AUC 0.973 and a Brier score of 0.035, beating a single logistic regression (0.862, 0.953, 0.056) and a visit-count rule (0.549, 0.390, 0.336). Each risk band churns within 3 points of its predicted rate, so the planner can use the probabilities at face value (E2).
2. **The proposal's trend signal holds on real members.** Members who left visited at a median 0.69 of their usual rate this month; members who stayed, at 1.00. The strongest signals are, however, same-month columns whose timing the data cannot confirm. Without them F1 is 0.817, and that is the honest lower bound (data preparation, E2).
3. **Most churn sits in one segment.** Four stable segments separate churn from 94.6% to 1.4%. The 728 "New and slipping" members, under a month in on average with visits down by half, account for about two-thirds of all members who left (689 of 1,061) (E1).
4. **Uplift can be estimated, but not yet proven.** The T-learner recovers the scenario's ground-truth ranking only in part (Spearman 0.39 overall, 0.61 for PT sessions). It ties the case-based estimator on ranking, and plans built on it keep slightly more members at the seeded staff level (24.6 against 21.0 extra), though not with more staff time. The 2,400 noisy past outcomes are too few to confirm either estimator on their own (knowledge discovery, E3).
5. **The model is less reliable for older members.** It misses about half of the churners aged 31 and over (recall 0.52), where churn is rare. This is reported on the Data & models page with a mitigation, not hidden (E2).

## Lessons

- **Contract first.** Fixing the data-table columns and a hand-made fixture on day one let the planner, rules and knowledge graph be built against the right shape before the real tables existed.
- **Guards that change numbers.** Out-of-fold scoring corrected an in-sample error rate of 2.8% to an honest 4.9% (4.6% on test), and the test-label and leakage checks turn "we did not leak" into tests that fail if someone does.
- **Notebook first, then package.** Every reported number comes from code the application runs, so the report and the app cannot drift apart.

## Recommendations for an operator

- Act on new members whose visits fall: they are most of the churn, and the driver chart shows why each one is flagged.
- Review medium-risk members aged 31 and over by hand, or use a lower review threshold for them.
- Keep visit dates and the outcome of every retention contact. With them, the next version can use recency and regularity features, validate on later months, and learn uplift from real responses.
- Hold back a random control group when adopting the plan, so the real effect of each offer can be measured instead of assumed.

## Future work

1. **Real, time-stamped data.** Validate on later months instead of a random split, add recency and regularity features, and model time to churn with survival methods. These handle members still active at the cut-off, the censoring this project had to drop.
2. **Settle the leakage question** with the operator's record timing. If the current-month columns turn out to be recorded after the churn month, serve the 12-feature model.
3. **Learn uplift from real randomised contacts**, replace the scenario's assumed effects, and compare the T-learner with stronger meta-learners such as the X-learner (Künzel et al., 2019).
4. **Monitor after each rebuild.** The model card already records calibration and fairness. Alerting when they drift would make rebuilds safe to automate.
5. **Fairness mitigation** for the 31+ age band, for example a group-specific review threshold, measured as a trade-off between recall and false alarms.
6. **Items dropped from the proposal:** Gaussian-mixture segmentation, class recommendations, and decision-tree surrogate rules for explanations (course-mapping appendix).
