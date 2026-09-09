# -*- coding: utf-8 -*-
"""
SIH PS 26017 — Land Acquisition / Infra Project Delay Risk
Model training + selection script (ML ONLY — no dashboard / hosting code)

What this does
---------------
1. Loads the pre-split train / val / test CSVs (project-level split, already
   leakage-checked per MODELING_GUIDE.txt).
2. Builds a leakage-safe feature matrix (drops target/meta columns AND the
   two mandatory-exclusion time-overrun columns).
3. Trains several candidate classifiers appropriate for the ~72/28 class
   imbalance (Logistic Regression baseline, Random Forest, XGBoost, LightGBM,CatBoost).
4. Selects the best model on the VALIDATION set (never touches test during
   selection).
5. Evaluates the single selected model ONCE on the held-out TEST set.
6. Saves the fitted model + the exact column schema needed for inference,
   plus a feature-importance table, so a separate script can score new/
   unlabeled projects and explain the predictions (see explain_and_score.py).

Run:
    python train_model.py --data_dir extracted

Outputs (written to --out_dir, default "model_output"):
    model_bundle.joblib          -> {"model": ..., "columns": [...], "model_name": ...}
    model_comparison.csv         -> validation metrics for every candidate model
    test_metrics.txt             -> final, once-only test set metrics
    feature_importance.csv       -> global feature importance of the final model
"""
import argparse
import os
import json
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    f1_score, precision_score, recall_score, roc_auc_score,
    average_precision_score, confusion_matrix, classification_report,
)
import joblib

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Columns that must NEVER be used as classifier features.
# Per MODELING_GUIDE.txt: time_overrun_months / _was_missing are near-direct
# proxies for the target and are excluded even though the train/val/test
# files already have them stripped (the inference file still carries them,
# so we drop defensively everywhere).
# ---------------------------------------------------------------------------
DROP_COLS = [
    "target_is_delayed", "label_confidence_tier", "is_unlabeled",
    "ml_split_v2", "project_id", "quarter",
    "time_overrun_months", "time_overrun_months_was_missing",
]
CAT_COLS = ["region_final", "sector_extracted"]


def load(data_dir, name):
    return pd.read_csv(os.path.join(data_dir, name))


def prep(df, cat_dummy_cols=None, fit=False):
    """One-hot encode categoricals; fit column schema on TRAIN only."""
    y = df["target_is_delayed"].astype(int) if "target_is_delayed" in df.columns and df["target_is_delayed"].notna().all() else \
        (df["target_is_delayed"] if "target_is_delayed" in df.columns else None)
    X = df.drop(columns=[c for c in DROP_COLS if c in df.columns])
    X = pd.get_dummies(X, columns=[c for c in CAT_COLS if c in X.columns], dummy_na=True)
    if fit:
        cat_dummy_cols = X.columns.tolist()
    else:
        X = X.reindex(columns=cat_dummy_cols, fill_value=0)
    return X, y, cat_dummy_cols


def evaluate(model, X, y, needs_scaling=False, scaler=None):
    Xe = scaler.transform(X) if needs_scaling else X
    proba = model.predict_proba(Xe)[:, 1]
    pred = (proba >= 0.5).astype(int)
    return {
        "f1": f1_score(y, pred),
        "precision": precision_score(y, pred),
        "recall": recall_score(y, pred),
        "roc_auc": roc_auc_score(y, proba),
        "pr_auc": average_precision_score(y, proba),
    }, proba, pred


def main(data_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    print("Loading data...")
    train = load(data_dir, "infra_projects_train.csv")
    val = load(data_dir, "infra_projects_val.csv")
    test = load(data_dir, "infra_projects_test.csv")

    X_train, y_train, cols = prep(train, fit=True)
    X_val, y_val, _ = prep(val, cat_dummy_cols=cols)
    X_test, y_test, _ = prep(test, cat_dummy_cols=cols)

    print(f"Train rows: {len(X_train)} | Val rows: {len(X_val)} | Test rows: {len(X_test)}")
    print(f"Feature count: {X_train.shape[1]}")

    neg = (y_train == 0).sum()
    pos = (y_train == 1).sum()
    scale_pos_weight = neg / pos
    print(f"Class balance -> not_delayed(0): {neg} | delayed(1): {pos} | scale_pos_weight={scale_pos_weight:.3f}")

    # Standardized copies for the linear baseline only (tree models don't need scaling)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    candidates = {}
    metrics_rows = []

    # ---- 1. Logistic Regression baseline ----
    print("\nTraining Logistic Regression (baseline)...")
    logreg = LogisticRegression(class_weight="balanced", max_iter=2000, n_jobs=-1)
    logreg.fit(X_train_scaled, y_train)
    m, _, _ = evaluate(logreg, X_val, y_val, needs_scaling=True, scaler=scaler)
    candidates["logistic_regression"] = {"model": logreg, "needs_scaling": True}
    metrics_rows.append({"model": "logistic_regression", **m})
    print(f"  val: {m}")

    # ---- 2. Random Forest ----
    print("Training Random Forest...")
    rf = RandomForestClassifier(
        n_estimators=500, max_depth=12, min_samples_leaf=5,
        class_weight="balanced", n_jobs=-1, random_state=42,
    )
    rf.fit(X_train, y_train)
    m, _, _ = evaluate(rf, X_val, y_val)
    candidates["random_forest"] = {"model": rf, "needs_scaling": False}
    metrics_rows.append({"model": "random_forest", **m})
    print(f"  val: {m}")

    # ---- 3. XGBoost ----
    print("Training XGBoost...")
    import xgboost as xgb
    xgb_model = xgb.XGBClassifier(
        n_estimators=600, max_depth=5, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
        reg_lambda=1.0, scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr", early_stopping_rounds=40,
        n_jobs=-1, random_state=42,
    )
    xgb_model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    m, _, _ = evaluate(xgb_model, X_val, y_val)
    candidates["xgboost"] = {"model": xgb_model, "needs_scaling": False}
    metrics_rows.append({"model": "xgboost", **m})
    print(f"  val: {m} | best_iteration={xgb_model.best_iteration}")

    # ---- 4. LightGBM ----
    print("Training LightGBM...")
    import lightgbm as lgb
    lgb_model = lgb.LGBMClassifier(
        n_estimators=600, max_depth=6, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.8, min_child_samples=20,
        reg_lambda=1.0, class_weight="balanced",
        n_jobs=-1, random_state=42, verbosity=-1,
    )
    lgb_model.fit(
        X_train, y_train, eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(40, verbose=False)],
    )
    m, _, _ = evaluate(lgb_model, X_val, y_val)
    candidates["lightgbm"] = {"model": lgb_model, "needs_scaling": False}
    metrics_rows.append({"model": "lightgbm", **m})
    print(f"  val: {m}")

    # ---- 5. CatBoost ----
    print("Training CatBoost...")
    
    from catboost import CatBoostClassifier

    cat_model = CatBoostClassifier(
        iterations=600,
        depth=6,
        learning_rate=0.03,
        loss_function="Logloss",
        eval_metric="AUC",
        auto_class_weights="Balanced",
        random_seed=42,
        verbose=False
    )

    cat_model.fit(
        X_train,
        y_train,
        eval_set=(X_val, y_val),
        verbose=False
    )

    m, _, _ = evaluate(cat_model, X_val, y_val)

    candidates["catboost"] = {
        "model": cat_model,
        "needs_scaling": False
    }

    metrics_rows.append({
        "model": "catboost",
        **m
    })

    print(f"  val: {m}")

    # ---- Model selection (by validation PR-AUC, a good metric for imbalance) ----
    comparison = pd.DataFrame(metrics_rows).set_index("model")
    comparison.to_csv(os.path.join(out_dir, "model_comparison.csv"))
    print("\n=== VALIDATION COMPARISON ===")
    print(comparison.round(4))

    best_name = comparison["pr_auc"].idxmax()
    best = candidates[best_name]
    best_model = best["model"]
    needs_scaling = best["needs_scaling"]
    print(f"\nSelected best model by validation PR-AUC: {best_name}")

    # ---- Final, once-only test evaluation of the selected model ----
    test_metrics, test_proba, test_pred = evaluate(
        best_model, X_test, y_test, needs_scaling=needs_scaling, scaler=scaler
    )
    cm = confusion_matrix(y_test, test_pred)
    report = classification_report(y_test, test_pred, target_names=["not_delayed", "delayed"])

    with open(os.path.join(out_dir, "test_metrics.txt"), "w") as f:
        f.write(f"Selected model: {best_name}\n\n")
        f.write("TEST SET METRICS (final, evaluated once)\n")
        for k, v in test_metrics.items():
            f.write(f"{k}: {v:.4f}\n")
        f.write("\nConfusion matrix (rows=actual, cols=pred [0,1]):\n")
        f.write(np.array2string(cm))
        f.write("\n\nClassification report:\n")
        f.write(report)

    print(f"\n=== TEST (final, {best_name}) ===")
    for k, v in test_metrics.items():
        print(f"{k}: {v:.4f}")
    print("Confusion matrix:\n", cm)

    # ---- Feature importance (tree models expose this natively; for logistic
    # regression fall back to absolute standardized coefficients) ----
    if hasattr(best_model, "feature_importances_"):
        importances = pd.Series(best_model.feature_importances_, index=X_train.columns)
    else:
        importances = pd.Series(np.abs(best_model.coef_[0]), index=X_train.columns)
    importances = importances.sort_values(ascending=False)
    importances.to_csv(os.path.join(out_dir, "feature_importance.csv"))
    print("\nTop 15 features:")
    print(importances.head(15))

    # ---- Save the candidate as a versioned, timestamped bundle (always) ----
    from datetime import datetime

    bundle = {
        "model": best_model,
        "model_name": best_name,
        "columns": cols,
        "needs_scaling": needs_scaling,
        "scaler": scaler if needs_scaling else None,
        "test_metrics": test_metrics,
    }

    version = datetime.now().strftime("%Y%m%d_%H%M%S")
    versioned_path = os.path.join(out_dir, f"model_bundle_{version}.joblib")
    joblib.dump(bundle, versioned_path)
    print(f"Saved versioned candidate -> {versioned_path}")

    # ---- Promotion: only overwrite the PRODUCTION model_bundle.joblib if the
    # new candidate beats (or ties, within tolerance) the currently deployed
    # model on the same held-out test set. This is the promotion step
    # described in MODEL_LIFECYCLE.md ("a newly trained model must not
    # automatically replace the existing production model"). ----
    PROMOTION_METRIC = "pr_auc"   # metric used to compare candidate vs. production
    PROMOTION_TOLERANCE = 0.0     # candidate must be >= production - tolerance to be promoted

    production_path = os.path.join(out_dir, "model_bundle.joblib")
    promote = True
    production_metrics = None

    if os.path.exists(production_path):
        try:
            prod_bundle = joblib.load(production_path)
            prod_model = prod_bundle["model"]
            prod_needs_scaling = prod_bundle.get("needs_scaling", False)
            prod_scaler = prod_bundle.get("scaler")
            prod_cols = prod_bundle["columns"]

            # Re-build test features against the PRODUCTION model's own column
            # schema (it may differ slightly from the new candidate's schema).
            X_test_prod, y_test_prod, _ = prep(test, cat_dummy_cols=prod_cols)
            production_metrics, _, _ = evaluate(
                prod_model, X_test_prod, y_test_prod,
                needs_scaling=prod_needs_scaling, scaler=prod_scaler,
            )

            candidate_score = test_metrics[PROMOTION_METRIC]
            production_score = production_metrics[PROMOTION_METRIC]
            promote = candidate_score >= (production_score - PROMOTION_TOLERANCE)

            print(f"\n=== PROMOTION CHECK ({PROMOTION_METRIC}) ===")
            print(f"Candidate ({best_name}): {candidate_score:.4f}")
            print(f"Production ({prod_bundle.get('model_name', 'unknown')}): {production_score:.4f}")
            print("Decision:", "PROMOTE" if promote else "KEEP EXISTING PRODUCTION MODEL")
        except Exception as e:
            # If the existing production bundle can't be loaded/evaluated for
            # any reason, fail safe: don't silently overwrite it.
            print(f"\nCould not evaluate existing production model ({e}); "
                  f"leaving it in place. Investigate before promoting manually.")
            promote = False
    else:
        print("\nNo existing production model_bundle.joblib found — promoting candidate as the first production model.")

    if promote:
        joblib.dump(bundle, production_path)
        print(f"Promoted candidate -> {production_path} (this is what explain_and_score.py / the API will use)")
    else:
        print(f"Candidate NOT promoted. Production model_bundle.joblib left unchanged.\n"
              f"To force-promote anyway, manually copy {versioned_path} -> {production_path}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default="extracted", help="Folder with the split CSVs")
    parser.add_argument("--out_dir", default="model_output", help="Folder to write model + reports")
    args = parser.parse_args()
    main(args.data_dir, args.out_dir)
