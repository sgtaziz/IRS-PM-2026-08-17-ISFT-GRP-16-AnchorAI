# Leakage check (A2)

Suspect columns: month_to_end_contract, contract_progress, avg_class_frequency_current_month, trend_ratio, freq_drop.

| variant | features | cv_f1 | cv_pr_auc | cv_brier | test_f1 | test_pr_auc | test_brier |
|---|---|---|---|---|---|---|---|
| with_suspect | 17.0 | 0.907 | 0.972 | 0.039 | 0.908 | 0.974 | 0.034 |
| without_suspect | 12.0 | 0.814 | 0.897 | 0.078 | 0.817 | 0.9 | 0.069 |

Dropping the suspect set lowers test PR-AUC by 0.074. The signal is real but not the whole
model: without the suspect set the ensemble still reaches PR-AUC 0.900.
The production model keeps the suspect columns because the current month's visits and the months
left on the contract are both known at the time the weekly plan is made. If the Kaggle label was
recorded after that month ended, the "without" row is the honest estimate; the report shows both.
