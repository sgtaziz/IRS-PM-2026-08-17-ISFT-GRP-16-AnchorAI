# Data collection and preparation

*Stream A. Every figure here is reproduced by `uv run anchorai data build` (seed 42) and the notebooks named in each subsection.*

## Source data

AnchorAI is built on the public Kaggle dataset *Gym Customers Features and Churn* (A. Vinueza, CC BY-NC-SA 4.0). The dataset is cited, not redistributed: users download it into `SystemCode/data/raw/`.

- **Size and quality:** 4,000 members and 14 columns, with no missing values and no duplicate rows.
- **Label:** `Churn` marks members who left; the churn rate is 26.5%.
- **Other columns:** demographics and contract, plus two attendance measures — average weekly class frequency over the member's lifetime and in the current month.

The dataset is a single snapshot. It has no clubs, classes, instructors, offers or contact history, and no time stamps, so there is nothing to censor (PLAN.md drift item 12).

## Preparation

1. **Renaming:** column names are lower-cased to snake case (e.g. `avg_class_frequency_current_month`). Each row gets a pseudonymous `member_id` (`M0001` to `M4000`).
2. **Split:** an 80/20 split, stratified on churn, gives 3,200 training and 800 test members; both have a 26.5% churn rate. Test labels are used only to report metrics. Nothing is fitted on them, which a regression test enforces (`tests/test_discovery.py`).
3. **Contract:** the column names and types of every table are fixed in `anchorai/scenario/tables.py`. They are checked on every build together with primary keys, foreign keys and value rules (for example, every attendance row has more than zero weekly visits). A small synthetic fixture with the same columns (`tests/fixtures/`) let the other streams build before the real tables existed.

## Features

Seventeen model features (`anchorai/features/__init__.py`): the 13 Kaggle predictors plus four derived ones.

| Feature | Definition | Why |
|---|---|---|
| `trend_ratio` | this month's weekly visits ÷ lifetime weekly visits (1.0 when there are none) | the "12 visits down to 4" signal from the proposal: falling attendance precedes cancellation |
| `visit_change` | this month's minus lifetime weekly visits (negative = fewer) | the same signal on an absolute scale |
| `contract_progress` | share of the contract already used | members near the end of a contract are free to leave |
| `charges_per_month` | extra spend ÷ (months as member + 1) | spend intensity, not accumulated spend |

The median `trend_ratio` is 0.69 for members who left and 1.00 for those who stayed (`notebooks/figures/a2_trend_ratio.png`).

### Leakage check

`avg_class_frequency_current_month` and `month_to_end_contract` may be measured in the same month as the churn label (PLAN.md drift item 5). With the three features derived from them, they form the *suspect* set. The same model was trained with and without that set (`notebooks/a_features_leakage.ipynb`, `notebooks/results/a_leakage.csv`):

| Variant | Features | Test F1 | Test PR-AUC | Test Brier |
|---|---|---|---|---|
| with suspect set (served) | 17 | 0.908 | 0.973 | 0.035 |
| without suspect set | 12 | 0.817 | 0.900 | 0.069 |

The suspect columns carry real signal, but the model stays strong without them. The served model keeps them because both values are known when the weekly plan is made. If the Kaggle label were recorded after that month ended, the second row would be the honest estimate, which is why the report shows both.

## Scenario layer

The knowledge graph, the case-based reasoner, the uplift models and the optimiser need things the Kaggle data lacks. So a **scenario layer** attaches a synthetic gym to the real members (`anchorai/scenario/build.py`, parameters in Appendix "Scenario layer parameters", `docs/SCENARIO.md`).

Segmentation and the churn model (E1, E2) use only real columns. Results that depend on the scenario (E3–E7) test whether the system recovers known structure and makes better decisions against a known ground truth. They are not claims about how real members respond.

- **Gym structure:** 3 clubs, 9 instructors and 18 classes. The 1,611 members who attend group classes are spread over 1 to 3 classes at their own club, and their weekly visits add up to their real Kaggle class frequency. Members whose frequency is zero attend no class.
- **Offers:** four retention offers, each with a cost, staff time, weekly stock, channels and the staff skill it needs. The same catalogue seeds the app's editable offer table.
- **Ground truth:**
  - **Hazard:** each member has a synthetic no-contact churn hazard computed from features only, never from the real label.
  - **Offer effects:** each offer has a documented, heterogeneous effect on next-month retention. For example, a PT session helps new members most, and a discount backfires on annual members.
  - **`true_uplift`:** the realised gain in stay probability for every member and offer.
- **Gym events:**
  - **What happens:** in the week before the scoring date, the instructor with the most attendees leaves and the busiest class at another club is cancelled.
  - **Effect:** an event raises the hazard of the members it touches, in proportion to the share of their class visits it hits (`true_churn`).
  - **Why it matters:** the churn model cannot see this; only the knowledge graph can. Members who trained mostly with the departed instructor see their hazard rise 1.80× (`notebooks/results/a5_event_lift.csv`).
- **Intervention history:** 2,400 past contacts in the 12 weeks before the scoring date. 1,416 were treated with a random offer through a random allowed channel, and the rest are controls. Outcomes follow the ground truth in force that week. Because assignment is random, uplift estimators face heterogeneity and sample size, not confounding. Treated members stay 4.9 points more often than controls.

Every table is regenerated from the raw CSV and `ANCHORAI_SEED`, and two builds with the same seed produce byte-identical files.
