"""
MedGemma Batched QA Agent
Analyzes recent triage cases in a single hourly Hugging Face call.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Dict, List

from google.cloud import bigquery

from medgemma_client import MedGemmaClient

PROJECT_ID = os.getenv("PROJECT_ID", "safe-triage-ai")
AUDIT_TABLE_ID = os.getenv(
    "AUDIT_TABLE_ID",
    "safe-triage-ai.safe_triage_audit.triage_logs",
)
MEDGEMMA_TABLE_ID = os.getenv(
    "MEDGEMMA_TABLE_ID",
    "safe-triage-ai.safe_triage_audit.medgemma_flagged_cases",
)
QA_MAX_CASES = int(os.getenv("MEDGEMMA_QA_MAX_CASES", "50"))
QA_WINDOW_HOURS = int(os.getenv("MEDGEMMA_QA_WINDOW_HOURS", "1"))
QA_THRESHOLD = float(os.getenv("MEDGEMMA_FLAG_THRESHOLD", "0.7"))


class MedGemmaBatchQA:
    """Hourly batch review using Gemma-2B over Hugging Face API."""

    def __init__(self):
        self.medgemma = MedGemmaClient()
        self.review_window_hours = QA_WINDOW_HOURS
        self.flagging_threshold = QA_THRESHOLD

    @staticmethod
    def _get_bq_client() -> bigquery.Client | None:
        try:
            return bigquery.Client(project=PROJECT_ID)
        except Exception as exc:
            print(f"[MedGemma] BigQuery client unavailable: {exc}")
            return None

    def ensure_flag_table(self) -> None:
        client = self._get_bq_client()
        if not client:
            return
        schema = [
            bigquery.SchemaField("case_id", "STRING"),
            bigquery.SchemaField("review_timestamp", "TIMESTAMP"),
            bigquery.SchemaField("severity", "STRING"),
            bigquery.SchemaField("confidence", "FLOAT"),
            bigquery.SchemaField("pattern", "STRING"),
            bigquery.SchemaField("reasoning", "STRING"),
            bigquery.SchemaField("recommended_action", "STRING"),
            bigquery.SchemaField("esi_recommendation", "INTEGER"),
            bigquery.SchemaField("model_used", "STRING"),
            bigquery.SchemaField("disaster_alert_sent", "BOOLEAN"),
        ]
        try:
            client.get_table(MEDGEMMA_TABLE_ID)
        except Exception:
            table = bigquery.Table(MEDGEMMA_TABLE_ID, schema=schema)
            client.create_table(table)
            print(f"[MedGemma] Created table: {MEDGEMMA_TABLE_ID}")

    def get_cases_last_hour(self) -> List[Dict]:
        client = self._get_bq_client()
        if not client:
            return []
        query = f"""
            SELECT
                log_id AS case_id,
                patient_id,
                timestamp,
                chief_complaint AS complaint,
                NULL AS complaint_ar,
                JSON_VALUE(vitals, '$.hr') AS hr,
                JSON_VALUE(vitals, '$.sbp') AS sbp,
                JSON_VALUE(vitals, '$.dbp') AS dbp,
                JSON_VALUE(vitals, '$.rr') AS rr,
                JSON_VALUE(vitals, '$.spo2') AS spo2,
                JSON_VALUE(vitals, '$.temp') AS temp,
                news2_score,
                final_esi AS esi_level,
                recommended_esi AS recommended_esi_level,
                extracted_features,
                NULL AS comorbidities,
                age,
                gender,
                IF(was_overridden IS NULL, TRUE, NOT was_overridden) AS clinician_confirmed,
                override_reason
            FROM `{AUDIT_TABLE_ID}`
            WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {self.review_window_hours} HOUR)
            ORDER BY timestamp DESC
            LIMIT {QA_MAX_CASES}
        """
        try:
            rows = client.query(query).result()
            cases = []
            for row in rows:
                case = dict(row)
                extracted = case.get("extracted_features")
                if extracted and isinstance(extracted, str):
                    try:
                        case["extracted_features"] = json.loads(extracted)
                    except Exception:
                        case["extracted_features"] = extracted
                comorb = case.get("comorbidities")
                if comorb and isinstance(comorb, str):
                    try:
                        case["comorbidities"] = json.loads(comorb)
                    except Exception:
                        case["comorbidities"] = []
                elif not comorb:
                    case["comorbidities"] = []
                cases.append(case)
            print(f"[MedGemma] Retrieved {len(cases)} cases")
            return cases
        except Exception as exc:
            print(f"[MedGemma] BigQuery fetch failed: {exc}")
            return []

    def build_batch_prompt(self, cases: List[Dict]) -> str:
        prompt = f"""You are an emergency medicine attending reviewing triage decisions.

Review these {len(cases)} ED cases and flag concerning patterns.

CRITICAL PATTERNS:
1. Silent MI: Diabetic + GI symptoms + age>50
2. Atypical stroke: Neuro symptoms without FAST
3. Sepsis: Fever + tachy + hypotension
4. Pediatric deterioration: Age<5 + dehydration signs
5. Aortic dissection: Chest pain + HTN + age>50

CASES:
"""

        for i, case in enumerate(cases, 1):
            comorbid = ", ".join(case.get("comorbidities", [])[:3]) or "None"
            prompt += f"""
{i}. {case.get('case_id')}: {case.get('age')}{case.get('gender')}, {comorbid}
Complaint: {str(case.get('complaint') or '')[:120]}
Vitals: HR{case.get('hr')} BP{case.get('sbp')}/{case.get('dbp')} RR{case.get('rr')} SpO2{case.get('spo2')}% T{case.get('temp')}
NEWS2={case.get('news2_score')} ESI={case.get('esi_level')}
"""

        prompt += """
Respond ONLY with JSON array:
[
  {"id":"case_id","flag":true,"severity":"Critical","confidence":0.9,"pattern":"Silent MI","reason":"Diabetic 58M GI symptoms","action":"ECG+troponin","esi":2},
  {"id":"case_id","flag":false,"severity":"Low","confidence":0.2,"pattern":"None","reason":"Appropriate ESI","action":"None","esi":null}
]

Include ALL cases. Valid JSON only, no markdown.
"""
        return prompt

    def parse_medgemma_response(self, response_text: str) -> List[Dict]:
        if not response_text:
            return []
        text = response_text.strip()
        if "```" in text:
            match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
            if match:
                text = match.group(1)
            else:
                array_match = re.search(r"\[.*\]", text, re.DOTALL)
                if array_match:
                    text = array_match.group(0)
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            objects = re.findall(r"\{[^{}]*\}", text)
            recovered = []
            for obj in objects:
                try:
                    recovered.append(json.loads(obj))
                except Exception:
                    continue
            return recovered

    def analyze_batch(self, cases: List[Dict]) -> Dict:
        if not cases:
            return {
                "status": "no_cases",
                "cases_reviewed": 0,
                "cases_flagged": 0,
                "critical_flags": 0,
                "moderate_flags": 0,
                "flagged_details": [],
                "critical_cases": [],
                "moderate_cases": [],
                "model_used": "medgemma-4b-it",
                "error": None,
            }

        prompt = self.build_batch_prompt(cases)
        response_text = self.medgemma.generate(prompt=prompt, max_tokens=3000, temperature=0.1)
        if not response_text:
            return {
                "status": "error",
                "cases_reviewed": len(cases),
                "cases_flagged": 0,
                "critical_flags": 0,
                "moderate_flags": 0,
                "flagged_details": [],
                "critical_cases": [],
                "moderate_cases": [],
                "model_used": "medgemma-4b-it",
                "error": "MedGemma API call failed",
            }

        parsed = self.parse_medgemma_response(response_text)
        if not parsed:
            return {
                "status": "error",
                "cases_reviewed": len(cases),
                "cases_flagged": 0,
                "critical_flags": 0,
                "moderate_flags": 0,
                "flagged_details": [],
                "critical_cases": [],
                "moderate_cases": [],
                "model_used": "medgemma-4b-it",
                "error": "Could not parse MedGemma response",
            }

        normalized = []
        for row in parsed:
            normalized.append(
                {
                    "case_id": row.get("id") or row.get("case_id"),
                    "flag_case": row.get("flag") if row.get("flag") is not None else row.get("flag_case", False),
                    "severity": row.get("severity", "Low"),
                    "confidence": float(row.get("confidence", 0.0) or 0.0),
                    "concerning_pattern": row.get("pattern") or row.get("concerning_pattern", "None"),
                    "reasoning": row.get("reason") or row.get("reasoning", ""),
                    "recommended_action": row.get("action") or row.get("recommended_action", "None"),
                    "esi_recommendation": row.get("esi") or row.get("esi_recommendation"),
                }
            )

        flagged = [
            row
            for row in normalized
            if row["flag_case"] and row["confidence"] >= self.flagging_threshold
        ]
        critical = [row for row in flagged if str(row["severity"]).lower() == "critical"]
        moderate = [row for row in flagged if str(row["severity"]).lower() == "moderate"]

        return {
            "status": "success",
            "cases_reviewed": len(cases),
            "cases_flagged": len(flagged),
            "critical_flags": len(critical),
            "moderate_flags": len(moderate),
            "flagged_details": flagged,
            "critical_cases": critical,
            "moderate_cases": moderate,
            "all_results": normalized,
            "model_used": "medgemma-4b-it",
            "timestamp": datetime.utcnow().isoformat(),
            "error": None,
        }

    def store_results_in_bigquery(self, results: Dict) -> None:
        if not results.get("flagged_details"):
            return
        client = self._get_bq_client()
        if not client:
            return
        self.ensure_flag_table()
        rows = []
        for case in results["flagged_details"]:
            rows.append(
                {
                    "case_id": case.get("case_id"),
                    "review_timestamp": datetime.utcnow().isoformat(),
                    "severity": case.get("severity"),
                    "confidence": case.get("confidence"),
                    "pattern": case.get("concerning_pattern"),
                    "reasoning": case.get("reasoning"),
                    "recommended_action": case.get("recommended_action"),
                    "esi_recommendation": case.get("esi_recommendation"),
                    "model_used": "medgemma-4b-it",
                    "disaster_alert_sent": str(case.get("severity", "")).lower() == "critical",
                }
            )
        try:
            errors = client.insert_rows_json(MEDGEMMA_TABLE_ID, rows)
            if errors:
                print(f"[MedGemma] BigQuery insert errors: {errors}")
            else:
                print(f"[MedGemma] Stored {len(rows)} flagged cases")
        except Exception as exc:
            print(f"[MedGemma] BigQuery storage failed: {exc}")

    async def run_hourly_review(self) -> Dict:
        print("[MedGemma] Hourly review started")
        cases = self.get_cases_last_hour()
        results = self.analyze_batch(cases)
        if results.get("status") == "success":
            self.store_results_in_bigquery(results)
        print("[MedGemma] Hourly review completed")
        return results
