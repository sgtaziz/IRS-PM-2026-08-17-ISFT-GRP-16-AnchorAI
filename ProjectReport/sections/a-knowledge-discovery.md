# Knowledge discovery: segmentation, churn and an uplift baseline

*Stream A. Code in `anchorai/discovery/`; experiments in `notebooks/a_segmentation.ipynb` (E1), `notebooks/a_churn.ipynb` (E2) and `notebooks/a_scenario_uplift.ipynb` (uplift baseline).*

## Behavioural segmentation (K-means)

**Input.** Seven behavioural features, standardised:

- months as a member (log-scaled, because it is long-tailed)
- lifetime weekly visits
- visit trend
- contract length
- extra spend
- age
- group-class attendance

**Fitting.**
- K-means is fitted on the training split only. Every member is then assigned to the nearest centre.
- Each k from 2 to 10 is fitted with 10 initialisations and scored by silhouette on the training split.
- Silhouette is low and almost flat on this data (0.155–0.178, `notebooks/results/e1_silhouette_by_k.csv`), so it cannot pick k alone.
- The rule (`choose_k`): take the most detailed k between 3 and 8 whose silhouette is within 5% of the best. This gives **k = 4**, with silhouette 0.174 against the best of 0.178 at k = 3. k = 4 adds a distinct annual-contract segment that k = 3 merges away.

**Naming.** Segments are ordered by churn rate and named by fixed rules on their centres (`name_segment`), so the names survive a rebuild:

| Segment | Members | Churn rate | Typical member |
|---|---|---|---|
| New and slipping | 728 | 94.6% | 0.9 months in, visits down 52% this month |
| Established solo trainers | 1,365 | 17.4% | 4.2 months, no group classes |
| Established class-goers | 961 | 12.6% | 4.2 months, all attend classes |
| Annual-contract loyalists | 946 | 1.4% | 12-month contracts |

## Churn model

**Model.** The mean of a logistic regression and a LightGBM model over the 17 features. It is fitted on 80% of the training split; the other 20% is held out for calibration.

**Class imbalance (26.5% churn).**
- Two treatments were compared with 5-fold cross-validation on the training split:
  - SMOTE-NC oversampling, applied inside each training fold through an `imblearn` pipeline so that no synthetic row leaks into a validation fold
  - class weights
- They score almost the same (out-of-fold PR-AUC 0.970 vs 0.972; Brier 0.039 for both). Class weights were kept on the documented tie-break: PR-AUC first, then Brier.

**Calibration.**
- SMOTE and class weights both distort probabilities, and the optimiser multiplies probability × uplift × value.
- So a Platt (logistic) calibrator is fitted on the held-out 20% of the training split, never on the test set.
- The decision threshold (0.404) maximises F1 on that same held-out slice.

**Scores for every member.**
- Test members are scored by the final model.
- Each training member is scored **out-of-fold**, by a model fitted on the other four folds, so no member's score has seen its own label. In-sample scoring had made training members look easier to predict than they are: an error rate of 2.8% at 0.5, against 4.6% on test. Out-of-fold it is 4.9% against 4.6% (`notebooks/results/e2_score_distribution.csv`).
- A regression test checks that changing one training member's label never changes that member's score.

**Explanations.**
- For each member, the five largest contributions (in log-odds) become the "Why this risk score" drivers on Member 360 and the `top_drivers` field of `MemberScore`.
- Each contribution is the average of the logistic-regression term (coefficient × standardised deviation from the training mean) and LightGBM's exact tree SHAP value.

**Outputs.** Every member gets a calibrated probability, a risk band (high ≥ 0.6, medium ≥ 0.3, low otherwise), a segment and drivers. They are served by `/api/members` and handed to the rule engine and optimiser as `MemberScore`.

## Uplift baseline (T-learner)

**Method.** The T-learner (`anchorai/discovery/uplift.py`) fits one outcome model per arm, for each of the four offers and for the untreated controls, on the scenario's intervention history. Each arm model is a mean of logistic regression and a small LightGBM. A member's uplift for an offer is the predicted stay probability under that offer minus the prediction under no contact.

**Result.** Against the scenario's ground truth, the T-learner ranks (member, offer) pairs with Spearman ρ = 0.39 overall (`notebooks/results/a6_tlearner_recovery.csv`).
- It does best for PT sessions (ρ = 0.61), whose true effect is the largest and most structured.
- It does worst for check-in messages (ρ = 0.26), whose true effect is small.

It is the baseline that Stream B's case-based uplift estimator is compared with in E3.
