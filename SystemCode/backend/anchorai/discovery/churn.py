"""Calibrated churn ensemble (PLAN.md A4, experiment E2).

The test split is touched only by `evaluate`. Resampling happens inside each training
fold (imblearn Pipeline), and calibration uses a held-out slice of the training split.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTENC
from imblearn.pipeline import Pipeline
from lightgbm import LGBMClassifier
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.preprocessing import StandardScaler

from anchorai.features import CATEGORICAL, FEATURES, SUSPECT

RESAMPLING = ("smote_nc", "class_weight")
CV_FOLDS = 5
CALIBRATION_SHARE = 0.2
AGE_BANDS = {"18-25": (0, 25), "26-30": (26, 30), "31+": (31, 200)}


def _make(kind: str, resampling: str, columns: list[str], seed: int) -> Pipeline:
    categorical = [i for i, c in enumerate(columns) if c in CATEGORICAL]
    numeric = [i for i, c in enumerate(columns) if c not in CATEGORICAL]
    weight = "balanced" if resampling == "class_weight" else None
    if kind == "lr":
        scale = ColumnTransformer([("num", StandardScaler(), numeric)], remainder="passthrough")
        model = Pipeline(
            [("scale", scale), ("lr", LogisticRegression(max_iter=2000, class_weight=weight))]
        )
    else:
        model = LGBMClassifier(
            n_estimators=300,
            learning_rate=0.03,
            num_leaves=15,
            min_child_samples=20,
            subsample=0.8,
            subsample_freq=1,
            colsample_bytree=0.8,
            class_weight=weight,
            random_state=seed,
            n_jobs=1,
            deterministic=True,
            verbose=-1,
        )
    steps = []
    if resampling == "smote_nc":
        steps.append(("smote", SMOTENC(categorical_features=categorical, random_state=seed)))
    return Pipeline([*steps, ("model", model)])


@dataclass
class ChurnModel:
    columns: list[str]
    resampling: str
    lr: Pipeline
    lgbm: Pipeline
    platt: LogisticRegression
    threshold: float
    lr_baseline: np.ndarray

    def raw_proba(self, x: pd.DataFrame) -> np.ndarray:
        values = x[self.columns].to_numpy()
        return (self.lr.predict_proba(values)[:, 1] + self.lgbm.predict_proba(values)[:, 1]) / 2

    def predict_proba(self, x: pd.DataFrame) -> np.ndarray:
        return self.platt.predict_proba(_logit(self.raw_proba(x)))[:, 1]

    def contributions(self, x: pd.DataFrame) -> pd.DataFrame:
        """Per-feature log-odds pushes towards churn: LR terms averaged with LightGBM SHAP."""
        values = x[self.columns].to_numpy()
        lr_pipe = self.lr[-1]
        scale, lr = lr_pipe.named_steps["scale"], lr_pipe.named_steps["lr"]
        z = scale.transform(values)
        lr_terms = (z - self.lr_baseline) * lr.coef_[0]
        order = [*scale.transformers_[0][2], *scale.transformers_[1][2]]
        lr_contrib = np.empty_like(lr_terms)
        lr_contrib[:, order] = lr_terms
        shap = self.lgbm[-1].predict(values, pred_contrib=True)[:, :-1]
        return pd.DataFrame((lr_contrib + shap) / 2, index=x.index, columns=self.columns)


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p)).reshape(-1, 1)


def _metrics(y: np.ndarray, p: np.ndarray, threshold: float) -> dict:
    pred = p >= threshold
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "f1": float(f1_score(y, pred, zero_division=0)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "pr_auc": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "threshold": float(threshold),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def _best_f1_threshold(y: np.ndarray, p: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(y, p)
    f1 = 2 * precision * recall / np.maximum(precision + recall, 1e-12)
    return float(thresholds[np.argmax(f1[:-1])])


def cross_validate(
    x: pd.DataFrame, y: pd.Series, resampling: str, columns: list[str], seed: int
) -> dict:
    """Out-of-fold ensemble metrics; resampling is refit inside every fold."""
    folds = StratifiedKFold(CV_FOLDS, shuffle=True, random_state=seed)
    values = x[columns].to_numpy()
    p = np.mean(
        [
            cross_val_predict(
                _make(kind, resampling, columns, seed), values, y, cv=folds, method="predict_proba"
            )[:, 1]
            for kind in ("lr", "lgbm")
        ],
        axis=0,
    )
    return _metrics(y.to_numpy(), p, 0.5)


def fit(
    x: pd.DataFrame, y: pd.Series, resampling: str, columns: list[str], seed: int
) -> ChurnModel:
    fit_pos, cal_pos = train_test_split(
        np.arange(len(x)), test_size=CALIBRATION_SHARE, stratify=y, random_state=seed
    )
    x_fit, y_fit = x.iloc[fit_pos], y.iloc[fit_pos].to_numpy()
    x_cal, y_cal = x.iloc[cal_pos], y.iloc[cal_pos].to_numpy()
    values = x_fit[columns].to_numpy()
    lr = _make("lr", resampling, columns, seed).fit(values, y_fit)
    lgbm = _make("lgbm", resampling, columns, seed).fit(values, y_fit)
    baseline = lr[-1].named_steps["scale"].transform(values).mean(axis=0)
    model = ChurnModel(columns, resampling, lr, lgbm, LogisticRegression(), 0.5, baseline)
    model.platt.fit(_logit(model.raw_proba(x_cal)), y_cal)
    model.threshold = _best_f1_threshold(y_cal, model.predict_proba(x_cal))
    return model


def _fairness(y: np.ndarray, p: np.ndarray, threshold: float, groups: pd.Series) -> dict:
    rows = {}
    for name in sorted(groups.unique()):
        mask = (groups == name).to_numpy()
        yy, pred = y[mask], p[mask] >= threshold
        negatives = max((yy == 0).sum(), 1)
        rows[str(name)] = {
            "n": int(mask.sum()),
            "churn_rate": float(yy.mean()),
            "recall": float(recall_score(yy, pred, zero_division=0)),
            "precision": float(precision_score(yy, pred, zero_division=0)),
            "fpr": float(((pred == 1) & (yy == 0)).sum() / negatives),
        }
    recalls = [r["recall"] for r in rows.values()]
    fprs = [r["fpr"] for r in rows.values()]
    return {
        "groups": rows,
        "recall_gap": float(max(recalls) - min(recalls)),
        "fpr_gap": float(max(fprs) - min(fprs)),
    }


def age_band(age: pd.Series) -> pd.Series:
    return pd.cut(age, [lo - 1 for lo, _ in AGE_BANDS.values()] + [200], labels=list(AGE_BANDS))


@dataclass
class ChurnResult:
    model: ChurnModel
    probabilities: pd.Series
    contributions: pd.DataFrame
    card: dict


def train(features: pd.DataFrame, churn: pd.Series, split: pd.Series, seed: int) -> ChurnResult:
    train_mask, test_mask = split == "train", split == "test"
    x_train, y_train = features[train_mask], churn[train_mask]
    x_test, y_test = features[test_mask], churn[test_mask].to_numpy()
    safe = [c for c in FEATURES if c not in SUSPECT]

    resampling_cv = {r: cross_validate(x_train, y_train, r, FEATURES, seed) for r in RESAMPLING}
    chosen = max(
        RESAMPLING, key=lambda r: (round(resampling_cv[r]["pr_auc"], 3), -resampling_cv[r]["brier"])
    )

    leakage = {}
    for variant, columns in (("with_suspect", FEATURES), ("without_suspect", safe)):
        variant_model = fit(x_train, y_train, chosen, columns, seed)
        leakage[variant] = {
            "columns": columns,
            "cv": cross_validate(x_train, y_train, chosen, columns, seed),
            "test": _metrics(y_test, variant_model.predict_proba(x_test), variant_model.threshold),
        }

    model = fit(x_train, y_train, chosen, FEATURES, seed)
    p_test = model.predict_proba(x_test)

    rule_threshold = _best_f1_threshold(
        y_train.to_numpy(), -x_train["avg_class_frequency_current_month"].to_numpy()
    )
    visit_rule = _metrics(
        y_test, (-x_test["avg_class_frequency_current_month"] >= rule_threshold).astype(float), 0.5
    )
    visit_rule["rule"] = f"churn if visits per week this month <= {-rule_threshold:.2f}"
    single_lr = _make("lr", "class_weight", FEATURES, seed).fit(
        x_train[FEATURES].to_numpy(), y_train
    )
    single = _metrics(y_test, single_lr.predict_proba(x_test[FEATURES].to_numpy())[:, 1], 0.5)

    true_frac, pred_mean = calibration_curve(y_test, p_test, n_bins=10, strategy="quantile")
    raw_true, raw_pred = calibration_curve(
        y_test, model.raw_proba(x_test), n_bins=10, strategy="quantile"
    )

    card = {
        "model": f"mean(LR, LightGBM) + Platt calibration, resampling={chosen}",
        "features": FEATURES,
        "n_train": int(train_mask.sum()),
        "n_test": int(test_mask.sum()),
        "test": _metrics(y_test, p_test, model.threshold),
        "resampling": {"chosen": chosen, **resampling_cv},
        "leakage": leakage,
        "baselines": {"visit_rule": visit_rule, "single_lr": single},
        "calibration": {
            "calibrated": {"predicted": pred_mean.tolist(), "observed": true_frac.tolist()},
            "uncalibrated": {"predicted": raw_pred.tolist(), "observed": raw_true.tolist()},
        },
        "fairness": {
            "age_band": _fairness(y_test, p_test, model.threshold, age_band(x_test["age"])),
            "gender": _fairness(y_test, p_test, model.threshold, x_test["gender"].astype(int)),
        },
    }
    probabilities = pd.Series(
        model.predict_proba(features), index=features.index, name="churn_prob"
    )
    return ChurnResult(model, probabilities, model.contributions(features), card)
