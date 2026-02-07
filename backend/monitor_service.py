"""
Vital Signs Monitor Integration Service
Receives HL7 v2.x (JSON-converted) or FHIR Observation resources
and exposes cached vitals for triage form auto-fill.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from types import SimpleNamespace

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

from alert_service import AlertLevel, send_alert_sync
from logic.deterministic_triage import NEWS2Calculator

router = APIRouter(prefix="/monitor", tags=["Vital Signs Monitor"])


class LOINCCode(str, Enum):
    HEART_RATE = "8867-4"
    SYSTOLIC_BP = "8480-6"
    DIASTOLIC_BP = "8462-4"
    RESP_RATE = "9279-1"
    SPO2 = "2708-6"
    TEMPERATURE = "8310-5"
    CONSCIOUSNESS = "80288-4"


class VitalSignObservation(BaseModel):
    loinc_code: str = Field(..., description="LOINC code identifying the vital sign")
    value: float = Field(..., description="Measured value")
    unit: str = Field(..., description="Unit of measurement")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    device_id: Optional[str] = Field(default=None, description="Monitor device identifier")
    bed_number: Optional[str] = Field(default=None, description="ED bed location")


class MonitorDataBundle(BaseModel):
    patient_id: str = Field(..., description="Patient identifier (National ID or MRN)")
    encounter_id: Optional[str] = Field(default=None, description="ED encounter/visit ID")
    observations: List[VitalSignObservation]
    monitor_type: Optional[str] = Field(default=None, description="e.g., Philips IntelliVue MX450")


class FHIRObservationBundle(BaseModel):
    resourceType: str = "Bundle"
    type: str = "transaction"
    entry: List[Dict[str, Any]]


LOINC_TO_VITALS_MAP = {
    LOINCCode.HEART_RATE.value: "hr",
    LOINCCode.SYSTOLIC_BP.value: "sbp",
    LOINCCode.DIASTOLIC_BP.value: "dbp",
    LOINCCode.RESP_RATE.value: "rr",
    LOINCCode.SPO2.value: "spo2",
    LOINCCode.TEMPERATURE.value: "temp",
    LOINCCode.CONSCIOUSNESS.value: "gcs",
}


CACHE_TTL_MINUTES = 30
vitals_cache: Dict[str, Dict[str, Any]] = {}


def _risk_label(news2_total: int) -> str:
    if news2_total >= 7:
        return "high"
    if news2_total >= 5:
        return "medium"
    if news2_total >= 1:
        return "low-medium"
    return "low"


def _consciousness_from_gcs(gcs: Optional[float]) -> str:
    if gcs is None:
        return "A"
    if gcs <= 8:
        return "U"
    if gcs <= 12:
        return "P"
    if gcs <= 14:
        return "C"
    return "A"


async def store_vitals_in_cache(patient_id: str, data: Dict[str, Any]) -> None:
    vitals_cache[patient_id] = {
        **data,
        "expires_at": datetime.utcnow() + timedelta(minutes=CACHE_TTL_MINUTES),
    }


async def get_vitals_from_cache(patient_id: str) -> Optional[Dict[str, Any]]:
    cached = vitals_cache.get(patient_id)
    if not cached:
        return None
    if datetime.utcnow() > cached["expires_at"]:
        del vitals_cache[patient_id]
        return None
    return cached


async def clear_expired_cache() -> None:
    while True:
        await asyncio.sleep(60)
        now = datetime.utcnow()
        expired = [pid for pid, data in vitals_cache.items() if now > data["expires_at"]]
        for pid in expired:
            del vitals_cache[pid]


def _map_observations_to_vitals(observations: List[VitalSignObservation]) -> Dict[str, float]:
    vitals: Dict[str, float] = {}
    for obs in observations:
        field_name = LOINC_TO_VITALS_MAP.get(obs.loinc_code)
        if field_name:
            vitals[field_name] = obs.value
    return vitals


def _calculate_news2(vitals: Dict[str, float]) -> Dict[str, Any]:
    calc = NEWS2Calculator()
    consciousness = _consciousness_from_gcs(vitals.get("gcs"))
    news2_vitals = SimpleNamespace(
        hr=int(vitals["hr"]) if vitals.get("hr") is not None else None,
        rr=int(vitals["rr"]) if vitals.get("rr") is not None else None,
        spo2=float(vitals["spo2"]) if vitals.get("spo2") is not None else None,
        sbp=int(vitals["sbp"]) if vitals.get("sbp") is not None else None,
        dbp=int(vitals["dbp"]) if vitals.get("dbp") is not None else None,
        temp=float(vitals["temp"]) if vitals.get("temp") is not None else None,
        gcs=int(vitals["gcs"]) if vitals.get("gcs") is not None else None,
    )
    result = calc.calculate(
        news2_vitals,
        age=30,
        is_copd=False,
        on_supplemental_o2=False,
        consciousness=consciousness,
    )
    return {
        "total_score": result.total_score,
        "risk_level": _risk_label(result.total_score),
        "triage_level": result.triage_level,
        "component_scores": result.component_scores,
        "missing_vitals": result.missing_vitals,
    }


@router.post(
    "/vitals/ingest",
    summary="Ingest vital signs from bedside monitor",
    description="Receives HL7 v2.x converted to JSON or FHIR Observation resources",
)
async def ingest_monitor_vitals(data: MonitorDataBundle):
    try:
        vitals = _map_observations_to_vitals(data.observations)
        required_vitals = {"hr", "sbp", "rr", "spo2", "temp"}
        missing = required_vitals - set(vitals.keys())
        if missing:
            await store_vitals_in_cache(
                data.patient_id,
                {
                    "vitals": vitals,
                    "timestamp": data.observations[0].timestamp.isoformat(),
                    "device": data.monitor_type or data.observations[0].device_id,
                    "bed": data.observations[0].bed_number,
                    "encounter_id": data.encounter_id,
                    "source": "monitor",
                },
            )
            return {
                "status": "partial",
                "message": f"Missing vitals: {sorted(missing)}. Cached for manual completion.",
                "vitals_received": vitals,
            }

        news2_result = _calculate_news2(vitals)
        vitals["consciousness"] = _consciousness_from_gcs(vitals.get("gcs"))

        await store_vitals_in_cache(
            data.patient_id,
            {
                "vitals": vitals,
                "news2": news2_result,
                "timestamp": data.observations[0].timestamp.isoformat(),
                "device": data.monitor_type or data.observations[0].device_id,
                "bed": data.observations[0].bed_number,
                "encounter_id": data.encounter_id,
                "source": "monitor",
            },
        )

        if news2_result["total_score"] >= 7:
            send_alert_sync(
                {
                    "alert_level": AlertLevel.CODE_RED,
                    "patient_id": data.patient_id,
                    "esi_level": 1,
                    "news2_score": news2_result["total_score"],
                    "complaint": "Critical monitor vitals",
                    "recommended": ["Immediate bedside reassessment", "Escalate to physician"],
                    "clinician": "Monitor Integration Service",
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

        return {
            "status": "success",
            "patient_id": data.patient_id,
            "vitals_received": vitals,
            "news2_score": news2_result["total_score"],
            "news2_risk": news2_result["risk_level"],
            "cached_until": (datetime.utcnow() + timedelta(minutes=CACHE_TTL_MINUTES)).isoformat(),
            "message": "Vitals cached. Nurse can open triage form for auto-fill.",
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Monitor ingestion failed: {exc}")


@router.post("/vitals/ingest-fhir", summary="Ingest FHIR Observation Bundle from monitor")
async def ingest_fhir_observations(bundle: FHIRObservationBundle):
    try:
        patient_id = None
        observations: List[VitalSignObservation] = []

        for entry in bundle.entry:
            resource = entry.get("resource", {})
            if resource.get("resourceType") == "Patient" and not patient_id:
                patient_id = resource.get("id")

        for entry in bundle.entry:
            resource = entry.get("resource", {})
            if resource.get("resourceType") != "Observation":
                continue

            subject_ref = resource.get("subject", {}).get("reference", "")
            if not patient_id and subject_ref.startswith("Patient/"):
                patient_id = subject_ref.split("/", 1)[1]

            code_codings = resource.get("code", {}).get("coding", [])
            loinc_code = None
            for coding in code_codings:
                if coding.get("system") == "http://loinc.org" and coding.get("code"):
                    loinc_code = coding["code"]
                    break
            if not loinc_code:
                continue

            value_qty = resource.get("valueQuantity") or {}
            if "value" not in value_qty:
                continue

            observations.append(
                VitalSignObservation(
                    loinc_code=loinc_code,
                    value=float(value_qty["value"]),
                    unit=value_qty.get("unit", ""),
                    timestamp=resource.get("effectiveDateTime", datetime.utcnow().isoformat()),
                    device_id=(resource.get("device") or {}).get("display"),
                    bed_number=(resource.get("encounter") or {}).get("display"),
                )
            )

        if not patient_id:
            raise HTTPException(status_code=400, detail="No patient reference found in FHIR bundle")
        if not observations:
            raise HTTPException(status_code=400, detail="No valid Observation resources found")

        return await ingest_monitor_vitals(
            MonitorDataBundle(patient_id=patient_id, observations=observations, monitor_type="FHIR")
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"FHIR parsing failed: {exc}")


@router.get("/vitals/{patient_id}", summary="Retrieve cached vitals for triage form auto-fill")
async def get_cached_vitals_endpoint(patient_id: str):
    vitals = await get_vitals_from_cache(patient_id)
    if not vitals:
        raise HTTPException(status_code=404, detail="No cached vitals. Nurse must enter manually.")
    payload = dict(vitals)
    payload.pop("expires_at", None)
    return {
        "patient_id": patient_id,
        **payload,
        "auto_fill": True,
        "message": "Vitals from monitor - pre-filled",
    }


@router.delete("/vitals/{patient_id}", summary="Clear cached vitals after triage completed")
async def clear_cached_vitals(patient_id: str):
    if patient_id in vitals_cache:
        del vitals_cache[patient_id]
    return {"status": "cleared"}


@router.get("/status", summary="Monitor connectivity status")
async def monitor_status():
    return {
        "service": "Vital Signs Monitor Integration",
        "status": "operational",
        "cached_patients": len(vitals_cache),
        "cache_ttl_minutes": CACHE_TTL_MINUTES,
        "supported_monitors": [
            "Philips IntelliVue Series",
            "GE Healthcare CARESCAPE",
            "Mindray BeneView",
            "Nihon Kohden Life Scope",
        ],
        "supported_protocols": ["HL7 v2.x (via JSON)", "FHIR R4 Observation"],
    }


def register_monitor_service(app: FastAPI) -> None:
    app.include_router(router)

    @app.on_event("startup")
    async def _start_monitor_cache_cleanup():
        if getattr(app.state, "monitor_cleanup_started", False):
            return
        app.state.monitor_cleanup_started = True
        asyncio.create_task(clear_expired_cache())
