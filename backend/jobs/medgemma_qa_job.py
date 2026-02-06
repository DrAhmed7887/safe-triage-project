#!/usr/bin/env python3
"""MedGemma QA Review Job - runs every 15 minutes via Cloud Scheduler."""
import json
import os
from datetime import datetime
from typing import Any, Dict, List

from google.cloud import bigquery
import vertexai

# Support both GA and preview SDKs
try:
    from vertexai.generative_models import GenerativeModel
except Exception:  # pragma: no cover
    from vertexai.preview.generative_models import GenerativeModel

PROJECT_ID = os.getenv("PROJECT_ID", "safe-triage-ai")
DATASET_ID = os.getenv("DATASET_ID", "safe_triage_audit")
TRIAGE_TABLE = os.getenv("TRIAGE_TABLE", "triage_logs")
QA_FLAGS_TABLE = os.getenv("QA_FLAGS_TABLE", "qa_flags")
QA_REVIEWS_TABLE = os.getenv("QA_REVIEWS_TABLE", "qa_reviews")
QA_MAX_CASES = int(os.getenv("QA_MAX_CASES", "50"))
MODEL_NAME = os.getenv("QA_MODEL", "gemini-2.0-flash-001")
BQ_LOCATION = os.getenv("BQ_LOCATION", "me-west1")


def _table_ref(name: str) -> str:
    return f"{PROJECT_ID}.{DATASET_ID}.{name}"

def ensure_tables(client: bigquery.Client) -> None:
    """Create QA tables if they don't exist."""
    qa_reviews_schema = [
        bigquery.SchemaField("patient_id", "STRING"),
        bigquery.SchemaField("reviewed_at", "TIMESTAMP"),
        bigquery.SchemaField("assigned_esi", "INTEGER"),
        bigquery.SchemaField("appropriate", "BOOLEAN"),
        bigquery.SchemaField("concern", "STRING"),
    ]
    qa_flags_schema = [
        bigquery.SchemaField("patient_id", "STRING"),
        bigquery.SchemaField("flagged_at", "TIMESTAMP"),
        bigquery.SchemaField("assigned_esi", "INTEGER"),
        bigquery.SchemaField("concern", "STRING"),
        bigquery.SchemaField("recommendation", "STRING"),
        bigquery.SchemaField("reasoning", "STRING"),
    ]

    for table_name, schema in [
        (QA_REVIEWS_TABLE, qa_reviews_schema),
        (QA_FLAGS_TABLE, qa_flags_schema),
    ]:
        table_id = _table_ref(table_name)
        try:
            client.get_table(table_id)
        except Exception:
            table = bigquery.Table(table_id, schema=schema)
            client.create_table(table)


def fetch_recent_cases(client: bigquery.Client) -> List[Dict[str, Any]]:
    query = f"""
        SELECT
            patient_id,
            age,
            gender,
            chief_complaint,
            vitals,
            extracted_features,
            recommended_esi,
            final_esi,
            timestamp
        FROM `{_table_ref(TRIAGE_TABLE)}`
        WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
        ORDER BY timestamp DESC
        LIMIT {QA_MAX_CASES}
    """
    rows = client.query(query, location=BQ_LOCATION).result()
    cases = []
    for row in rows:
        cases.append(dict(row))
    return cases


def analyze_case(model: GenerativeModel, case: Dict[str, Any]) -> Dict[str, Any]:
    age = int(case.get("age") or 0)
    assigned_esi = int(case.get("final_esi") or 0)
    complaint = str(case.get("chief_complaint") or "").replace("أ", "ا").lower()
    extracted_raw = case.get("extracted_features")
    extracted_text = ""
    if extracted_raw:
        if isinstance(extracted_raw, str):
            try:
                parsed = json.loads(extracted_raw)
                if isinstance(parsed, list):
                    extracted_text = " ".join(str(x) for x in parsed)
                else:
                    extracted_text = str(parsed)
            except Exception:
                extracted_text = extracted_raw
        else:
            extracted_text = str(extracted_raw)
    full_text = f"{complaint} {extracted_text}".replace("أ", "ا").lower()
    gi_silent_mi_signals = [
        "indigestion", "heartburn", "epigastric", "dyspepsia",
        "سوء هضم", "حموضه", "حموضة", "حرقان", "الم معده", "ألم معدة",
    ]
    has_silent_mi_pattern = age >= 50 and assigned_esi >= 3 and any(sig in full_text for sig in gi_silent_mi_signals)
    if has_silent_mi_pattern:
        return {
            "appropriate": False,
            "concern": "Possible silent MI risk in older patient with atypical GI presentation",
            "recommendation": "ESI 2",
            "reasoning": "Atypical ACS can present as GI symptoms in older adults and should be upgraded for urgent cardiac reassessment.",
        }

    prompt = f"""
You are a senior emergency physician reviewing a triage decision.

Case:
- Age: {case.get('age')}, Gender: {case.get('gender')}
- Complaint: {case.get('chief_complaint')}
- Extracted Symptoms: {case.get('extracted_features')}
- Assigned ESI: {case.get('final_esi')}

Question: Is this ESI appropriate? Could this be under-triaged?

Return JSON only:
{{
  "appropriate": true/false,
  "concern": "description if inappropriate",
  "recommendation": "ESI level if different",
  "reasoning": "clinical justification"
}}
"""
    response = model.generate_content(prompt)
    text = response.text.strip()
    try:
        return json.loads(text)
    except Exception:
        return {"appropriate": True, "concern": "parse_failed", "recommendation": None, "reasoning": text}


def log_flag(client: bigquery.Client, case: Dict[str, Any], analysis: Dict[str, Any]) -> None:
    row = {
        "patient_id": case.get("patient_id"),
        "flagged_at": datetime.utcnow().isoformat(),
        "concern": analysis.get("concern"),
        "recommendation": analysis.get("recommendation"),
        "reasoning": analysis.get("reasoning"),
        "assigned_esi": case.get("final_esi"),
    }
    client.insert_rows_json(_table_ref(QA_FLAGS_TABLE), [row])


def log_review(client: bigquery.Client, case: Dict[str, Any], analysis: Dict[str, Any]) -> None:
    row = {
        "patient_id": case.get("patient_id"),
        "reviewed_at": datetime.utcnow().isoformat(),
        "assigned_esi": case.get("final_esi"),
        "appropriate": analysis.get("appropriate", True),
        "concern": analysis.get("concern"),
    }
    client.insert_rows_json(_table_ref(QA_REVIEWS_TABLE), [row])


def main():
    print("🩺 MedGemma QA job starting...")
    client = bigquery.Client(project=PROJECT_ID, location=BQ_LOCATION)
    ensure_tables(client)
    vertexai.init(project=PROJECT_ID, location=os.getenv("VERTEX_REGION", "us-central1"))
    model = GenerativeModel(MODEL_NAME)

    cases = fetch_recent_cases(client)
    print(f"Reviewing {len(cases)} cases")

    for case in cases:
        analysis = analyze_case(model, case)
        log_review(client, case, analysis)
        if not analysis.get("appropriate", True):
            log_flag(client, case, analysis)
            print(f"🚨 Flagged {case.get('patient_id')} - {analysis.get('concern')}")

    print("✅ MedGemma QA job complete")


if __name__ == "__main__":
    main()
