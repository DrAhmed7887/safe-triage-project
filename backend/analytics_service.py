"""
Analytics Service - privacy-compliant aggregated reporting.
No per-patient PHI is returned by these endpoints.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query, FastAPI
from pydantic import BaseModel, Field
from google.cloud import bigquery
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

router = APIRouter(prefix="/analytics", tags=["Analytics"])

PROJECT_ID = os.getenv("PROJECT_ID", "safe-triage-ai")
DATASET_ID = os.getenv("DATASET_ID", "safe_triage_audit")
TRIAGE_TABLE = os.getenv("TRIAGE_TABLE", "triage_logs")
CONFIRMATION_TABLE = os.getenv("CONFIRMATION_TABLE", "triage_confirmations")
ACCESS_LOG_TABLE = os.getenv("ANALYTICS_ACCESS_TABLE", "analytics_access_log")
BQ_LOCATION = os.getenv("BQ_LOCATION", "me-west1")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "safe-triage-ai")

_bq_client: Optional[bigquery.Client] = None


def _table_ref(table_name: str) -> str:
    return f"{PROJECT_ID}.{DATASET_ID}.{table_name}"


def _get_bq_client() -> bigquery.Client:
    global _bq_client
    if _bq_client is None:
        try:
            _bq_client = bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"BigQuery unavailable: {exc}")
    return _bq_client


def ensure_analytics_tables() -> None:
    schema = [
        bigquery.SchemaField("access_id", "STRING"),
        bigquery.SchemaField("user_id", "STRING"),
        bigquery.SchemaField("user_role", "STRING"),
        bigquery.SchemaField("action", "STRING"),
        bigquery.SchemaField("timestamp", "TIMESTAMP"),
        bigquery.SchemaField("metadata", "STRING"),
    ]
    table_id = _table_ref(ACCESS_LOG_TABLE)
    client = _get_bq_client()
    try:
        client.get_table(table_id)
    except Exception:
        table = bigquery.Table(table_id, schema=schema)
        client.create_table(table)


def _verify_firebase_token(authorization: str) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        request = google_requests.Request()
        claims = id_token.verify_firebase_token(token, request, audience=FIREBASE_PROJECT_ID)
        if not claims:
            raise HTTPException(status_code=401, detail="Invalid Firebase token")
        return claims
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def _normalize_role(role_value: Optional[str]) -> str:
    role = (role_value or "").strip().lower()
    if role in {"supervisor", "admin"}:
        return "supervisor"
    if role in {"doctor", "physician"}:
        return "doctor"
    if role in {"nurse"}:
        return "nurse"
    return role


def require_supervisor_role(
    authorization: str = Header(default=None),
    x_user_role: Optional[str] = Header(default=None),
):
    claims = _verify_firebase_token(authorization)
    custom_claims = claims.get("custom_claims") if isinstance(claims.get("custom_claims"), dict) else {}
    token_role_raw = claims.get("role") or claims.get("triage_role") or custom_claims.get("role")
    token_role = _normalize_role(token_role_raw)
    header_role = _normalize_role(x_user_role)
    effective_role = header_role or token_role
    if effective_role != "supervisor":
        raise HTTPException(status_code=403, detail="Supervisor access required")
    return {
        "uid": claims.get("uid"),
        "email": claims.get("email"),
        "role": effective_role,
    }


class AccessLogRequest(BaseModel):
    action: str = Field(..., min_length=3)
    metadata: Optional[Dict[str, Any]] = None


def _run_scalar_query(query: str, params: List[bigquery.ScalarQueryParameter]) -> Dict[str, Any]:
    client = _get_bq_client()
    job = client.query(
        query,
        job_config=bigquery.QueryJobConfig(query_parameters=params),
        location=BQ_LOCATION,
    )
    rows = list(job.result())
    return dict(rows[0]) if rows else {}


def _run_rows_query(query: str, params: List[bigquery.ScalarQueryParameter]) -> List[Dict[str, Any]]:
    client = _get_bq_client()
    job = client.query(
        query,
        job_config=bigquery.QueryJobConfig(query_parameters=params),
        location=BQ_LOCATION,
    )
    return [dict(row) for row in job.result()]


@router.get("/dashboard/summary")
def get_dashboard_summary(
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    user: Dict[str, Any] = Depends(require_supervisor_role),
):
    try:
        end_dt = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()
        start_dt = datetime.fromisoformat(start_date) if start_date else (end_dt - timedelta(days=1))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO-8601.")

    params = [
        bigquery.ScalarQueryParameter("start", "TIMESTAMP", start_dt),
        bigquery.ScalarQueryParameter("end", "TIMESTAMP", end_dt),
    ]

    total_cases = _run_scalar_query(
        f"""
        SELECT COUNT(*) AS count
        FROM `{_table_ref(TRIAGE_TABLE)}`
        WHERE timestamp BETWEEN @start AND @end
        """,
        params,
    )

    esi_distribution = _run_rows_query(
        f"""
        SELECT
            final_esi AS esi_level,
            COUNT(*) AS count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS percentage
        FROM `{_table_ref(TRIAGE_TABLE)}`
        WHERE timestamp BETWEEN @start AND @end
        GROUP BY final_esi
        ORDER BY final_esi
        """,
        params,
    )

    news2_distribution = _run_rows_query(
        f"""
        SELECT
            CASE
                WHEN news2_score >= 7 THEN 'High (>=7)'
                WHEN news2_score >= 5 THEN 'Medium (5-6)'
                ELSE 'Low (0-4)'
            END AS risk_level,
            COUNT(*) AS count
        FROM `{_table_ref(TRIAGE_TABLE)}`
        WHERE timestamp BETWEEN @start AND @end
        GROUP BY risk_level
        """,
        params,
    )

    override_rate = _run_scalar_query(
        f"""
        SELECT
            COUNTIF(was_overridden = TRUE) AS overrides,
            COUNT(*) AS total,
            ROUND(SAFE_DIVIDE(COUNTIF(was_overridden = TRUE) * 100.0, COUNT(*)), 1) AS override_percentage
        FROM `{_table_ref(TRIAGE_TABLE)}`
        WHERE timestamp BETWEEN @start AND @end
        """,
        params,
    )

    under_triage = _run_scalar_query(
        f"""
        SELECT COUNT(*) AS incidents
        FROM `{_table_ref(TRIAGE_TABLE)}`
        WHERE timestamp BETWEEN @start AND @end
          AND final_esi > recommended_esi
        """,
        params,
    )

    avg_response_time = _run_scalar_query(
        f"""
        SELECT ROUND(AVG(response_time_seconds), 1) AS avg_seconds
        FROM `{_table_ref(CONFIRMATION_TABLE)}`
        WHERE timestamp BETWEEN @start AND @end
          AND response_time_seconds IS NOT NULL
        """,
        params,
    )

    hourly_volume = _run_rows_query(
        f"""
        SELECT EXTRACT(HOUR FROM timestamp) AS hour, COUNT(*) AS cases
        FROM `{_table_ref(TRIAGE_TABLE)}`
        WHERE timestamp BETWEEN @start AND @end
        GROUP BY hour
        ORDER BY hour
        """,
        params,
    )

    return {
        "period": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
        "statistics": {
            "total_cases": total_cases,
            "esi_distribution": esi_distribution,
            "news2_distribution": news2_distribution,
            "override_rate": override_rate,
            "under_triage": under_triage,
            "avg_response_time": avg_response_time,
            "hourly_volume": hourly_volume,
        },
        "privacy_notice": "Anonymized aggregate statistics only. No individual patient data included.",
        "accessed_by": user.get("uid"),
    }


@router.get("/dashboard/quality-metrics")
def get_quality_metrics(user: Dict[str, Any] = Depends(require_supervisor_role)):
    query = f"""
        SELECT
            ROUND(SAFE_DIVIDE(COUNTIF(final_esi > recommended_esi) * 100.0, COUNT(*)), 2) AS under_triage_rate,
            ROUND(SAFE_DIVIDE(COUNTIF(final_esi < recommended_esi) * 100.0, COUNT(*)), 2) AS over_triage_rate,
            ROUND(AVG(IFNULL(ai_confidence, 0)) * 100, 1) AS avg_confidence,
            ROUND(AVG(IFNULL(response_time_seconds, 0)), 1) AS avg_confirmation_seconds
        FROM `{_table_ref(TRIAGE_TABLE)}` AS t
        LEFT JOIN `{_table_ref(CONFIRMATION_TABLE)}` AS c
        ON t.patient_id = c.patient_id
        WHERE DATE(t.timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    """
    row = _run_scalar_query(query, [])
    under_triage = float(row.get("under_triage_rate") or 0)
    over_triage = float(row.get("over_triage_rate") or 0)
    confidence = float(row.get("avg_confidence") or 0)
    latency = float(row.get("avg_confirmation_seconds") or 0)

    return {
        "metrics": row,
        "thresholds": {
            "under_triage_rate": {"target": "<2%", "status": "ok" if under_triage < 2 else "warning"},
            "over_triage_rate": {"target": "<15%", "status": "ok" if over_triage < 15 else "warning"},
            "avg_confidence": {"target": ">=70%", "status": "ok" if confidence >= 70 else "warning"},
            "avg_confirmation_seconds": {"target": "<300s", "status": "ok" if latency < 300 else "warning"},
        },
        "period": "Last 30 days",
        "accessed_by": user.get("uid"),
    }


@router.post("/audit/log-access")
def log_dashboard_access(
    payload: AccessLogRequest,
    user: Dict[str, Any] = Depends(require_supervisor_role),
):
    row = {
        "access_id": str(uuid.uuid4()),
        "user_id": user.get("uid"),
        "user_role": user.get("role"),
        "action": payload.action,
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": str(payload.metadata or {}),
    }
    client = _get_bq_client()
    errors = client.insert_rows_json(_table_ref(ACCESS_LOG_TABLE), [row])
    if errors:
        raise HTTPException(status_code=500, detail=f"Failed to write access log: {errors}")
    return {"status": "logged"}


def register_analytics_service(app: FastAPI) -> None:
    try:
        ensure_analytics_tables()
    except Exception:
        # Service can still run; endpoints will return 503 if BQ remains unavailable.
        pass
    app.include_router(router)
