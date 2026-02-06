"""
Audit Service - BigQuery logging for SAFE-Triage
GAHAR Compliance: 5-7 year retention, append-only, encrypted at rest
"""

import os
import uuid
from datetime import datetime, date
from typing import Optional, Dict, Any
import json

try:
    from google.cloud import bigquery
    BQ_AVAILABLE = True
except ImportError:
    BQ_AVAILABLE = False
    print("[Audit] google-cloud-bigquery not installed - logging disabled")


class AuditService:
    def __init__(self):
        self.client = None
        self.table_id = "safe-triage-ai.safe_triage_audit.triage_logs"
        self.confirmation_table_id = "safe-triage-ai.safe_triage_audit.triage_confirmations"
        self.report_download_table_id = "safe-triage-ai.safe_triage_audit.report_downloads"
        
        if not BQ_AVAILABLE:
            print("[Audit] BigQuery client not available")
            return
            
        try:
            self.client = bigquery.Client(project="safe-triage-ai")
            print("[Audit] BigQuery audit logging initialized")
            self._ensure_confirmation_table()
            self._ensure_report_download_table()
        except Exception as e:
            print(f"[Audit] BigQuery init failed: {e}")

    def _ensure_confirmation_table(self) -> None:
        """Create confirmation audit table if it doesn't exist."""
        if not self.client:
            return

        schema = [
            bigquery.SchemaField("log_id", "STRING"),
            bigquery.SchemaField("timestamp", "TIMESTAMP"),
            bigquery.SchemaField("confirmed_at", "TIMESTAMP"),
            bigquery.SchemaField("patient_id", "STRING"),
            bigquery.SchemaField("recommended_esi", "INTEGER"),
            bigquery.SchemaField("confirmed_esi", "INTEGER"),
            bigquery.SchemaField("was_overridden", "BOOLEAN"),
            bigquery.SchemaField("clinician_id", "STRING"),
            bigquery.SchemaField("clinician_name", "STRING"),
            bigquery.SchemaField("clinician_role", "STRING"),
            bigquery.SchemaField("action", "STRING"),
            bigquery.SchemaField("override_reason", "STRING"),
            bigquery.SchemaField("supervisor_id", "STRING"),
            bigquery.SchemaField("response_time_seconds", "INTEGER"),
            bigquery.SchemaField("escalated", "BOOLEAN"),
        ]

        try:
            table = self.client.get_table(self.confirmation_table_id)
            existing = {field.name for field in table.schema}
            missing = [field for field in schema if field.name not in existing]
            if missing:
                table.schema = list(table.schema) + missing
                self.client.update_table(table, ["schema"])
                print(f"[Audit] Updated confirmation table schema (+{len(missing)} fields)")
        except Exception:
            try:
                table = bigquery.Table(self.confirmation_table_id, schema=schema)
                self.client.create_table(table)
                print("[Audit] Created confirmation audit table")
            except Exception as e:
                print(f"[Audit] Failed to create confirmation table: {e}")

    def _ensure_report_download_table(self) -> None:
        """Create report downloads table if it doesn't exist."""
        if not self.client:
            return

        schema = [
            bigquery.SchemaField("download_id", "STRING"),
            bigquery.SchemaField("timestamp", "TIMESTAMP"),
            bigquery.SchemaField("report_date", "DATE"),
            bigquery.SchemaField("department", "STRING"),
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("user_email", "STRING"),
            bigquery.SchemaField("user_name", "STRING"),
        ]

        try:
            self.client.get_table(self.report_download_table_id)
        except Exception:
            try:
                table = bigquery.Table(self.report_download_table_id, schema=schema)
                self.client.create_table(table)
                print("[Audit] Created report downloads table")
            except Exception as e:
                print(f"[Audit] Failed to create report downloads table: {e}")
    
    def log_triage(
        self,
        patient_id: str,
        age: int,
        gender: str,
        chief_complaint: str,
        vitals: Dict[str, Any],
        news2_score: int,
        news2_breakdown: Dict[str, Any],
        recommended_esi: int,
        final_esi: int,
        extracted_features: Optional[Dict] = None,
        icd10_codes: Optional[list] = None,
        ai_confidence: Optional[float] = None,
        was_overridden: bool = False,
        override_reason: Optional[str] = None,
        clinician_id: Optional[str] = None,
        rag_sources: Optional[list] = None,
        session_mode: str = "standard"
    ) -> bool:
        """
        Log a triage decision to BigQuery.
        Returns True if logged successfully, False otherwise.
        """
        if not self.client:
            print("[Audit] Skipping log - no BigQuery client")
            return False
        
        try:
            row = {
                "log_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "patient_id": patient_id,
                "age": age,
                "gender": gender,
                "chief_complaint": chief_complaint,
                "vitals": json.dumps(vitals) if vitals else None,
                "extracted_features": json.dumps(extracted_features) if extracted_features else None,
                "icd10_codes": json.dumps(icd10_codes) if icd10_codes else None,
                "news2_score": news2_score,
                "news2_breakdown": json.dumps(news2_breakdown) if news2_breakdown else None,
                "ai_confidence": ai_confidence,
                "recommended_esi": recommended_esi,
                "final_esi": final_esi,
                "was_overridden": was_overridden,
                "override_reason": override_reason,
                "clinician_id": clinician_id,
                "rag_sources": json.dumps(rag_sources) if rag_sources else None,
                "session_mode": session_mode
            }
            
            errors = self.client.insert_rows_json(self.table_id, [row])
            
            if errors:
                print(f"[Audit] BigQuery insert errors: {errors}")
                return False
            
            print(f"[Audit] Logged triage for patient {patient_id}")
            return True
            
        except Exception as e:
            print(f"[Audit] Failed to log: {e}")
            return False
    
    def get_stats(self, days: int = 1) -> Dict[str, Any]:
        """Get triage statistics for dashboard."""
        if not self.client:
            return {"error": "BigQuery not available"}
        
        try:
            query = f"""
            SELECT 
                COUNT(*) as total,
                COUNTIF(final_esi = 1) as esi1,
                COUNTIF(final_esi = 2) as esi2,
                COUNTIF(final_esi = 3) as esi3,
                COUNTIF(final_esi = 4) as esi4,
                COUNTIF(final_esi = 5) as esi5,
                COUNTIF(final_esi > recommended_esi) as under_triage,
                SAFE_DIVIDE(COUNTIF(was_overridden = TRUE) * 100.0, COUNT(*)) as override_rate
            FROM `{self.table_id}`
            WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
            """
            
            result = self.client.query(query).result()
            row = list(result)[0]
            
            return {
                "total": row.total,
                "esiBreakdown": {
                    "ESI1": row.esi1,
                    "ESI2": row.esi2,
                    "ESI3": row.esi3,
                    "ESI4": row.esi4,
                    "ESI5": row.esi5
                },
                "underTriage": int(row.under_triage or 0),
                "overrideRate": round(float(row.override_rate or 0), 1)
            }
        except Exception as e:
            print(f"[Audit] Stats query failed: {e}")
            return {"error": str(e)}

    def log_confirmation(
        self,
        patient_id: str,
        recommended_esi: int,
        confirmed_esi: int,
        clinician_id: str,
        clinician_role: str,
        action: str,
        override_reason: Optional[str] = None,
        supervisor_id: Optional[str] = None,
        response_time_seconds: Optional[int] = None,
        escalated: bool = False,
    ) -> bool:
        """Log human confirmation to BigQuery (placeholders OK)."""
        if not self.client:
            print("[Audit] Skipping confirmation log - no BigQuery client")
            return False

        try:
            row = {
                "log_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "confirmed_at": datetime.utcnow().isoformat(),
                "patient_id": patient_id,
                "recommended_esi": recommended_esi,
                "confirmed_esi": confirmed_esi,
                "was_overridden": action == "overridden",
                "clinician_id": clinician_id,
                "clinician_name": clinician_id,
                "clinician_role": clinician_role,
                "action": action,
                "override_reason": override_reason,
                "supervisor_id": supervisor_id,
                "response_time_seconds": response_time_seconds,
                "escalated": escalated,
            }

            errors = self.client.insert_rows_json(self.confirmation_table_id, [row])
            if errors:
                print(f"[Audit] BigQuery confirmation insert errors: {errors}")
                return False

            print(f"[Audit] Logged confirmation for patient {patient_id}")
            return True
        except Exception as e:
            print(f"[Audit] Confirmation log failed: {e}")
            return False

    def log_report_download(
        self,
        report_date: date,
        department: str,
        user_id: Optional[str],
        user_email: Optional[str],
        user_name: Optional[str],
    ) -> bool:
        """Log daily report downloads to BigQuery."""
        if not self.client:
            print("[Audit] Skipping report download log - no BigQuery client")
            return False

        try:
            row = {
                "download_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "report_date": report_date.isoformat(),
                "department": department,
                "user_id": user_id,
                "user_email": user_email,
                "user_name": user_name,
            }
            errors = self.client.insert_rows_json(self.report_download_table_id, [row])
            if errors:
                print(f"[Audit] Report download insert errors: {errors}")
                return False
            print(f"[Audit] Logged report download for {user_email or user_id}")
            return True
        except Exception as e:
            print(f"[Audit] Report download log failed: {e}")
            return False


# Singleton
audit_service = AuditService()
