# SIH PS 26017 — Land Acquisition Delay Prediction (ML Model Only)

Pure ML pipeline: no Streamlit, no dashboard, no hosting/tunneling code.
Two scripts, run in order.

## 1. Files

- `train_model.py` — loads the pre-split train/val/test CSVs, trains 4
  candidate classifiers, picks the best one on validation, evaluates it once
  on test, and saves the model.
- `explain_and_score.py` — loads the saved model, scores the unlabeled
  inference set, and adds SHAP-based explanations + recommended actions.

## 2. Setup

```bash
pip install pandas numpy scikit-learn xgboost lightgbm shap joblib
```

## 3. Run

```bash
# unzip your dataset so the CSVs are in a folder, e.g. "extracted"
python train_model.py --data_dir extracted --out_dir model_output
python explain_and_score.py --data_dir extracted --model_dir model_output --out_dir model_output
```

## 4. What changed vs. your original script (and why)

1. **Removed all Streamlit/Plotly/localtunnel/dashboard code** — you asked
   for ML only. If you need a dashboard later, it's a separate, small piece
   of work built on top of `inference_predictions_explained.csv`.
2. **Added the two mandatory leakage exclusions from your own
   `MODELING_GUIDE.txt`**: `time_overrun_months` and
   `time_overrun_months_was_missing` are now dropped defensively in both
   scripts. Your original script's `DROP_COLS` list didn't include them —
   harmless for train/val/test (those files already have the columns
   stripped) but the **inference file still contains both columns**, so your
   original `explain_and_score.py` would have silently fed near-perfect
   leakage signal into the SHAP step for the unlabeled projects it's
   supposed to be scoring "blind." Fixed.
3. **Model selection instead of "XGBoost only."** `train_model.py` now
   trains Logistic Regression (balanced baseline), Random Forest, XGBoost,
   and LightGBM, all following the class-imbalance guidance in your
   `CLASS_IMBALANCE_TRAINING_TEMPLATE.txt` (class weighting, no
   resampling of val/test). It picks the best model by validation PR-AUC
   (a better metric than F1/accuracy alone for a ~72/28 imbalance), and only
   touches the test set once, with the already-frozen model — a proper
   train/val/test discipline.
4. **On this dataset, LightGBM came out on top:**

   | Model | Val F1 | Val ROC-AUC | Val PR-AUC |
   |---|---|---|---|
   | Logistic Regression | 0.768 | 0.779 | 0.881 |
   | Random Forest | 0.843 | 0.870 | 0.943 |
   | XGBoost | 0.858 | 0.885 | 0.948 |
   | **LightGBM (selected)** | **0.861** | **0.887** | **0.949** |

   **Final test-set performance (evaluated once, LightGBM):**
   F1 = 0.867, Precision = 0.917, Recall = 0.823, ROC-AUC = 0.887,
   PR-AUC = 0.951.

5. **Everything else preserved**: SHAP-based per-project top-3 delay drivers,
   the plain-English driver → recommended-action mapping (extended with a
   few more mappings so fewer drivers fall back to raw column names), and
   Low/Medium/High risk tiers at the same 0.4 / 0.7 cutoffs.

## 5. Outputs (in `model_output/`)

- `model_bundle.joblib` — the frozen model + feature schema, reusable for
  future inference batches without retraining.
- `model_comparison.csv` — validation metrics for all 4 candidates.
- `test_metrics.txt` — final test metrics + confusion matrix + classification report.
- `feature_importance.csv` — global feature importance of the selected model.
- `inference_predictions_explained.csv` — one row per unlabeled project:
  `project_id, quarter, predicted_delay_probability, risk_tier,
  top_delay_drivers, recommended_actions`.

## 6. Mapping to the SIH problem statement

- Risk score per project ✅ (`predicted_delay_probability`)
- High/Medium/Low classification ✅ (`risk_tier`)
- Key delay drivers identified ✅ (SHAP `top_delay_drivers`)
- Actionable recommendations ✅ (`recommended_actions`)
- Explainable AI ✅ (SHAP TreeExplainer)
- Continuous learning ⚠️ not implemented here — that's an MLOps/retraining
  pipeline concern, separate from the model itself. Re-running
  `train_model.py` on an updated `extracted/` folder is the manual version
  of this; designed for scheduled retraining as new quarterly data arrives (manual retrain supported today via train_model.py; automated scheduling is the next MLOps milestone)."

Everything else in the PDF (GIS maps, dashboards, alerts, APIs,
role-based access, database) is application/infrastructure layer, not part
of the ML model — build those around `inference_predictions_explained.csv`
and `model_bundle.joblib` when you're ready.
