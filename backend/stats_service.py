"""
Triage Statistics Service
Provides HIPAA-compliant aggregate statistics (no PHI).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from google.cloud import bigquery

from audit_service import audit_service


def _as_dict(row: Any) -> Dict[str, Any]:
    return dict(row) if row is not None else {}


def _normalize_period(period: str) -> str:
    value = (period or "").strip().lower()
    if value in {"today", "week", "month"}:
        return value
    return "today"


def _start_datetime(period: str) -> datetime:
    now = datetime.utcnow()
    normalized = _normalize_period(period)
    if normalized == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if normalized == "week":
        return now - timedelta(days=7)
    return now - timedelta(days=30)


def _run_scalar_query(client: bigquery.Client, table_id: str, query: str, start_dt: datetime) -> Dict[str, Any]:
    job = client.query(
        query.format(table_id=table_id),
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_dt", "TIMESTAMP", start_dt),
            ]
        ),
    )
    rows = list(job.result())
    return _as_dict(rows[0]) if rows else {}


def _run_rows_query(client: bigquery.Client, table_id: str, query: str, start_dt: datetime) -> List[Dict[str, Any]]:
    job = client.query(
        query.format(table_id=table_id),
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_dt", "TIMESTAMP", start_dt),
            ]
        ),
    )
    return [_as_dict(row) for row in job.result()]


def _safe_harbor_esi_buckets(esi_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enforce minimum bucket size to reduce re-identification risk.
    Buckets with count < 5 are merged into "Other".
    """
    if not esi_rows:
        return []

    visible = []
    other_count = 0
    for row in esi_rows:
        count = int(row.get("count") or 0)
        if count < 5:
            other_count += count
            continue
        visible.append(
            {
                "esi_level": str(row.get("esi_level")),
                "count": count,
            }
        )

    if other_count > 0:
        visible.append({"esi_level": "Other", "count": other_count})

    total = sum(int(item["count"]) for item in visible) or 1
    for item in visible:
        item["percentage"] = round((int(item["count"]) * 100.0) / total, 1)

    # Keep numeric ESI levels ordered, then "Other".
    visible.sort(key=lambda item: 99 if item["esi_level"] == "Other" else int(item["esi_level"]))
    return visible


def get_triage_stats(period: str = "today") -> Dict[str, Any]:
    """
    Get aggregate triage statistics for today/week/month.
    Returns anonymized aggregate statistics only (HIPAA compliant).
    """
    client = audit_service.client
    if not client:
        return {
            "period": _normalize_period(period),
            "statistics": {},
            "error": "BigQuery not available",
            "hipaa_compliant": True,
            "phi_included": False,
        }

    start_dt = _start_datetime(period)
    now = datetime.utcnow()
    table_id = audit_service.table_id

    queries = {
        "total_cases": """
            SELECT COUNT(*) AS count
            FROM `{table_id}`
            WHERE timestamp >= @start_dt
        """,
        "esi_distribution": """
            SELECT
                CAST(final_esi AS STRING) AS esi_level,
                COUNT(*) AS count
            FROM `{table_id}`
            WHERE timestamp >= @start_dt
            GROUP BY final_esi
            ORDER BY final_esi
        """,
        "avg_news2": """
            SELECT ROUND(AVG(news2_score), 1) AS avg_score
            FROM `{table_id}`
            WHERE timestamp >= @start_dt
        """,
        "under_triage_count": """
            SELECT COUNT(*) AS count
            FROM `{table_id}`
            WHERE timestamp >= @start_dt
              AND final_esi > recommended_esi
        """,
        "override_rate": """
            SELECT
                COUNTIF(was_overridden = TRUE) AS override_count,
                COUNT(*) AS total,
                ROUND(SAFE_DIVIDE(COUNTIF(was_overridden = TRUE) * 100.0, COUNT(*)), 1) AS override_percentage
            FROM `{table_id}`
            WHERE timestamp >= @start_dt
        """,
        "critical_cases": """
            SELECT COUNT(*) AS count
            FROM `{table_id}`
            WHERE timestamp >= @start_dt
              AND final_esi <= 2
        """,
        "hourly_trend": """
            SELECT
                EXTRACT(HOUR FROM timestamp) AS hour,
                COUNT(*) AS cases
            FROM `{table_id}`
            WHERE timestamp >= @start_dt
            GROUP BY hour
            ORDER BY hour
        """,
    }

    results: Dict[str, Any] = {}

    for key, query in queries.items():
        try:
            if key in {"esi_distribution", "hourly_trend"}:
                rows = _run_rows_query(client, table_id, query, start_dt)
                if key == "esi_distribution":
                    rows = _safe_harbor_esi_buckets(rows)
                results[key] = rows
            else:
                results[key] = _run_scalar_query(client, table_id, query, start_dt)
        except Exception as exc:  # pragma: no cover - runtime failure path
            results[key] = {"error": str(exc)}

    # Response time is stored in confirmation table, not triage log.
    try:
        confirmation_query = """
            SELECT ROUND(AVG(response_time_seconds), 1) AS avg_seconds
            FROM `{table_id}`
            WHERE timestamp >= @start_dt
              AND response_time_seconds IS NOT NULL
        """
        results["avg_response_time"] = _run_scalar_query(
            client, audit_service.confirmation_table_id, confirmation_query, start_dt
        )
    except Exception as exc:  # pragma: no cover - runtime failure path
        results["avg_response_time"] = {"error": str(exc)}

    return {
        "period": _normalize_period(period),
        "start_date": start_dt.isoformat(),
        "end_date": now.isoformat(),
        "statistics": results,
        "hipaa_compliant": True,
        "phi_included": False,
    }


def get_realtime_shift_stats(hours: int = 8) -> Dict[str, Any]:
    """
    Get current shift aggregate stats only (last N hours).
    """
    client = audit_service.client
    if not client:
        return {
            "shift": "current",
            "period": f"last_{hours}_hours",
            "error": "BigQuery not available",
            "hipaa_compliant": True,
            "phi_included": False,
        }

    start_dt = datetime.utcnow() - timedelta(hours=max(hours, 1))
    triage_table_id = audit_service.table_id
    confirmation_table_id = audit_service.confirmation_table_id

    query = """
        SELECT
            COUNT(*) AS total_cases,
            COUNTIF(final_esi <= 2) AS critical_cases,
            COUNTIF(final_esi > recommended_esi) AS under_triage,
            ROUND(AVG(news2_score), 1) AS avg_news2
        FROM `{table_id}`
        WHERE timestamp >= @start_dt
    """

    try:
        summary = _run_scalar_query(client, triage_table_id, query, start_dt)
        response_time_query = """
            SELECT ROUND(AVG(response_time_seconds), 1) AS avg_response_seconds
            FROM `{table_id}`
            WHERE timestamp >= @start_dt
              AND response_time_seconds IS NOT NULL
        """
        response_time = _run_scalar_query(client, confirmation_table_id, response_time_query, start_dt)
        summary["avg_response_seconds"] = response_time.get("avg_response_seconds")
    except Exception as exc:  # pragma: no cover - runtime failure path
        summary = {"error": str(exc)}

    return {
        "shift": "current",
        "period": f"last_{hours}_hours",
        "start_date": start_dt.isoformat(),
        "last_updated": datetime.utcnow().isoformat(),
        **summary,
        "hipaa_compliant": True,
        "phi_included": False,
    }
