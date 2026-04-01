#!/usr/bin/env python3
"""
Create BigQuery views for MedGemma QA analytics dashboard.

Usage:
    python setup_medgemma_bigquery.py

Creates three views in safe-triage-ai.safe_triage_audit:
    1. medgemma_daily_summary   — daily aggregates (flags, patterns, severity)
    2. medgemma_pattern_trends  — pattern frequency over time
    3. medgemma_severity_counts — severity breakdown for dashboard cards
"""

from __future__ import annotations

import os

from google.cloud import bigquery

PROJECT_ID = os.getenv("PROJECT_ID", "safe-triage-ai")
DATASET = f"{PROJECT_ID}.safe_triage_audit"
FLAGS_TABLE = f"{DATASET}.medgemma_flagged_cases"


def create_views() -> None:
    client = bigquery.Client(project=PROJECT_ID)

    views = {
        # ---- Daily summary: one row per day ----
        f"{DATASET}.medgemma_daily_summary": f"""
            SELECT
                DATE(review_timestamp) AS review_date,
                COUNT(*) AS total_flags,
                COUNTIF(severity = 'Critical') AS critical_count,
                COUNTIF(severity = 'Moderate') AS moderate_count,
                COUNTIF(severity = 'Low') AS low_count,
                COUNTIF(disaster_alert_sent = TRUE) AS alerts_sent,
                ROUND(AVG(confidence), 3) AS avg_confidence,
                COUNT(DISTINCT pattern) AS distinct_patterns,
                STRING_AGG(DISTINCT model_used, ', ') AS models_used
            FROM `{FLAGS_TABLE}`
            GROUP BY review_date
            ORDER BY review_date DESC
        """,
        # ---- Pattern trends: which patterns appear most over time ----
        f"{DATASET}.medgemma_pattern_trends": f"""
            SELECT
                DATE(review_timestamp) AS review_date,
                pattern,
                severity,
                COUNT(*) AS occurrences,
                ROUND(AVG(confidence), 3) AS avg_confidence,
                COUNTIF(disaster_alert_sent = TRUE) AS alerts_sent
            FROM `{FLAGS_TABLE}`
            GROUP BY review_date, pattern, severity
            ORDER BY review_date DESC, occurrences DESC
        """,
        # ---- Severity counts: overall breakdown for KPI cards ----
        f"{DATASET}.medgemma_severity_counts": f"""
            SELECT
                severity,
                COUNT(*) AS total,
                ROUND(AVG(confidence), 3) AS avg_confidence,
                MIN(review_timestamp) AS first_seen,
                MAX(review_timestamp) AS last_seen,
                COUNT(DISTINCT pattern) AS distinct_patterns
            FROM `{FLAGS_TABLE}`
            GROUP BY severity
            ORDER BY
                CASE severity
                    WHEN 'Critical' THEN 1
                    WHEN 'Moderate' THEN 2
                    WHEN 'Low' THEN 3
                    ELSE 4
                END
        """,
    }

    for view_id, query in views.items():
        view = bigquery.Table(view_id)
        view.view_query = query
        try:
            client.delete_table(view_id, not_found_ok=True)
            client.create_table(view)
            print(f"  Created view: {view_id}")
        except Exception as exc:
            print(f"  Error creating {view_id}: {exc}")

    print("\nDone. Views are ready for the MedGemma dashboard.")


if __name__ == "__main__":
    print("Creating MedGemma BigQuery analytics views...")
    create_views()
