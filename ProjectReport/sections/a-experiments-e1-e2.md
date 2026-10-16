# Experiments E1 and E2 (real data)

*Stream A. Both experiments use only the real Kaggle members. Reproduce them with `uv run anchorai data build` (seed 42), then `notebooks/a_segmentation.ipynb` and `notebooks/a_churn.ipynb`. Figures are in `notebooks/figures/`, tables in `notebooks/results/`.*

## E1: Are the segments meaningful?

**Method.** K-means on seven standardised behavioural features, fitted on the training split for k = 2 to 10. Three measurements:

- silhouette on the training split
- stability: the adjusted Rand index (ARI) against five other random seeds
- how sharply the segments separate churn

**Silhouette by k** (`e1_silhouette.png`, `results/e1_silhouette_by_k.csv`):

| k | 2 | 3 | **4** | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|
| silhouette | 0.167 | 0.178 | **0.174** | 0.157 | 0.155 | 0.161 | 0.162 | 0.158 | 0.160 |

**Results.**
- **Choice of k:** silhouette is low and nearly flat, as expected for behavioural data without clean clusters. The documented rule (most detailed k within 5% of the best) chooses **k = 4** (silhouette 0.174).
- **Stability:** very high. Mean ARI across seeds is 1.00 (minimum 0.998), so the same members land in the same segments whatever the initialisation.
- **Generalisation:** the test split falls into the segments in proportions similar to the training split, within 4.2 percentage points for every segment.
- **Churn separation:** sharp. Churn rates run from 94.6% (New and slipping) through 17.4% and 12.6% down to 1.4% (Annual-contract loyalists), as profiled in `e1_profiles.png` and `results/e1_segment_profiles.csv`.

**Finding.** The segments are not geometrically crisp, but they are stable, interpretable, and separate risk by a factor of almost 70. That is what a retention team needs from them.

## E2: Does the churn model beat simple rules?

**Method.** All metrics are on the 800 untouched test members (`results/e2_model_vs_baselines.csv`). The churn class is the positive class. F1 uses each model's own threshold: the calibrated ensemble uses 0.404, chosen on the calibration slice, and the logistic regression uses 0.5.

**Baselines:**
- a single class-weighted logistic regression
- a visit rule: "churn if visits per week this month ≤ 1.63", with the threshold chosen on the training split

| Model | F1 | Precision | Recall | PR-AUC | ROC-AUC | Brier |
|---|---|---|---|---|---|---|
| **AnchorAI ensemble, calibrated** | **0.908** | 0.906 | 0.910 | **0.973** | 0.988 | **0.035** |
| Single logistic regression | 0.862 | 0.818 | 0.910 | 0.953 | 0.978 | 0.056 |
| Visit rule (≤ 1.63 visits/week) | 0.549 | 0.426 | 0.774 | 0.390 | 0.699 | 0.336 |

**Confusion matrix** (threshold 0.404, `e2_confusion.png`): 193 true positives, 19 missed churners, 20 false alarms and 568 true negatives. The precision-recall curve against the visit rule is in `e2_pr_curve.png`.

**Imbalance treatment** (5-fold CV on the training split, `results/e2_resampling_cv.csv`):

| Treatment | F1 | PR-AUC | Brier |
|---|---|---|---|
| SMOTE-NC inside each training fold | 0.905 | 0.970 | 0.039 |
| class weights (chosen) | 0.906 | 0.972 | 0.039 |

The two are equivalent here. Class weights won the documented tie-break (PR-AUC first) and are simpler.

**Leakage check** (`results/e2_leakage_test.csv`): without the five suspect columns, test F1 falls to 0.817 and PR-AUC to 0.900. Both versions are reported: the served one, and the honest lower bound if the current-month columns were recorded after the churn month.

**Calibration** (`e2_calibration.png`, `results/e2_reliability_by_band.csv`). Platt calibration moves the uncalibrated curve onto the diagonal, and each risk band churns at about its predicted rate:

| Band (test) | Members | Mean predicted | Observed churn |
|---|---|---|---|
| low (< 0.3) | 579 | 1.6% | 2.9% |
| medium (0.3–0.6) | 24 | 44.1% | 41.7% |
| high (≥ 0.6) | 197 | 95.1% | 93.9% |

**Why the probabilities are so extreme** (`e2_score_distribution.png`, `results/e2_score_distribution.csv`).
- Most members score near 0 or near 1. This is a property of the data, not an artefact: a few columns (tenure, months left on the contract, this month's visits) nearly decide the outcome, and the bands above show the extremes are honest.
- The test split, scored out-of-sample, is as extreme as the training split. Training members are scored out-of-fold, so their error rate at 0.5 (4.9%) matches the test split (4.6%).
- One consequence for the rule base is that the medium band is small: 169 of 4,000 members. `results/e2_band_cutoffs.csv` lists band sizes for lower medium cut-offs.

**Drivers.** By mean absolute SHAP value on the test split, the LightGBM component (`e2_shap.png`) relies most on the change in weekly visits, tenure and age, followed by visit trend and extra spend. This matches the segment profiles: the high-churn segment is new, younger, and visiting much less this month.

**Fairness on the test set** (`results/e2_fairness.csv`):

| Group | Members | Churn rate | Recall | False-positive rate |
|---|---|---|---|---|
| age 18–25 | 108 | 61.1% | 0.985 | 0.143 |
| age 26–30 | 425 | 28.9% | 0.943 | 0.043 |
| age 31+ | 267 | 8.6% | 0.522 | 0.004 |
| gender 0 | 389 | 26.0% | 0.861 | 0.045 |
| gender 1 | 411 | 27.0% | 0.955 | 0.023 |

- **Age:** the largest gap (recall gap 0.46). Churn among members aged 31 and over is rare (23 churners in the test split), and the model misses about half of them. This is reported rather than hidden. A mitigation for staff is to review medium-risk members in that band, or to use a lower review threshold for them.
- **Gender:** the gap is small (recall 0.86 vs 0.95). Gender is coded 0/1 in the source data, with no labels.

**Finding.** The calibrated ensemble clearly beats both baselines on every metric:
- F1 0.908 against 0.862 for logistic regression and 0.549 for the visit rule
- PR-AUC 0.973 against 0.953 and 0.390
- Brier 0.035 against 0.056 and 0.336

Its probabilities are calibrated, so the optimiser can multiply them by uplift and value at face value.

## Input to E3: the uplift baseline

The T-learner baseline (`notebooks/a_scenario_uplift.ipynb`, `results/a6_tlearner_recovery.csv`) recovers the scenario's ground-truth uplift ranking with Spearman ρ = 0.39 overall and 0.61 for PT sessions. The Qini curve in `a6_qini.png` lies well above random targeting but well below the oracle. Stream B's case-based estimator is compared against this in E3.

## Limitations

- **One real snapshot.** The Kaggle data is a single snapshot with one binary label, so there is no out-of-time validation. The test split is a random 20% of the same snapshot.
- **Leakage uncertainty.** The leakage question cannot be settled from the data alone, which is why both models are reported.
- **Synthetic scenario.** Everything that depends on the scenario layer (uplift, gym events, intervention history) is synthetic and documented in the scenario appendix. Results built on it measure recovery of known structure, not real member behaviour.
