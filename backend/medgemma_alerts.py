"""
MedGemma Alert System
Dispatches critical and summary QA alerts through existing alert_service.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict

from alert_service import AlertLevel, send_alert_async


async def send_disaster_alert(case: Dict) -> Dict:
    """Immediate alert for critical MedGemma findings."""
    payload = {
        "alert_level": AlertLevel.CODE_RED,
        "patient_id": case.get("case_id", "UNKNOWN"),
        "esi_level": case.get("esi_recommendation") or 2,
        "news2_score": "",
        "complaint": f"MedGemma Critical: {case.get('concerning_pattern', 'Unknown pattern')}",
        "icd10_code": "",
        "icd10_description": "",
        "snomed_code": "",
        "snomed_term": "",
        "recommended": [
            f"Reason: {case.get('reasoning', 'N/A')}",
            f"Action: {case.get('recommended_action', 'Manual physician review now')}",
            "Immediate senior review required",
        ],
        "clinician": "MedGemma-1.5-4B QA Agent",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return await send_alert_async(payload)


async def send_hourly_report(results: Dict) -> Dict:
    """Hourly QA summary report."""
    reviewed = results.get("cases_reviewed", 0)
    flagged = results.get("cases_flagged", 0)
    critical = results.get("critical_flags", 0)
    moderate = results.get("moderate_flags", 0)
    ratio = (flagged / reviewed * 100.0) if reviewed else 0.0
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:00")

    payload = {
        "alert_level": AlertLevel.ESCALATION,
        "patient_id": f"QA-HOURLY-{timestamp}",
        "esi_level": "",
        "news2_score": "",
        "complaint": (
            f"MedGemma Hourly Report {timestamp}: "
            f"reviewed={reviewed}, flagged={flagged} ({ratio:.1f}%), "
            f"critical={critical}, moderate={moderate}"
        ),
        "icd10_code": "",
        "icd10_description": "",
        "snomed_code": "",
        "snomed_term": "",
        "recommended": ["Open analytics dashboard for flagged case details"],
        "clinician": "MedGemma-1.5-4B QA Agent",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return await send_alert_async(payload)
