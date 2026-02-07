from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.responses import StreamingResponse
from validators import validate_gender_complaint
from audit_service import audit_service
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import tempfile
import os
import io
from datetime import datetime, timedelta
from threading import Lock

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from models import (
    PatientInput,
    TriageResult,
    TriageConfirmationRequest,
    TriageConfirmationStart,
    TriageConfirmationPending,
)
from logic.deterministic_triage import DeterministicTriageEngine
from database import engine, Base, get_db
from sql_models import Patient
import uvicorn
from ai_service import ai_service
from medasr_service import medasr_service
from alert_service import (
    AlertLevel,
    GAHAR_NOTICE,
    send_alert_sync,
    flush_alert_queue_sync,
    get_queue_size,
)
from logic.icd10_integration import enrich_triage_with_icd10, check_silent_mi_pattern, format_icd10_for_hospital_record
from qa_agent import qa_agent
from report_service import generate_daily_report
from resource_labels import get_resources_for_category, get_resources_for_workup
from monitor_service import register_monitor_service
from analytics_service import register_analytics_service
from medgemma_hourly_job import run_hourly_job

# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SAFE-Triage AI System", version="2.0.0")

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_monitor_service(app)
register_analytics_service(app)

# Use the deterministic engine with keyword database
# STANDARD MODE: No AI, only keyword matching (fast)
engine_logic = DeterministicTriageEngine(use_ai=False)

# AI-ENHANCED MODE: Uses AI classification with fallback
engine_logic_ai = DeterministicTriageEngine(use_ai=True)

# Warmup to reduce cold starts
@app.on_event("startup")
async def startup_warmup():
    """Preload heavy resources to reduce cold start latency."""
    try:
        print("🔥 Warmup: initializing UMLS cache", flush=True)
        ai_service.umls_rag.search_snomed("chest pain")
    except Exception as e:
        print(f"Warmup UMLS failed: {e}", flush=True)

    try:
        print("🔥 Warmup: deterministic engine", flush=True)
        engine_logic.triage(
            {
                "age": 30,
                "gender": "male",
                "chief_complaint_text": "warmup",
                "vitals": {"hr": 80, "sbp": 120, "dbp": 80, "rr": 16, "temp": 37, "spo2": 98},
            }
        )
    except Exception as e:
        print(f"Warmup deterministic engine failed: {e}", flush=True)

# ============ HUMAN CONFIRMATION PLACEHOLDERS ============
CONFIRMATION_TIMEOUT_SECONDS = int(os.getenv("CONFIRMATION_TIMEOUT_SECONDS", "300"))
SUPERVISOR_PIN = os.getenv("SUPERVISOR_PIN", "0000")
DOWNGRADE_ROLE = os.getenv("DOWNGRADE_ROLE", "supervisor")

_pending_lock = Lock()
_pending_confirmations = {}


def _send_alert_for_level(
    level: int,
    patient_id: str,
    complaint: str,
    news2_score: int = 0,
    icd10_code: str = "",
    icd10_description: str = "",
    snomed_code: str = "",
    snomed_term: str = "",
    recommended: list = None,
    clinician: str = "Unassigned | غير محدد",
):
    if level is None or level > 2:
        return None
    payload = {
        "alert_level": AlertLevel.CODE_RED if level == 1 else AlertLevel.HIGH_ALERT,
        "patient_id": patient_id,
        "esi_level": level,
        "news2_score": news2_score,
        "complaint": complaint,
        "icd10_code": icd10_code,
        "icd10_description": icd10_description,
        "snomed_code": snomed_code,
        "snomed_term": snomed_term,
        "recommended": recommended or [],
        "clinician": clinician,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return send_alert_sync(payload)


def _build_red_flag_summary(vitals: dict, news2_score: int) -> list:
    summary = []
    try:
        spo2 = vitals.get("spo2")
        sbp = vitals.get("sbp")
        hr = vitals.get("hr")
        if spo2 is not None and spo2 < 90:
            summary.append("SpO2 < 90% → Critical hypoxia | تشبع الأكسجين < 90% → نقص أكسجة حاد")
        if sbp is not None and sbp < 90:
            summary.append("SBP < 90 → Hypotension | ضغط انقباضي < 90 → هبوط ضغط")
        if hr is not None and hr > 130:
            summary.append("HR > 130 → Severe tachycardia | نبض > 130 → تسارع شديد")
        if news2_score is not None and news2_score >= 7:
            summary.append("NEWS2 ≥ 7 → Critical early warning | نيوز2 ≥ 7 → إنذار حرج مبكر")
    except Exception:
        return summary
    return summary


def _normalize_category(category: str) -> str:
    normalized = (category or "").strip().lower()
    if any(token in normalized for token in ["trauma", "fracture", "orthopedic", "hip_fracture"]):
        return "trauma_fracture"
    if normalized == "dyspnea":
        return "respiratory_distress"
    if "sepsis" in normalized or "infection" in normalized:
        return "sepsis_concern"
    if "allerg" in normalized or "anaphyl" in normalized:
        return "allergic_reaction"
    if "psych" in normalized or "suicid" in normalized or "agitation" in normalized:
        return "psychiatric"
    if "abdominal" in normalized or "abdomen" in normalized:
        return "abdominal_pain"
    return normalized


def _action_text_for_level_and_category(
    level: int,
    category: str,
    complaint_text: str = "",
    extracted_symptoms: list = None,
) -> dict:
    normalized = _normalize_category(category)
    combined_text = " ".join(
        [complaint_text or ""] + [str(item) for item in (extracted_symptoms or [])]
    ).lower()

    if any(token in combined_text for token in ["fracture", "broken", "trauma", "dislocation", "كسر", "اصابة", "إصابة"]):
        normalized = "trauma_fracture"
    elif normalized in {"unclear", "unclear_needs_evaluation", "general", "other", ""}:
        if any(token in combined_text for token in ["shortness of breath", "dyspnea", "can not breathe", "ضيق نفس", "مش قادر اتنفس"]):
            normalized = "respiratory_distress"
        elif any(token in combined_text for token in ["stroke", "facial droop", "weakness", "سكتة", "شلل"]):
            normalized = "stroke_symptoms"
        elif any(token in combined_text for token in ["chest pain", "radiating", "angina", "ألم صدر"]):
            normalized = "chest_pain_cardiac"
        elif any(token in combined_text for token in ["sepsis", "infection", "حمى", "تعفن", "عدوى"]):
            normalized = "sepsis_concern"

    if level == 1:
        return {"en": "Resuscitation room immediately", "ar": "غرفة الإنعاش فوراً"}

    if level == 2:
        if normalized == "chest_pain_cardiac":
            return {"en": "ECG room, continuous monitoring", "ar": "غرفة رسم القلب، مراقبة مستمرة"}
        if normalized == "stroke_symptoms":
            return {"en": "Stroke bay, CT immediately", "ar": "سرير السكتة، أشعة مقطعية فوراً"}
        if normalized == "respiratory_distress":
            return {"en": "Resuscitation area, oxygen", "ar": "منطقة الإنعاش، أكسجين"}
        if normalized == "trauma_fracture":
            return {"en": "Trauma bay, imaging", "ar": "سرير الإصابات، أشعة"}
        if normalized == "abdominal_pain":
            return {"en": "Acute care, assessment", "ar": "رعاية حادة، تقييم"}
        if normalized == "sepsis_concern":
            return {"en": "Acute care, IV access, labs", "ar": "رعاية حادة، كانيولا، تحاليل"}
        if normalized == "allergic_reaction":
            return {"en": "Acute care, medication", "ar": "رعاية حادة، علاج"}
        if normalized == "psychiatric":
            return {"en": "Safe room, assessment", "ar": "غرفة آمنة، تقييم"}
        if normalized in {"unclear", "unclear_needs_evaluation"}:
            return {
                "en": "Assessment area, physician evaluation",
                "ar": "منطقة التقييم، فحص طبيب",
            }
        return {
            "en": "Acute care area, physician within 15 min",
            "ar": "منطقة الرعاية الحادة، طبيب خلال 15 دقيقة",
        }

    if level == 3:
        return {"en": "Urgent care area", "ar": "منطقة الرعاية العاجلة"}

    return {"en": "Waiting area, routine", "ar": "منطقة الانتظار، روتيني"}


def _register_pending_confirmation(patient_id: str, recommended_esi: int) -> dict:
    now = datetime.utcnow()
    expires = now + timedelta(seconds=CONFIRMATION_TIMEOUT_SECONDS)
    record = {
        "patient_id": patient_id,
        "recommended_esi": recommended_esi,
        "created_at": now,
        "expires_at": expires,
    }
    with _pending_lock:
        _pending_confirmations[patient_id] = record
    return record


def _resolve_pending_confirmation(patient_id: str) -> dict:
    with _pending_lock:
        return _pending_confirmations.pop(patient_id, None)


def require_firebase_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        request = google_requests.Request()
        audience = os.getenv("FIREBASE_PROJECT_ID", "safe-triage-ai")
        claims = id_token.verify_firebase_token(token, request, audience=audience)
        return claims or {}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.get("/")
def read_root():
    return {"message": "SAFE-Triage AI System Active", "version": "2.0.0", "features": ["Voice Input", "AI Triage", "ESI v5", "Telegram Alerts"]}

@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...), language: str = Form("auto")):
    """🎤 Voice Input: Convert speech to medical text via Gemini"""
    try:
        suffix = os.path.splitext(audio.filename or "")[1] or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        result = medasr_service.transcribe(
            tmp_path,
            language_code=language,
            content_type=audio.content_type,
        )
        os.unlink(tmp_path)
        
        if result["success"]:
            return {"success": True, "transcription": result["transcription"]}
        else:
            raise HTTPException(status_code=500, detail=result["error"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test-alert")
def test_alert():
    """Send a test alert to verify Telegram + Email delivery."""
    payload = {
        "alert_level": AlertLevel.CODE_RED,
        "patient_id": "PT-001",
        "esi_level": 1,
        "news2_score": 8,
        "complaint": "chest pain radiating to left arm",
        "icd10_code": "I20.9",
        "icd10_description": "Angina pectoris",
        "snomed_code": "225566008",
        "snomed_term": "Ischemic chest pain",
        "recommended": ["12-Lead ECG", "Troponin", "Monitor"],
        "clinician": "Dr. Ahmed",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }
    result = send_alert_sync(payload)
    return {"success": True, "alerts_sent": result, "gahar_notice": GAHAR_NOTICE}


@app.post("/confirm-triage/request", response_model=TriageConfirmationPending)
def request_confirmation(request: TriageConfirmationStart):
    """Register a pending confirmation (placeholder storage)."""
    record = _register_pending_confirmation(request.patient_id, request.recommended_esi)
    return record


@app.get("/pending-confirmations", response_model=List[TriageConfirmationPending])
def get_pending_confirmations():
    """List pending confirmations (in-memory placeholder)."""
    with _pending_lock:
        records = list(_pending_confirmations.values())
    return records


@app.post("/confirm-triage")
def confirm_triage(confirmation: TriageConfirmationRequest):
    """
    Record human confirmation of AI recommendation.

    Placeholders:
    - Supervisor PIN: SUPERVISOR_PIN (default 0000)
    - Downgrade role: DOWNGRADE_ROLE (default supervisor)
    """
    is_downgrade = confirmation.confirmed_esi > confirmation.recommended_esi

    if is_downgrade:
        if confirmation.clinician_role != DOWNGRADE_ROLE:
            raise HTTPException(status_code=403, detail="Only supervisors can downgrade ESI")
        if confirmation.supervisor_pin != SUPERVISOR_PIN:
            raise HTTPException(status_code=401, detail="Invalid supervisor PIN")

    if confirmation.action == "overridden" and not confirmation.override_reason:
        raise HTTPException(status_code=400, detail="override_reason required for overrides")

    pending = _resolve_pending_confirmation(confirmation.patient_id)
    response_time = None
    if pending:
        response_time = int((datetime.utcnow() - pending["created_at"]).total_seconds())

    audit_service.log_confirmation(
        patient_id=confirmation.patient_id,
        recommended_esi=confirmation.recommended_esi,
        confirmed_esi=confirmation.confirmed_esi,
        clinician_id=confirmation.clinician_id,
        clinician_role=confirmation.clinician_role,
        action=confirmation.action,
        override_reason=confirmation.override_reason,
        supervisor_id=confirmation.clinician_id if confirmation.clinician_role == "supervisor" else None,
        response_time_seconds=response_time,
        escalated=False,
    )

    alerts_sent = _send_alert_for_level(
        level=confirmation.confirmed_esi,
        patient_id=confirmation.patient_id,
        complaint=f"Confirmed ESI {confirmation.confirmed_esi}",
        clinician=confirmation.clinician_id,
    )

    return {
        "status": "confirmed",
        "response_time_seconds": response_time,
        "alerts_sent": alerts_sent,
        "gahar_notice": GAHAR_NOTICE,
    }

@app.post("/triage", response_model=TriageResult)
def triage_patient(patient: PatientInput, db: Session = Depends(get_db)):
    complaint_text = (patient.chief_complaint_text or "").strip()
    if not complaint_text:
        raise HTTPException(
            status_code=400,
            detail="Chief complaint cannot be empty | لا يمكن أن تكون الشكوى فارغة",
        )

    # Gender-complaint validation
    gender_check = validate_gender_complaint(patient.gender, complaint_text)
    if not gender_check["valid"]:
        raise HTTPException(status_code=400, detail=gender_check)

    try:
        result = engine_logic.evaluate(patient)
        vitals_dict = patient.vitals.model_dump() if patient.vitals else {}
        red_flag_summary = _build_red_flag_summary(vitals_dict, getattr(result, 'news2_score', 0))
        
        # Add ICD-10 coding for GAHAR compliance
        result_dict = result.model_dump() if hasattr(result, 'model_dump') else vars(result)
        result_dict["chief_complaint"] = patient.chief_complaint_text
        result_dict["category"] = getattr(result, 'category', 'general')
        result_dict["red_flag_summary"] = red_flag_summary
        enriched = enrich_triage_with_icd10(result_dict)
        
        # Check Silent MI pattern for diabetic patients
        patient_data = patient.model_dump()
        silent_mi = check_silent_mi_pattern(patient_data)
        if silent_mi["pattern_detected"]:
            enriched["silent_mi_alert"] = silent_mi
        
        # Send alert for critical patients
        alerts_sent = _send_alert_for_level(
            level=result.level.value if hasattr(result.level, 'value') else result.level,
            patient_id=patient.patient_id,
            complaint=patient.chief_complaint_text,
            news2_score=getattr(result, 'news2_score', 0),
            icd10_code=enriched.get("icd10_coding", {}).get("code", ""),
            icd10_description=enriched.get("icd10_coding", {}).get("description_en", ""),
            clinician="Unassigned | غير محدد",
        )
        
        # Audit logging for GAHAR compliance
        audit_service.log_triage(
            patient_id=patient.patient_id,
            age=patient.age,
            gender=patient.gender,
            chief_complaint=patient.chief_complaint_text,
            vitals=patient.vitals.model_dump() if patient.vitals else {},
            news2_score=getattr(result, 'news2_score', 0),
            news2_breakdown=getattr(result, 'news2_breakdown', {}),
            recommended_esi=result.level.value if hasattr(result.level, 'value') else result.level,
            final_esi=result.level.value if hasattr(result.level, 'value') else result.level,
            icd10_codes=[enriched.get("icd10_coding", {}).get("code")],
            session_mode="standard"
        )
        
        return result_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai-triage")
def ai_triage_patient(patient: PatientInput, db: Session = Depends(get_db)):
    """
    AI-enhanced triage endpoint.
    
    AUDIT FIX: Properly handles AI fallback flag.
    When AI fails, uses deterministic engine instead of hardcoded Level 3.
    """
    try:
        print("=" * 50, flush=True)
        print("🏥 AI-TRIAGE ENDPOINT CALLED", flush=True)
        print(f"   ai_service.client = {ai_service.client}", flush=True)
        print(f"   ai_service.mode = {getattr(ai_service, 'mode', 'unknown')}", flush=True)
        print("=" * 50, flush=True)

        complaint_text = (patient.chief_complaint_text or "").strip()
        if not complaint_text:
            raise HTTPException(
                status_code=400,
                detail="Chief complaint cannot be empty | لا يمكن أن تكون الشكوى فارغة",
            )

        # Gender-complaint validation
        gender_check = validate_gender_complaint(patient.gender, complaint_text)
        if not gender_check["valid"]:
            raise HTTPException(status_code=400, detail=gender_check)

        ai_result = ai_service.analyze_triage(patient.model_dump())
        print(f"   ai_result = {ai_result}", flush=True) if ai_result is None else print(f"   ai_result keys = {list(ai_result.keys())}", flush=True)
        
        # AUDIT FIX: Check for fallback flag (not just "error" key)
        # This ensures deterministic engine handles failures safely
        if ai_result is None or ai_result.get("fallback") or "error" in ai_result:
            # Use AI-enabled engine for fallback (it will use keyword matching)
            std_result = engine_logic_ai.evaluate(patient)
            vitals_dict = patient.vitals.model_dump() if patient.vitals else {}
            red_flag_summary = _build_red_flag_summary(vitals_dict, getattr(std_result, 'news2_score', 0))
            
            # Build informative response showing deterministic fallback was used
            fallback_reason = ai_result.get("message", ai_result.get("error", "AI unavailable")) if ai_result else "AI unavailable"
            
            # Add ICD-10 coding for GAHAR compliance
            fallback_dict = {
                "level": std_result.level.value if hasattr(std_result.level, 'value') else std_result.level,
                "category": getattr(std_result, 'category', 'general'),
                "chief_complaint": patient.chief_complaint_text
            }
            enriched = enrich_triage_with_icd10(fallback_dict)
            icd10_coding = enriched.get("icd10_coding", {})

            alerts_sent = None
            fallback_level = std_result.level.value if hasattr(std_result.level, 'value') else std_result.level
            fallback_action = _action_text_for_level_and_category(
                fallback_level,
                getattr(std_result, "category", ai_result.get("category") if ai_result else ""),
                complaint_text=patient.chief_complaint_text,
                extracted_symptoms=ai_result.get("extracted_symptoms") if ai_result else [],
            )
            if fallback_level <= 2:
                alert_payload = {
                    "alert_level": AlertLevel.CODE_RED if fallback_level == 1 else AlertLevel.HIGH_ALERT,
                    "patient_id": patient.patient_id,
                    "esi_level": fallback_level,
                    "news2_score": 0,
                    "complaint": patient.chief_complaint_text,
                    "icd10_code": icd10_coding.get("primary_code", ""),
                    "icd10_description": icd10_coding.get("description_en", ""),
                    "snomed_code": ai_result.get("snomed_code") if ai_result else "",
                    "snomed_term": ai_result.get("snomed_term") if ai_result else "",
                    "recommended": [],
                    "clinician": "Unassigned | غير محدد",
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                }
                alerts_sent = send_alert_sync(alert_payload)
            
            return {
                "level": fallback_level,
                "color_code": std_result.color_code,
                "label_en": std_result.label_en,
                "label_ar": std_result.label_ar,
                "description_ar": fallback_action["ar"],
                "description_en": fallback_action["en"],
                "action_ar": fallback_action["ar"],
                "action_en": fallback_action["en"],
                "time_ar": std_result.time_ar,
                "time_en": std_result.time_en,
                "reasoning": std_result.reasoning + [f"⚠️ {fallback_reason}"],
                "reasoning_ar": std_result.reasoning_ar + [ai_result.get("message_ar", "تم استخدام الفرز الحتمي") if ai_result else "تم استخدام الفرز الحتمي"],
                "reasoning_en": std_result.reasoning_en + [fallback_reason],
                "red_flags": std_result.red_flags,
                "red_flag_summary": red_flag_summary,
                "ai_data": None,
                "confidence": "Deterministic (AI Fallback)",
                "icd10_coding": icd10_coding,
                "icd10_code": icd10_coding.get("primary_code", ""),
                "icd10_description": icd10_coding.get("description_en", ""),
                "snomed_code": "",
                "snomed_term": "",
                "resource_plan": get_resources_for_workup(ai_result.get("recommended_workup") or []) if ai_result else [],
                "alerts_sent": alerts_sent,
                "requires_review": getattr(std_result, "requires_review", False),
                "review_message": getattr(std_result, "review_message", ""),
                "gahar_notice": GAHAR_NOTICE
            }

        # Determine ESI using deterministic rules with AI/RAG category override
        triage_input = patient.model_dump()
        triage_input["category_override"] = ai_result.get("category")
        det_result = engine_logic_ai.triage(triage_input)
        level = det_result.final_level
        localized_resources = get_resources_for_category(det_result.category)
        ai_workup_resources = get_resources_for_workup(ai_result.get("recommended_workup") or [])
        # Prefer keyword-localized workup if available to avoid category misclassification noise.
        merged_resources = ai_workup_resources[:] if ai_workup_resources else localized_resources[:]

        vitals_dict = patient.vitals.model_dump() if patient.vitals else {}
        red_flag_summary = _build_red_flag_summary(vitals_dict, det_result.news2_score)
        colors = {1:"#ef4444", 2:"#f97316", 3:"#eab308", 4:"#22c55e", 5:"#3b82f6"}
        labels_en = {1:"Resuscitation", 2:"Emergent", 3:"Urgent", 4:"Less Urgent", 5:"Non-Urgent"}
        labels_ar = {1:"إنعاش", 2:"طوارئ", 3:"عاجل", 4:"أقل إلحاحاً", 5:"غير عاجل"}
        
        # ESI v4 time to physician guidelines
        times_en = {1:"Immediate", 2:"< 15 minutes", 3:"< 30 minutes", 4:"< 60 minutes", 5:"< 120 minutes"}
        times_ar = {1:"فوري", 2:"< 15 دقيقة", 3:"< 30 دقيقة", 4:"< 60 دقيقة", 5:"< 120 دقيقة"}
        action_category = ai_result.get("category") or det_result.category
        if (action_category or "").strip().lower() in {"", "unclear", "unclear_needs_evaluation", "general", "other"}:
            action_category = det_result.category or action_category
        selected_action = _action_text_for_level_and_category(
            level,
            action_category,
            complaint_text=patient.chief_complaint_text,
            extracted_symptoms=ai_result.get("extracted_symptoms"),
        )

        # Add ICD-10 coding for GAHAR compliance
        response_dict = {
            "level": level,
            "category": det_result.category,
            "chief_complaint": patient.chief_complaint_text
        }
        enriched = enrich_triage_with_icd10(response_dict)
        icd10_coding = enriched.get("icd10_coding", {})
        ai_icd10 = ai_result.get("icd10_coding") or {}
        if ai_icd10.get("primary_code"):
            icd10_coding = {
                **icd10_coding,
                "primary_code": ai_icd10.get("primary_code"),
                "description_en": ai_icd10.get("description_en", icd10_coding.get("description_en")),
                "gahar_compliant": True
            }
        category_for_icd = (ai_result.get("category") or det_result.category or "").strip().lower()
        primary_code = (icd10_coding.get("primary_code") or "").strip().upper()
        if primary_code in {"", "R69"}:
            category_icd_fallback = {
                "chest_pain_cardiac": ("I20.9", "Angina pectoris, unspecified"),
                "stroke_symptoms": ("I63.9", "Cerebral infarction, unspecified"),
                "respiratory_distress": ("R06.0", "Dyspnea"),
            }
            if category_for_icd in category_icd_fallback:
                code, desc = category_icd_fallback[category_for_icd]
                icd10_coding = {
                    **icd10_coding,
                    "primary_code": code,
                    "description_en": desc,
                    "gahar_compliant": True,
                }

        alerts_sent = None
        if level <= 2:
            alert_payload = {
                "alert_level": AlertLevel.CODE_RED if level == 1 else AlertLevel.HIGH_ALERT,
                "patient_id": patient.patient_id,
                "esi_level": level,
                "news2_score": det_result.news2_score,
                "complaint": patient.chief_complaint_text,
                "icd10_code": icd10_coding.get("primary_code", ""),
                "icd10_description": icd10_coding.get("description_en", ""),
                "snomed_code": ai_result.get("snomed_code", ""),
                "snomed_term": ai_result.get("snomed_term", ""),
                "recommended": ai_result.get("recommended_workup") or [],
                "clinician": "Unassigned | غير محدد",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            }
            alerts_sent = send_alert_sync(alert_payload)
        
        # Check Silent MI pattern
        patient_data = patient.model_dump()
        silent_mi = check_silent_mi_pattern(patient_data)

        # Audit logging for GAHAR compliance
        audit_service.log_triage(
            patient_id=patient.patient_id,
            age=patient.age,
            gender=patient.gender,
            chief_complaint=patient.chief_complaint_text,
            vitals=patient.vitals.model_dump() if patient.vitals else {},
            news2_score=det_result.news2_score,
            news2_breakdown=getattr(det_result, "news2_breakdown", {}),
            recommended_esi=level,
            final_esi=level,
            extracted_features=ai_result.get("extracted_symptoms"),
            icd10_codes=[icd10_coding.get("primary_code")] if icd10_coding else [],
            ai_confidence=ai_result.get("confidence"),
            rag_sources=ai_result.get("rag_sources"),
            session_mode="ai"
        )

        # QA Agent review
        try:
            final_esi = level
            qa_review = qa_agent.review_triage(
                triage_result={
                    "esi_level": final_esi,
                    "news2_score": det_result.news2_score,
                },
                patient={
                    "age": patient.age,
                    "gender": patient.gender,
                    "comorbidities": [],
                    "chief_complaint": patient.chief_complaint_text,
                },
            )
            if qa_review["flagged"]:
                print(f"⚠️ QA FLAG: {qa_review['reason']} - Recommend ESI {qa_review['recommended_esi']}")
        except Exception as e:
            print(f"QA Agent error (non-blocking): {e}")

        return {
            "level": level,
            "color_code": colors.get(level, "#eab308"),
            "label_en": f"{labels_en.get(level)} (Level {level})",
            "label_ar": f"{labels_ar.get(level)} (مستوى {level})",
            "description": f"{selected_action['ar']} / {selected_action['en']}",
            "description_ar": selected_action["ar"],
            "description_en": selected_action["en"],
            "recommended_action": f"{selected_action['ar']} / {selected_action['en']}",
            "action_ar": selected_action["ar"],
            "action_en": selected_action["en"],
            "time_to_physician": f"{times_ar.get(level)} / {times_en.get(level)}",
            "time_ar": times_ar.get(level),
            "time_en": times_en.get(level),
            "red_flags": ai_result.get("red_flags", []),
            "red_flag_summary": red_flag_summary,
            "reasoning": [ai_result.get("reasoning")],
            "reasoning_ar": [ai_result.get("reasoning_ar")] if ai_result.get("reasoning_ar") else [],
            "reasoning_en": [ai_result.get("reasoning")] if ai_result.get("reasoning") else [],
            "ai_data": ai_result,
            "confidence": "AI-Generated",
            "icd10_coding": icd10_coding,
            "icd10_code": icd10_coding.get("primary_code", ""),
            "icd10_description": icd10_coding.get("description_en", ""),
            "snomed_code": ai_result.get("snomed_code", ""),
            "snomed_term": ai_result.get("snomed_term", ""),
            "resource_plan": merged_resources,
            "silent_mi_alert": silent_mi if silent_mi["pattern_detected"] else None,
            "alerts_sent": alerts_sent,
            "requires_review": det_result.requires_review,
            "review_message": det_result.review_message,
            "gahar_notice": GAHAR_NOTICE
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/patients")
def get_patients(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    patients = db.query(Patient).order_by(Patient.created_at.desc()).offset(skip).limit(limit).all()
    return patients

@app.get("/patients/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
         raise HTTPException(status_code=404, detail="Patient not found")
    return patient

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

@app.get("/stats")
def get_triage_stats(days: int = 1):
    """Get triage statistics for dashboard. GAHAR compliance monitoring."""
    return audit_service.get_stats(days=days)

@app.get("/health")
def health_check():
    """System health check for monitoring and thesis demo."""
    status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # Check AI Service
    ai_service_ref = None
    try:
        from ai_service import ai_service
        ai_service_ref = ai_service
        status["components"]["ai"] = {
            "status": "ok" if ai_service.client else "degraded",
            "mode": getattr(ai_service, 'mode', 'unknown'),
            "model": getattr(ai_service, 'model_name', 'unknown')
        }
    except Exception as e:
        status["components"]["ai"] = {"status": "error", "error": str(e)}
    
    # Check RAG
    try:
        rag_ok = ai_service_ref is not None and getattr(ai_service_ref, "umls_rag", None) is not None
        status["components"]["rag"] = {"status": "ok" if rag_ok else "degraded"}
    except Exception as e:
        status["components"]["rag"] = {"status": "error", "error": str(e)}
    
    # Check QA Agent
    try:
        from qa_agent import qa_agent
        status["components"]["qa_agent"] = {"status": "ok"}
    except Exception as e:
        status["components"]["qa_agent"] = {"status": "error", "error": str(e)}
    
    # Check BigQuery
    try:
        from audit_service import audit_service
        status["components"]["bigquery"] = {
            "status": "ok" if audit_service.client else "degraded"
        }
    except Exception as e:
        status["components"]["bigquery"] = {"status": "error", "error": str(e)}

    # Flush alert queue (offline fallback)
    try:
        flush_result = flush_alert_queue_sync()
        status["components"]["alerts"] = {
            "status": "ok",
            "queue_size": get_queue_size(),
            "flush_result": flush_result,
        }
    except Exception as e:
        status["components"]["alerts"] = {"status": "error", "error": str(e)}
    
    # Overall status
    all_ok = all(c.get("status") == "ok" for c in status["components"].values())
    status["status"] = "healthy" if all_ok else "degraded"
    
    status["gahar_notice"] = GAHAR_NOTICE
    return status


@app.post("/medgemma/hourly-review", tags=["MedGemma QA"])
async def trigger_medgemma_hourly():
    """Manually trigger hourly MedGemma batch QA (Cloud Scheduler target)."""
    try:
        result = await run_hourly_job()
        result["gahar_notice"] = GAHAR_NOTICE
        return result
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "gahar_notice": GAHAR_NOTICE,
        }


@app.post("/medgemma/review-now")
async def medgemma_review_now():
    """Backward-compatible alias for immediate manual MedGemma review."""
    return await trigger_medgemma_hourly()


@app.get("/medgemma/status", tags=["MedGemma QA"])
def medgemma_status():
    """Health check for Hugging Face MedGemma service."""
    try:
        from medgemma_client import MedGemmaClient

        client = MedGemmaClient()
        healthy = client.test_connection()
        return {
            "service": "MedGemma QA",
            "model": "medgemma-2b",
            "provider": "Hugging Face",
            "status": "operational" if healthy else "degraded",
            "api_accessible": healthy,
            "gahar_notice": GAHAR_NOTICE,
        }
    except Exception as exc:
        return {
            "service": "MedGemma QA",
            "model": "medgemma-2b",
            "provider": "Hugging Face",
            "status": "error",
            "api_accessible": False,
            "error": str(exc),
            "gahar_notice": GAHAR_NOTICE,
        }


@app.get("/reports/daily-summary")
def daily_summary_report(
    date: str = None,
    department: str = "Emergency Department",
    user: dict = Depends(require_firebase_user),
):
    """Generate daily PDF report with ICD-10 codes."""
    try:
        report_date = datetime.utcnow().date()
        if date:
            report_date = datetime.strptime(date, "%Y-%m-%d").date()

        audit_service.log_report_download(
            report_date=report_date,
            department=department,
            user_id=user.get("uid"),
            user_email=user.get("email"),
            user_name=user.get("name") or user.get("email") or user.get("uid"),
        )

        pdf_bytes = generate_daily_report(report_date, department)
        filename = f"SAFE_Triage_Daily_Report_{report_date.isoformat()}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
