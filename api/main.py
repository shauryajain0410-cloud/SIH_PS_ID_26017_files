import pandas as pd
import numpy as np
import joblib
from fastapi import FastAPI, Query
import sqlite3
import os
from fastapi.middleware.cors import CORSMiddleware

from .predict_new_project import router as predict_new_project_router


app = FastAPI(
    title="Infrastructure Delay Risk API",
    description="API for project risk predictions, explanations and alerts.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://luminous-melomakarona-8b211d.netlify.app",

    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict_new_project_router)


DB_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "model_output",
    "scoring.db"
)
INFERENCE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "infra_projects_inference_unlabeled.csv"
)
PREDICTIONS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "model_output",
    "inference_predictions_explained.csv"
)
MODEL_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "model_output",
    "model_bundle.joblib"
)


def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def get_table_columns(table_name: str):
    conn = get_connection()
    try:
        rows = conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
        return {row["name"] for row in rows}
    finally:
        conn.close()


def first_existing(columns, names, default=None):
    for name in names:
        if name in columns:
            return name
    return default

def safe_float(value, default=0.0):
    try:
        if value is None:
            return default

        value = float(value)

        if not np.isfinite(value):
            return default

        return value

    except (TypeError, ValueError):
        return default


# -------------------------------------------------------------------
# BASIC
# -------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Infrastructure Delay Risk API is running",
        "version": "1.0.0"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "database": os.path.exists(DB_FILE)
    }


# -------------------------------------------------------------------
# PROJECTS
# -------------------------------------------------------------------

def query_projects(
    region="All",
    sector="All",
    risk="All",
    confidence_tier="All",
    search="",
    page=1,
    page_size=25,
    sort_by="predicted_delay_probability",
    sort_order="desc",
):
    # ------------------------------------------------------------
    # SOURCE 1: full scored prediction file
    # ------------------------------------------------------------
    if not os.path.exists(PREDICTIONS_FILE):
        raise RuntimeError(
            f"Prediction file not found: {PREDICTIONS_FILE}"
        )

    predictions_df = pd.read_csv(PREDICTIONS_FILE)

    # ------------------------------------------------------------
    # SOURCE 2: original enriched inference data
    # ------------------------------------------------------------
    if os.path.exists(INFERENCE_FILE):
        base_df = pd.read_csv(INFERENCE_FILE)
    else:
        base_df = pd.DataFrame()

    # ------------------------------------------------------------
    # Normalize score columns
    # ------------------------------------------------------------
    if "predicted_delay_probability" not in predictions_df.columns:
        raise RuntimeError(
            "predicted_delay_probability column missing from "
            "inference_predictions_explained.csv"
        )

    predictions_df["predicted_delay_probability"] = pd.to_numeric(
        predictions_df["predicted_delay_probability"],
        errors="coerce"
    ).fillna(0)

    # Normalize probability to 0-1
    predictions_df.loc[
        predictions_df["predicted_delay_probability"] > 1,
        "predicted_delay_probability"
    ] /= 100.0

    predictions_df["predicted_delay_probability"] = (
        predictions_df["predicted_delay_probability"]
        .clip(0, 1)
    )

    # ------------------------------------------------------------
    # Merge with original inference attributes
    # ------------------------------------------------------------
    if (
        not base_df.empty
        and "project_id" in base_df.columns
        and "quarter" in base_df.columns
        and "project_id" in predictions_df.columns
        and "quarter" in predictions_df.columns
    ):
        keep = [
            c for c in [
                "project_id",
                "quarter",
                "region_final",
                "sector_extracted",
                "physical_progress_pct",
                "original_cost_crore",
                "land_required_ha",
                "land_acquired_ha",
                "land_possession_ha",
                "land_acquisition_pct",
                "land_gap_ha_calc",
                "label_confidence_tier",
            ]
            if c in base_df.columns
        ]

        base_small = (
            base_df[keep]
            .drop_duplicates(
                subset=["project_id", "quarter"],
                keep="last"
            )
        )

        merged = predictions_df.merge(
            base_small,
            on=["project_id", "quarter"],
            how="left",
            suffixes=("", "_base"),
        )
    else:
        merged = predictions_df.copy()

    # ------------------------------------------------------------
    # Helper to safely choose values
    # ------------------------------------------------------------
    def get_value(row, *names, default=None):
        for name in names:
            if name in row.index:
                value = row[name]

                if value is not None and not pd.isna(value):
                    return value

        return default

    # ------------------------------------------------------------
    # Build frontend rows
    # ------------------------------------------------------------
    projects = []

    for _, row in merged.iterrows():

        probability = float(
            get_value(
                row,
                "predicted_delay_probability",
                default=0
            )
        )

        risk_value = get_value(
            row,
            "risk_tier",
            "risk_category",
            default="Low"
        )

        risk_text = str(risk_value).strip().lower()

        if "high" in risk_text:
            risk_category = "High"
        elif "medium" in risk_text:
            risk_category = "Medium"
        else:
            risk_category = "Low"

        drivers_raw = get_value(
            row,
            "top_delay_drivers",
            "top_contributing_drivers",
            default=""
        )

        if isinstance(drivers_raw, str):
            drivers = [
                x.strip()
                for x in drivers_raw.split(";")
                if x.strip()
            ]
        elif isinstance(drivers_raw, list):
            drivers = drivers_raw
        else:
            drivers = []

        projects.append({
            "project_id": str(
                get_value(row, "project_id", default="")
            ),
            "quarter": str(
                get_value(row, "quarter", default="")
            ),
            "region_final": str(
                get_value(
                    row,
                    "region_final",
                    "region",
                    default="Unknown"
                )
            ),
            "sector_extracted": str(
                get_value(
                    row,
                    "sector_extracted",
                    "sector",
                    default="Unknown"
                )
            ),
            "predicted_delay_probability": probability,
            "predicted_delay_pct": probability * 100,

            "risk_category": risk_category,

            "label_confidence_tier": str(
                get_value(
                    row,
                    "label_confidence_tier",
                    "confidence_tier",
                    default="unknown_insufficient_evidence"
                )
            ),

            "original_cost_crore": float(
                pd.to_numeric(
                    get_value(row, "original_cost_crore", default=0),
                    errors="coerce"
                ) or 0
            ),

            "physical_progress_pct": float(
                pd.to_numeric(
                    get_value(row, "physical_progress_pct", default=0),
                    errors="coerce"
                ) or 0
            ),

            "land_acquisition_pct": float(
                pd.to_numeric(
                    get_value(row, "land_acquisition_pct", default=0),
                    errors="coerce"
                ) or 0
            ),

            "land_gap_ha_calc": float(
                pd.to_numeric(
                    get_value(row, "land_gap_ha_calc", default=0),
                    errors="coerce"
                ) or 0
            ),

            "top_contributing_drivers": drivers,
        })

    # ------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------
    if region != "All":
        projects = [
            p for p in projects
            if p["region_final"] == region
        ]

    if sector != "All":
        projects = [
            p for p in projects
            if p["sector_extracted"] == sector
        ]

    if risk != "All":
        projects = [
            p for p in projects
            if p["risk_category"] == risk
        ]

    if confidence_tier != "All":
        projects = [
            p for p in projects
            if p["label_confidence_tier"] == confidence_tier
        ]

    if search:
        q = search.lower()
        projects = [
            p for p in projects
            if q in p["project_id"].lower()
        ]

    # ------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------
    allowed_sort = {
        "project_id",
        "predicted_delay_probability",
        "physical_progress_pct",
        "original_cost_crore",
        "region_final",
        "sector_extracted",
    }

    if sort_by not in allowed_sort:
        sort_by = "predicted_delay_probability"

    reverse = sort_order.lower() != "asc"

    projects.sort(
        key=lambda p: p.get(sort_by, 0),
        reverse=reverse
    )

    # ------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------
    total_count = len(projects)

    total_pages = max(
        1,
        (total_count + page_size - 1) // page_size
    )

    start = (page - 1) * page_size
    end = start + page_size

    return {
        "projects": projects[start:end],
        "total_count": total_count,
        "total_pages": total_pages,
        "page": page,
        "page_size": page_size,
    }

# Keep the original endpoint working too
@app.get("/projects")
def get_projects():
    return query_projects(
        page=1,
        page_size=10000,
        sort_by="predicted_delay_probability",
        sort_order="desc",
    )

@app.get("/api/projects")
def get_projects_api(
    region: str = "All",
    sector: str = "All",
    risk: str = "All",
    confidence_tier: str = "All",
    search: str = "",
    page: int = 1,
    page_size: int = 25,
    sort_by: str = "predicted_delay_probability",
    sort_order: str = "desc",
):
    return query_projects(
        region=region,
        sector=sector,
        risk=risk,
        confidence_tier=confidence_tier,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


# -------------------------------------------------------------------
# PROJECT EXPLANATION
# -------------------------------------------------------------------

@app.get("/api/projects/{project_id}")
def get_project_detail(project_id: str):
    # ------------------------------------------------------------
    # Load prediction
    # ------------------------------------------------------------
    if not os.path.exists(PREDICTIONS_FILE):
        raise RuntimeError(
            f"Prediction file not found: {PREDICTIONS_FILE}"
        )

    predictions_df = pd.read_csv(PREDICTIONS_FILE)

    prediction_matches = predictions_df[
        predictions_df["project_id"].astype(str) == str(project_id)
    ]

    if prediction_matches.empty:
        return {
            "error": "Project not found",
            "project_id": project_id,
        }

    prediction_row = prediction_matches.iloc[0].to_dict()

    # ------------------------------------------------------------
    # Load original inference data
    # ------------------------------------------------------------
    base_row = {}

    if os.path.exists(INFERENCE_FILE):
        base_df = pd.read_csv(INFERENCE_FILE)

        matches = base_df[
            base_df["project_id"].astype(str) == str(project_id)
        ]

        # Prefer matching quarter when available
        if (
            not matches.empty
            and "quarter" in matches.columns
            and "quarter" in prediction_row
        ):
            qmatch = matches[
                matches["quarter"].astype(str)
                == str(prediction_row["quarter"])
            ]

            if not qmatch.empty:
                matches = qmatch

        if not matches.empty:
            base_row = matches.iloc[0].to_dict()

    # ------------------------------------------------------------
    # Probability
    # ------------------------------------------------------------
    probability = safe_float(
        prediction_row.get(
            "predicted_delay_probability",
            0
        )
    )

    if probability > 1:
        probability /= 100

    # ------------------------------------------------------------
    # Risk
    # ------------------------------------------------------------
    risk = str(
        prediction_row.get(
            "risk_tier",
            "Low"
        )
    )

    # ------------------------------------------------------------
    # Drivers
    # ------------------------------------------------------------
    drivers_raw = prediction_row.get(
        "top_delay_drivers",
        ""
    )

    drivers = [
        x.strip()
        for x in str(drivers_raw).split(";")
        if x.strip()
    ]

    # ------------------------------------------------------------
    # Recommended actions
    # ------------------------------------------------------------
    actions_raw = prediction_row.get(
        "recommended_actions",
        ""
    )

    actions = [
        x.strip()
        for x in str(actions_raw).split(";")
        if x.strip()
    ]

    # ============================================================
    # REAL SHAP EXPLANATION
    # ============================================================

    shap_explanation = []

    try:
        bundle = joblib.load(MODEL_FILE)

        model = bundle["model"]
        train_cols = bundle["columns"]
        model_name = bundle.get("model_name", "")
        needs_scaling = bundle.get("needs_scaling", False)
        scaler = bundle.get("scaler")

        # Rebuild the model input exactly like explain_and_score.py
        ml_row = pd.DataFrame([base_row])

        DROP_COLS = [
            "target_is_delayed",
            "label_confidence_tier",
            "is_unlabeled",
            "ml_split_v2",
            "project_id",
            "quarter",
            "time_overrun_months",
            "time_overrun_months_was_missing",
        ]

        CAT_COLS = [
            "region_final",
            "sector_extracted",
        ]

        ml_row = ml_row.drop(
            columns=[
                c for c in DROP_COLS
                if c in ml_row.columns
            ],
            errors="ignore",
        )

        ml_row = pd.get_dummies(
            ml_row,
            columns=[
                c for c in CAT_COLS
                if c in ml_row.columns
            ],
            dummy_na=True,
        )

        ml_row = ml_row.reindex(
            columns=train_cols,
            fill_value=0,
        )

        # SHAP needs the exact model input
        if needs_scaling and scaler is not None:
            X_shap = scaler.transform(ml_row)
        else:
            X_shap = ml_row

        import shap

        if needs_scaling:
            explainer = shap.LinearExplainer(
                model,
                X_shap,
            )
            shap_values = explainer.shap_values(X_shap)
        else:
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_shap)

            if isinstance(shap_values, list):
                shap_values = shap_values[1]

        row_shap = np.asarray(shap_values)[0]

        feature_names = np.asarray(train_cols)
        feature_values = np.asarray(X_shap)[0]

        # Highest absolute local contributions
        top_indices = np.argsort(
            np.abs(row_shap)
        )[::-1][:8]

        for idx in top_indices:

            shap_value = float(row_shap[idx])

            if abs(shap_value) < 1e-8:
                continue

            value = float(feature_values[idx])

            shap_explanation.append({
                "raw_feature": str(feature_names[idx]),
                "friendly_name": str(feature_names[idx]),
                "shap_value": shap_value,
                "impact": (
                    "increases_risk"
                    if shap_value > 0
                    else "reduces_risk"
                ),
                "feature_value": value,
            })

    except Exception as e:
        print(
            f"SHAP detail generation failed for "
            f"{project_id}: {e}"
        )

        # Do not crash the project page.
        # Fall back to the already-generated top drivers.
        shap_explanation = [
            {
                "raw_feature": driver,
                "friendly_name": driver,
                "shap_value": 0.0,
                "impact": "increases_risk",
                "feature_value": 0.0,
            }
            for driver in drivers[:3]
        ]

    # ============================================================
    # COMPLETE PROJECT DETAIL RESPONSE
    # ============================================================

    def val(name, default=0):
        value = base_row.get(name)

        if value is None or pd.isna(value):
            value = prediction_row.get(name, default)

        return value

    raw_narrative = str(
        val(
            "narrative_text",
            val("raw_narrative", "")
        )
    )

    return {
        "project_id": str(project_id),

        "quarter": str(
            prediction_row.get(
                "quarter",
                base_row.get("quarter", "")
            )
        ),

        "predicted_delay_probability": probability,

        "predicted_delay_pct": probability * 100,

        "risk_category": risk,

        "label_confidence_tier": str(
            val(
                "label_confidence_tier",
                "unknown_insufficient_evidence"
            )
        ),

        "feature_snapshot": {

            "identity": {
                "project_id": str(project_id),
                "quarter": str(
                    val("quarter", "")
                ),
                "region": str(
                    val("region_final", "Unknown")
                ),
                "sector": str(
                    val("sector_extracted", "Unknown")
                ),
                "state_freq_encoded": safe_float(
                    val("state_freq_encoded", 0)
                ),
                "label_confidence_tier": str(
                    val(
                        "label_confidence_tier",
                        "unknown_insufficient_evidence"
                    )
                ),
            },

            "progress_and_cost": {
                "original_cost_crore": safe_float(
                    val("original_cost_crore", 0)
                ),
                "anticipated_cost_crore": safe_float(
                    val(
                        "anticipated_cost_crore_extracted",
                        0
                    )
                ),
                "cost_overrun_pct": safe_float(
                    val(
                        "cost_overrun_pct_calc_clean",
                        0
                    )
                ),
                "physical_progress_pct": safe_float(
                    val("physical_progress_pct", 0)
                ),
                "project_age_months": safe_float(
                    val(
                        "project_age_months_at_report",
                        0
                    )
                ),
            },

            "land_acquisition_status": {
                "land_required_ha": safe_float(
                    val("land_required_ha", 0)
                ),
                "land_acquired_ha": safe_float(
                    val("land_acquired_ha", 0)
                ),
                "land_possession_ha": safe_float(
                    val("land_possession_ha", 0)
                ),
                "land_gap_ha": safe_float(
                    val("land_gap_ha_calc", 0)
                ),
                "land_acquisition_pct": safe_float(
                    val("land_acquisition_pct", 0)
                ),
                "land_possession_pct": safe_float(
                    val("land_possession_pct_calc", 0)
                ),
                "land_progress_ratio": safe_float(
                    val(
                        "land_acquisition_progress_ratio",
                        0
                    )
                ),
                "has_land_component": bool(
                    val(
                        "has_land_component_v2",
                        False
                    )
                ),
            },

            "bottleneck_indicators": {
                "legal_dispute_flag": bool(
                    val("legal_dispute", False)
                ),
                "compensation_mentioned": bool(
                    val(
                        "compensation_mentioned",
                        False
                    )
                ),
                "forest_or_clearance_issue": bool(
                    val(
                        "forest_land_or_clearance_issue",
                        False
                    )
                ),
                "rr_issue_flag": bool(
                    val("rr_issue", False)
                ),
                "row_issue_flag": bool(
                    val("row_issue", False)
                ),
                "administrative_issue_flag": bool(
                    val(
                        "administrative_issue",
                        False
                    )
                ),
                "num_compound_issues": int(
                    safe_float(
                        val("num_issue_flags_v2", 0)
                    )
                ),
                "has_delay_reason_text": bool(
                    val(
                        "has_delay_reason_text",
                        False
                    )
                ),
            },
        },

        "shap_explanation": shap_explanation,

        "recommended_actions": actions,

        "narrative": {
            "raw_text": raw_narrative,
            "has_narrative": bool(
                raw_narrative.strip()
            ),
            "active_keyword_flags": [],
            "character_length": len(raw_narrative),
        },

        "audit_record": {
            "time_overrun_months": safe_float(
                val("time_overrun_months", 0)
            ),
            "time_overrun_months_was_missing": bool(
                val(
                    "time_overrun_months_was_missing",
                    False
                )
            ),
            "ml_split_status": str(
                val("ml_split_v2", "")
            ),
            "governance_note": (
                "Local TreeSHAP explanation generated "
                "from the frozen production model and "
                "the project's inference features."
            ),
        },
    }


# Preserve the old endpoint too
@app.get("/projects/{project_id}/explanation")
def get_project_explanation(project_id: str):
    return get_project_detail(project_id)

# -------------------------------------------------------------------
# ALERTS
# -------------------------------------------------------------------

def query_alerts(min_probability=0.0):
    columns = get_table_columns("alerts")

    probability_column = first_existing(
        columns,
        [
            "predicted_delay_probability",
            "delay_probability",
            "probability",
        ]
    )

    where_sql = ""
    params = []

    if probability_column and min_probability > 0:
        where_sql = f"WHERE {probability_column} >= ?"
        params.append(min_probability)

    conn = get_connection()

    try:
        order_clause = "rowid DESC"

        if "quarter" in columns and "severity" in columns:
            order_clause = """
                CASE severity
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    ELSE 4
                END,
                quarter DESC
            """

        rows = conn.execute(
            f"""
            SELECT *
            FROM alerts
            {where_sql}
            ORDER BY {order_clause}
            """,
            params,
        ).fetchall()

        alerts = [dict(row) for row in rows]

        return {
            "alert_count": len(alerts),
            "alerts": alerts,
        }

    finally:
        conn.close()


@app.get("/api/alerts")
def get_alerts_api(
    min_probability: float = Query(0.0)
):
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT
                a.*,
                ps.predicted_delay_probability AS score_probability,
                ps.top_delay_drivers AS score_drivers,
                ps.recommended_actions AS score_actions
            FROM alerts a
            LEFT JOIN project_scores ps
                ON a.project_id = ps.project_id
            ORDER BY a.rowid DESC
            """
        ).fetchall()

        alerts = []

        for row in rows:
            r = dict(row)

            # Get probability from project_scores
            probability = safe_float(
                r.get("score_probability")
            )

            if probability > 1:
                probability_fraction = probability / 100
            else:
                probability_fraction = probability

            if probability_fraction < min_probability:
                continue

            # Region
            region = (
                r.get("region")
                or r.get("region_final")
                or ""
            )

            # Sector
            sector = (
                r.get("sector")
                or r.get("sector_extracted")
                or ""
            )

            # Driver
            primary_driver = (
                r.get("primary_driver")
                or r.get("top_delay_driver")
                or r.get("top_delay_drivers")
                or r.get("score_drivers")
                or r.get("driver")
                or ""
            )

            # Severity
            severity_raw = (
                r.get("severity")
                or r.get("alert_type")
                or "HIGH"
            )

            severity_text = str(severity_raw).upper()

            if "CRITICAL" in severity_text:
                severity = "CRITICAL"
            else:
                severity = "HIGH"

            alerts.append({
                "alert_id": str(
                    r.get("alert_id")
                    or r.get("id")
                    or f"ALERT-{len(alerts)+1}"
                ),
                "project_id": str(
                    r.get("project_id") or ""
                ),
                "quarter": str(
                    r.get("quarter") or ""
                ),
                "sector": sector,
                "region": region,
                "predicted_delay_probability": probability_fraction,
                "predicted_delay_pct": probability_fraction * 100,
                "severity": severity,
                "primary_driver": str(primary_driver),
                "label_confidence_tier": str(
                    r.get("label_confidence_tier") or ""
                ),
                "timestamp": str(
                    r.get("timestamp")
                    or r.get("created_at")
                    or r.get("run_timestamp")
                    or ""
                ),
                "recommended_actions": str(
                    r.get("recommended_actions")
                    or r.get("score_actions")
                    or ""
                ),
            })

        return {
            "alert_count": len(alerts),
            "alerts": alerts,
        }

    finally:
        conn.close()

# -------------------------------------------------------------------
# EXECUTIVE OVERVIEW
# -------------------------------------------------------------------

@app.get("/api/overview")
def get_overview():
    columns = get_table_columns("project_scores")

    probability_col = first_existing(
        columns,
        ["predicted_delay_probability"]
    )

    risk_col = first_existing(
        columns,
        ["risk_tier"]
    )

    region_col = first_existing(
        columns,
        ["region_final", "region"]
    )

    sector_col = first_existing(
        columns,
        ["sector_extracted", "sector"]
    )

    quarter_col = first_existing(
        columns,
        ["quarter"]
    )

    conn = get_connection()

    try:
        total_projects = conn.execute(
            "SELECT COUNT(*) FROM project_scores"
        ).fetchone()[0]

        high_risk = 0
        medium_risk = 0
        low_risk = 0

        if risk_col:
            risk_rows = conn.execute(
                f"""
                SELECT {risk_col} AS risk, COUNT(*) AS cnt
                FROM project_scores
                GROUP BY {risk_col}
                """
            ).fetchall()

            for row in risk_rows:
                risk_value = str(row["risk"] or "").lower()

                if "high" in risk_value:
                    high_risk += row["cnt"]
                elif "medium" in risk_value:
                    medium_risk += row["cnt"]
                elif "low" in risk_value:
                    low_risk += row["cnt"]

        # -------------------------------
        # Region summary
        # -------------------------------

        by_region = []

        if region_col:
            region_rows = conn.execute(
                f"""
                SELECT
                    {region_col} AS region,
                    COUNT(*) AS total
                FROM project_scores
                GROUP BY {region_col}
                ORDER BY total DESC
                """
            ).fetchall()

            for row in region_rows:
                region_name = row["region"] or "Unknown"

                region_result = {
                    "region": region_name,
                    "total": row["total"],
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                }

                if risk_col:
                    risk_rows = conn.execute(
                        f"""
                        SELECT {risk_col} AS risk, COUNT(*) AS cnt
                        FROM project_scores
                        WHERE {region_col} = ?
                        GROUP BY {risk_col}
                        """,
                        (row["region"],),
                    ).fetchall()

                    for rr in risk_rows:
                        rv = str(rr["risk"] or "").lower()

                        if "high" in rv:
                            region_result["high"] += rr["cnt"]
                        elif "medium" in rv:
                            region_result["medium"] += rr["cnt"]
                        elif "low" in rv:
                            region_result["low"] += rr["cnt"]

                by_region.append(region_result)

        # -------------------------------
        # Sector summary
        # -------------------------------

        top_10_sectors = []
        all_sectors = []

        if sector_col:
            sector_rows = conn.execute(
                f"""
                SELECT
                    {sector_col} AS sector,
                    COUNT(*) AS total
                FROM project_scores
                GROUP BY {sector_col}
                ORDER BY total DESC
                """
            ).fetchall()

            all_sectors = sorted(
                [
                    row["sector"] or "Unknown"
                    for row in sector_rows
                ]
            )

            for row in sector_rows[:10]:
                avg_probability = 0.0

                if probability_col:
                    avg_probability = safe_float(
                        conn.execute(
                            f"""
                            SELECT AVG({probability_col})
                            FROM project_scores
                            WHERE {sector_col} = ?
                            """,
                            (row["sector"],),
                        ).fetchone()[0]
                    )

                top_10_sectors.append({
                    "sector": row["sector"] or "Unknown",
                    "total": row["total"],
                    "avg_probability": avg_probability,
                })

        # -------------------------------
        # Quarterly trend
        # -------------------------------

        quarterly_trend = []

        if quarter_col:
            quarter_rows = conn.execute(
                f"""
                SELECT
                    {quarter_col} AS quarter,
                    COUNT(*) AS total
                    {f', AVG({probability_col}) AS avg_probability' if probability_col else ''}
                FROM project_scores
                GROUP BY {quarter_col}
                ORDER BY {quarter_col}
                """
            ).fetchall()

            for row in quarter_rows:
                item = {
                    "quarter": row["quarter"] or "Unknown",
                    "total": row["total"],
                    "avg_probability": safe_float(
                        row["avg_probability"]
                    ) if probability_col else 0.0,
                }

                quarterly_trend.append(item)

        avg_probability = 0.0

        if probability_col:
            avg_probability = safe_float(
                conn.execute(
                    f"""
                    SELECT AVG({probability_col})
                    FROM project_scores
                    """
                ).fetchone()[0]
            )

        return {
            "total_projects": total_projects,
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
            "avg_delay_probability": avg_probability,
            "by_region": by_region,
            "top_10_sectors": top_10_sectors,
            "all_sectors": all_sectors,
            "quarterly_trend": quarterly_trend,
        }

    finally:
        conn.close()


# -------------------------------------------------------------------
# MODEL GOVERNANCE / METADATA
# -------------------------------------------------------------------

@app.get("/api/model/metadata")
def get_model_metadata():
    return {
        "model_type": "LightGBM + TreeSHAP",
        "problem_statement": "Predictive Analytics System for Early Detection of Land Acquisition Delays",
        "target": "target_is_delayed",
        "split_methodology": "Train / validation / test split using ml_split_v2",
        "excluded_features": [
            "target_is_delayed",
            "label_confidence_tier",
            "is_unlabeled",
            "ml_split_v2",
            "project_id",
            "quarter",
            "time_overrun_months",
            "time_overrun_months_was_missing",
        ],
        "total_engineered_features": 0,
        "feature_names_sample": [
            "project_age_months_at_report",
            "original_cost_crore",
            "physical_progress_pct",
            "state_freq_encoded",
            "anticipated_cost_crore",
            "cost_overrun_pct_calc_clean",
            "land_acquisition_pct",
            "land_gap_ha_calc",
            "covid_period",
        ],
        "test_set_evaluation": {
            "test_samples": 6099,
            "precision": 0.9172,
            "recall": 0.8205,
            "f1_score": 0.8662,
            "roc_auc": 0.8872,
            "pr_auc": 0.9513,
            "confusion_matrix": {
                "labels": [
                    "Not Delayed",
                    "Delayed"
                ],
                "matrix": [
                    [1269, 333],
                    [807, 3690]
                ],
                "true_negatives": 1269,
                "false_positives": 333,
                "false_negatives": 807,
                "true_positives": 3690,
            },
        },
        "raw_test_metrics_log": (
            "LightGBM selected by validation PR-AUC. "
            "Final test F1=0.8662, Precision=0.9172, "
            "Recall=0.8205, ROC-AUC=0.8872, PR-AUC=0.9513."
        ),
        "retraining_instructions": (
            "Retrain quarterly using the approved training pipeline. "
            "Compare the candidate model against the current production "
            "model before promotion."
        ),
    }


# -------------------------------------------------------------------
# REGIONAL ANALYTICS
# -------------------------------------------------------------------

@app.get("/api/regional")
def get_regional():
    columns = get_table_columns("project_scores")

    region_col = first_existing(
        columns,
        ["region_final", "region"]
    )

    sector_col = first_existing(
        columns,
        ["sector_extracted", "sector"]
    )

    probability_col = first_existing(
        columns,
        ["predicted_delay_probability"]
    )
    risk_col = first_existing(
    columns,
    ["risk_tier", "risk_category"]
    )

    quarter_col = first_existing(
        columns,
        ["quarter"]
    )

    conn = get_connection()

    try:
        regions = []
        sectors = []

        if region_col:
            rows = conn.execute(
                f"""
                SELECT DISTINCT {region_col} AS region
                FROM project_scores
                WHERE {region_col} IS NOT NULL
                ORDER BY {region_col}
                """
            ).fetchall()

            regions = [
                row["region"] or "Unknown"
                for row in rows
            ]

        if sector_col:
            rows = conn.execute(
                f"""
                SELECT DISTINCT {sector_col} AS sector
                FROM project_scores
                WHERE {sector_col} IS NOT NULL
                ORDER BY {sector_col}
                """
            ).fetchall()

            sectors = [
                row["sector"] or "Unknown"
                for row in rows
            ]

        # -----------------------------------------
        # Sector x region heatmap matrix
        # Frontend expects:
        # [
        #   {
        #       "sector": "...",
        #       "regions": {
        #           "Central": {
        #               "count": ...,
        #               "avg_prob": ...,
        #               "delay_rate": ...
        #           }
        #       }
        #   }
        # ]
        # -----------------------------------------

        heatmap_matrix = []

        if region_col and sector_col:
            rows = conn.execute(
                f"""
                SELECT
                    {sector_col} AS sector,
                    {region_col} AS region,
                    COUNT(*) AS project_count,
                    {
                        f"AVG({probability_col})"
                        if probability_col
                        else "0"
                    } AS avg_probability
                FROM project_scores
                GROUP BY {sector_col}, {region_col}
                ORDER BY {sector_col}, {region_col}
                """
            ).fetchall()

            grouped = {}

            for row in rows:
                sector_name = row["sector"] or "Unknown"
                region_name = row["region"] or "Unknown"

                if sector_name not in grouped:
                    grouped[sector_name] = {}

                count = int(row["project_count"] or 0)
                avg_prob = safe_float(row["avg_probability"])

                grouped[sector_name][region_name] = {
                    "count": count,
                    "avg_prob": avg_prob,
                    "delay_rate": avg_prob,
                }

            for sector_name, region_data in grouped.items():
                heatmap_matrix.append({
                    "sector": sector_name,
                    "regions": region_data,
                })

        # -----------------------------------------
        # Regional map bubbles
        #
        # These are regional monitoring nodes, not
        # fabricated project-level coordinates.
        # -----------------------------------------

        map_bubbles = []

        REGION_COORDS = {
            "North": (28.6139, 77.2090),
            "South": (13.0827, 80.2707),
            "East": (22.5726, 88.3639),
            "West": (19.0760, 72.8777),
            "Central": (23.2599, 77.4126),
            "Northeast": (26.1445, 91.7362),
            "Multi-State/National": (23.0000, 80.0000),
            "Unknown": (22.0000, 79.0000),
        }

        if region_col:
            rows = conn.execute(
                f"""
                SELECT
                    {region_col} AS region,
                    COUNT(*) AS project_count
                    {
                        f", AVG({probability_col}) AS avg_probability"
                        if probability_col
                        else ""
                    }
                FROM project_scores
                GROUP BY {region_col}
                ORDER BY project_count DESC
                """
            ).fetchall()

            for row in rows:
                region_name = row["region"] or "Unknown"

                # Risk counts for this region
                high_risk_count = 0

                if risk_col:
                    high_row = conn.execute(
                        f"""
                        SELECT COUNT(*)
                        FROM project_scores
                        WHERE {region_col} = ?
                          AND LOWER(COALESCE({risk_col}, '')) LIKE '%high%'
                        """,
                        (row["region"],),
                    ).fetchone()

                    high_risk_count = high_row[0] if high_row else 0

                total_projects = row["project_count"]

                high_risk_pct = (
                    (high_risk_count / total_projects) * 100
                    if total_projects > 0
                    else 0.0
                )

                avg_probability = (
                    safe_float(row["avg_probability"])
                    if probability_col
                    else 0.0
                )

                lat, lng = REGION_COORDS.get(
                    region_name,
                    REGION_COORDS["Unknown"]
                )

                map_bubbles.append({
                    "region": region_name,
                    "lat": lat,
                    "lng": lng,
                    "total_projects": total_projects,
                    "high_risk_count": high_risk_count,
                    "high_risk_pct": high_risk_pct,
                    "avg_delay_probability": avg_probability,
                    "top_sectors": {},
                })

        # -----------------------------------------
        # Regional quarterly timeline
        # -----------------------------------------


        timeline = []

        # -----------------------------------------
        # Load inference data and model predictions
        # -----------------------------------------

        base_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "infra_projects_inference_unlabeled.csv"
        )

        predictions_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "model_output",
            "inference_predictions_explained.csv"
        )

        base_df = pd.read_csv(base_path)
        predictions_df = pd.read_csv(predictions_path)

        # Keep only the fields required for the timeline
        base_df = base_df[
            [
                "project_id",
                "quarter",
                "physical_progress_pct",
                "land_acquisition_pct",
            ]
        ].copy()

        predictions_df = predictions_df[
            [
                "project_id",
                "quarter",
                "risk_tier",
            ]
        ].copy()

        # Join model risk classification to the actual
        # inference records
        timeline_df = base_df.merge(
            predictions_df,
            on=["project_id", "quarter"],
            how="inner"
        )

                # Clean numerical columns
        timeline_df["physical_progress_pct"] = pd.to_numeric(
            timeline_df["physical_progress_pct"],
            errors="coerce"
        )

        timeline_df["land_acquisition_pct"] = pd.to_numeric(
            timeline_df["land_acquisition_pct"],
            errors="coerce"
        )

        timeline_df = timeline_df.dropna(
            subset=["quarter"]
        )

        # Normalize risk labels
        timeline_df["risk_tier"] = (
            timeline_df["risk_tier"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        # -----------------------------------------
        # Normalize quarter labels and sort
        # chronologically
        # -----------------------------------------

        import re

        def normalize_quarter(value):
            if value is None or pd.isna(value):
                return None

            text = str(value).strip().upper()

            # Convert separators like:
            # Q2/2014 -> Q2-2014
            # Q2 2014 -> Q2-2014
            text = re.sub(r"[/_\s]+", "-", text)

            # Already in correct form: Q2-2014-15
            match = re.fullmatch(
                r"Q([1-4])-(\d{4})-(\d{2})",
                text
            )

            if match:
                quarter = int(match.group(1))
                start_year = int(match.group(2))
                end_year = int(match.group(3))

                return (
                    f"Q{quarter}-"
                    f"{start_year}-"
                    f"{end_year:02d}"
                )

            # Short form: Q2-2014
            # Interpret it as FY 2014-15
            match = re.fullmatch(
                r"Q([1-4])-(\d{4})",
                text
            )

            if match:
                quarter = int(match.group(1))
                start_year = int(match.group(2))
                end_year = (start_year + 1) % 100

                return (
                    f"Q{quarter}-"
                    f"{start_year}-"
                    f"{end_year:02d}"
                )

            return text

        timeline_df["quarter"] = (
            timeline_df["quarter"]
            .apply(normalize_quarter)
        )

        # Create a real chronological sorting key.
        # Example:
        # Q1-2019-20 -> 2019*4 + 0
        # Q2-2019-20 -> 2019*4 + 1
        # Q4-2019-20 -> 2019*4 + 3
        def quarter_sort_key(value):
            if value is None:
                return float("inf")

            match = re.fullmatch(
                r"Q([1-4])-(\d{4})-\d{2}",
                str(value)
            )

            if not match:
                return float("inf")

            quarter = int(match.group(1))
            year = int(match.group(2))

            return year * 4 + (quarter - 1)

        timeline_df["quarter_sort"] = (
            timeline_df["quarter"]
            .apply(quarter_sort_key)
        )

        timeline_df = timeline_df.sort_values(
            "quarter_sort"
        )

        # Build chart data quarter by quarter
        for quarter, group in timeline_df.groupby(
            "quarter",
            sort=False
        ):

            high_risk = group[
                group["risk_tier"].str.contains(
                    "high",
                    na=False
                )
            ]

            ontrack = group[
                ~group["risk_tier"].str.contains(
                    "high",
                    na=False
                )
            ]

                # Percentage of projects with fully acquired land
                # Treat >= 99.999% as fully acquired to avoid
                # floating-point precision issues.
            high_risk_land_complete_pct = (
                    (
                        high_risk["land_acquisition_pct"] >= 99.999
                    ).mean() * 100
                    if len(high_risk) > 0
                    else 0.0
                )

            ontrack_land_complete_pct = (
                    (
                        ontrack["land_acquisition_pct"] >= 99.999
                    ).mean() * 100
                    if len(ontrack) > 0
                    else 0.0
                )

            timeline.append({
                    "quarter": str(quarter),

                    "high_risk_physical_progress": safe_float(
                        high_risk["physical_progress_pct"].mean()
                    ),

                    "ontrack_physical_progress": safe_float(
                        ontrack["physical_progress_pct"].mean()
                    ),

                    "high_risk_land_complete_pct": safe_float(
                        high_risk_land_complete_pct
                    ),

                    "ontrack_land_complete_pct": safe_float(
                        ontrack_land_complete_pct
                    ),
                })



        

        return {
            "regions_list": regions,
            "map_bubbles": map_bubbles,
            "top_sectors": sectors[:10],
            "heatmap_matrix": heatmap_matrix,
            "timeline": timeline,
            "gis_governance_notice": (
                "Regional visualization uses aggregated region-level "
                "statistics from the project register. No project "
                "coordinates are fabricated where latitude/longitude "
                "data are unavailable."
            ),
        }

    finally:
        conn.close()